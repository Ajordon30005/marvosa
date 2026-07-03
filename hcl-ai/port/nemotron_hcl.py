"""
nemotron_hcl.py — a Nemotron(-style) transformer forward pass ported onto the
HCL substrate, following hcl-pure/references/06_porting.md.

This is NOT a reimplementation of the math and NOT a weight copy. It is the
forward pass re-expressed as compositions of the ten HCL primitives, so the
model's computation runs as integer-exact FBit/braid operations — the same
substrate Marvosa's own mind and memory stand on. Once the computation is on the
substrate it is commensurable with the HCL-AI (everything is an FBit: a phase +
amplitude), which is the point of the port.

Porting law (06_porting.md): compose, never invent. Every operation below maps
to a primitive already defined in 02_operations.md:
    multiply           -> AMP_MOD
    add / accumulate   -> COMP (in a loop)
    subtract           -> COMP(a, SHIFT(b, -1))
    negate             -> SHIFT(x, -1)
    divide / reciprocal-> AMP_MOD(a, INV(b))
    sqrt               -> _fixed_sqrt (engine) / FISSION
    exp                -> MOBIUS_GROWTH
    cos / sin          -> PHASE_COS / PHASE_SIN
No new math is introduced; this file only ARRANGES the engine's primitives.

Float boundary (Step 3): inputs convert once via to_fp at construction, outputs
convert once via from_fp for inspection. Everything between is integer.
Constants (Step 4): 1/sqrt(d), eps are bootstrapped from the engine, never
imported. The braid word (Step 6) is available from the engine after a run.
Integrity (Step 7): the four-param alpha check must still read 137.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))

import hcl_engine as E

SCALE = E.SCALE
FB    = E.FBit
T     = E.HCLTranscriber


def _fp(x):
    """Boundary in: a Python float/int -> fixed-point integer, ONCE."""
    return T.to_fp(x)


def _val(X):
    """Boundary out: fixed-point integer -> float, ONCE, for display only."""
    return T.from_fp(X)


class HCLTensorEngine:
    """
    Runs transformer ops on the HCL substrate by composing primitives.
    All vector/matrix values are fixed-point integers (x * SCALE). The class
    holds one HCL() so every primitive call appends to a single braid word —
    the complete, reversible trace of the whole forward pass.
    """

    def __init__(self):
        # Compose through a Transcriber instance: it calls the HCL primitives AND
        # logs each generator to its braid_log, so the whole forward pass leaves a
        # complete reversible trace (06_porting Step 6 — keep the braid word).
        self.t = E.HCLTranscriber()

    # ---- scalar helpers: each is a Transcriber primitive (logged to the braid) ----

    def add(self, a, b):                        # a + b  -> COMP
        return self.t.add(a, b)

    def sub(self, a, b):                        # a - b  -> COMP(a, SHIFT(b,-1))
        return self.t.sub(a, b)

    def mul(self, a, b):                        # a * b  -> AMP_MOD
        return self.t.mul(a, b)

    def div(self, a, b):                        # a / b  -> AMP_MOD(a, INV(b))
        return self.t.div(a, b)

    def exp(self, a):                           # e^a    -> MOBIUS_GROWTH
        return self.t.exp(a)

    def sqrt(self, a):                          # sqrt(a) -> FISSION / integer Newton
        return self.t.sqrt(a)

    # ---- vector/matrix ops, composed from the scalars above ----

    def dot(self, xs, ws):                      # Σ x_i*w_i  -> COMP-loop of AMP_MOD
        return self.t.dot(xs, ws)               # the engine's fused form (bit-identical)

    def linear(self, x, W, b=None):
        """y = x W^T (+ b). W is a list of rows (output dim x input dim)."""
        y = [self.dot(x, row) for row in W]
        if b is not None:
            y = [self.add(yi, bi) for yi, bi in zip(y, b)]
        return y

    def layernorm1p(self, x, weight, bias, eps):
        """
        NemotronLayerNorm1P: (x-mean)/sqrt(var+eps), scale by (weight+1), + bias.
        mean/var/sqrt/scale/bias are all COMP/AMP_MOD/INV/_fixed_sqrt compositions.
        """
        n = len(x)
        inv_n = self.div(_fp(1.0), _fp(float(n)))          # 1/n on the substrate
        # mean = (Σ x) / n
        s = 0
        for xi in x:
            s = self.add(s, xi)
        mean = self.mul(s, inv_n)
        # var = (Σ (x-mean)^2) / n
        sv = 0
        devs = []
        for xi in x:
            d = self.sub(xi, mean); devs.append(d)
            sv = self.add(sv, self.mul(d, d))
        var = self.mul(sv, inv_n)
        denom = self.sqrt(self.add(var, eps))              # sqrt(var+eps)
        inv_denom = self.div(_fp(1.0), denom)
        out = []
        for d, w, bi in zip(devs, weight, bias):
            normed = self.mul(d, inv_denom)
            scaled = self.mul(normed, self.add(w, _fp(1.0)))  # (weight + 1): the "1P"
            out.append(self.add(scaled, bi))
        return out

    def softmax(self, z):
        """softmax(z) = exp(z_i) / Σ exp(z_j), via MOBIUS_GROWTH + COMP + INV.
        Subtract max first (a comparison at the boundary) for numerical range."""
        m = z[0]
        for zi in z[1:]:
            if zi > m:
                m = zi
        exps = [self.exp(self.sub(zi, m)) for zi in z]
        s = 0
        for e in exps:
            s = self.add(s, e)
        inv_s = self.div(_fp(1.0), s)
        return [self.mul(e, inv_s) for e in exps]

    def relu2(self, x):
        """Nemotron's relu^2 activation: max(0,x) then square (AMP_MOD)."""
        out = []
        for xi in x:
            r = xi if xi > 0 else 0          # max(0,x): comparison (control, boundary)
            out.append(self.mul(r, r))       # square -> AMP_MOD
        return out

    def attention(self, Q, K, V, d_head):
        """
        softmax(QK^T / sqrt(d)) V, one query row against all keys/values.
        Q: [d], K: [seq][d], V: [seq][d]. All on the substrate.
        """
        inv_sqrt_d = self.div(_fp(1.0), self.sqrt(_fp(float(d_head))))  # 1/sqrt(d) bootstrapped
        scores = []
        for k in K:
            s = self.dot(Q, k)               # Q·k
            scores.append(self.mul(s, inv_sqrt_d))
        weights = self.softmax(scores)       # attention distribution
        # weighted sum of V rows
        out = [0] * len(V[0])
        for w, v in zip(weights, V):
            for j in range(len(v)):
                out[j] = self.add(out[j], self.mul(w, v[j]))
        return out

    def braid_word(self):
        """The complete reversible operation trace of everything run (Step 6)."""
        return self.t.braid_word()

    def alpha_ok(self):
        """Step 7: the four-param integrity checksum must read 137."""
        return abs(E.ALPHA_INV / SCALE - 137) < 1


def transformer_block(eng, x, params):
    """
    One Nemotron decoder layer, exactly as modeling_nemotron.py wires it:
        h = x + attn(layernorm(x));  out = h + mlp(layernorm(h))
    `params` carries the (already fixed-point) weights for this block.
    """
    # pre-attention norm
    a = eng.layernorm1p(x, params['ln1_w'], params['ln1_b'], params['eps'])
    # self-attention (single-head here; multi-head is the same op per head)
    Q = eng.linear(a, params['q_w'])
    K = [eng.linear(a, params['k_w'])]          # one-token cache for the demo
    Vv = [eng.linear(a, params['v_w'])]
    attn = eng.attention(Q, K, Vv, params['d_head'])
    attn = eng.linear(attn, params['o_w'])
    h = [eng.add(xi, ai) for xi, ai in zip(x, attn)]   # residual
    # MLP
    b = eng.layernorm1p(h, params['ln2_w'], params['ln2_b'], params['eps'])
    up = eng.linear(b, params['up_w'])
    act = eng.relu2(up)
    down = eng.linear(act, params['down_w'])
    out = [eng.add(hi, di) for hi, di in zip(h, down)]  # residual
    return out
