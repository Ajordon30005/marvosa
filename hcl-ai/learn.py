"""
learn.py — TRAINING on the substrate: the executable form of
docs/11-training-on-the-substrate.md.

⛔ READ docs/11 (the proof) and hcl-ai/RUNMODEL_USAGE.md FIRST.

Every gradient below is a composition of the ten primitives per the adjoint
table (docs/11, Theorem 1), applied by walking the forward computation in
reverse (Theorem 2 — the braid read backwards, realized here as cached
activations at tensor granularity). The optimizer's every constant derives
from the four params (Theorem 3): learning rate γ·λᵏ, reward gate e^(−β·H),
decay by η. Training state persists as the one α-tagged line (Theorem 4)
via the fold cycle. Zero new math; zero floats in the value path; the only
boundary crossings are the same ones inference uses.

    from learn import Trainer
    t = Trainer(model)                      # model: chatmodel.StandardModel
    t.step("Once upon a time, there was a little girl named Lily.")
    t.save_checkpoint(path); t.line()       # the trained model as ONE line
"""

import sys, os, struct

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, 'engine'), os.path.join(_HERE, 'port')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from chatmodel import StandardModel, BOS, EOS          # the proven runner
from nemotron_hcl import _fp, _val                     # boundary (verbatim)
import hcl_engine as E                                 # four params live here


def _lambda_pow(k: int) -> int:
    """λᵏ as fixed-point, by repeated AMP_MOD of the param itself."""
    v = E.SCALE
    for _ in range(k):
        v = E._fixed_mul(v, E.LAMBDA)
    return v


class Trainer:
    """Exact-arithmetic gradient descent for a llama2c model on the substrate.

    grads are dicts mirroring the model's weight structure; every entry is a
    fixed-point integer produced by engine ops only."""

    def __init__(self, model: StandardModel, k_stratum: int = 2):
        self.m = model
        self.e = model.eng
        self.c = model.cfg
        # Theorem 3: lr = γ·λᵏ — derived, never chosen from outside.
        # k selects the stratum: k=1 (γλ≈0.046) can overshoot on a single
        # short example (verified: identical overshoot in the float mirror —
        # the surface, not the substrate); k=2 (γλ²≈0.0046) descends stably.
        self.LR = E._fixed_mul(E.GAMMA, _lambda_pow(k_stratum))
        self.BETA = E.BETA
        self.ONE = _fp(1.0)
        self.braid_ops = 0          # cumulative trace length across ticks
        self._mark = self.e.t.braid_len

    def _tick(self):
        """Bound the in-RAM trace exactly as inference does: record the
        braid length (the transcriber's own counter), then its clear(). The
        tape Theorem 2 consumes is the cached activations; the count
        preserves the audit."""
        t = self.e.t
        self.braid_ops += t.braid_len - self._mark
        self._mark = t.braid_len
        t.clear()

    # ── tape-cached forward (same engine calls as inference) ────────────
    def _forward_tape(self, toks):
        """Full-sequence causal forward over `toks`, caching every activation
        the reverse walk consumes. Returns (logits_per_pos, tape)."""
        e, m, c = self.e, self.m, self.c
        D, HS, KD = c['dim'], c['head_size'], c['kv_dim']
        H, KV, L = c['n_heads'], c['n_kv_heads'], c['n_layers']
        n = len(toks)
        tape = {'toks': toks, 'x0': [], 'layers': [dict() for _ in range(L)]}

        # RoPE cos/sin per position (cached for the transposed rotation)
        tape['rope'] = []
        for pos in range(n):
            cs = []
            for j in range(HS // 2):
                val = e.mul(_fp(float(pos)), m.inv_freq[j])
                pf = e.div(val, 2 * E.PI_INT) % E.SCALE
                cs.append((e.t.cos(pf), e.t.sin(pf)))
            tape['rope'].append(cs)

        def rot(vec, pos, upto, sign=+1):
            for i in range(0, upto, 2):
                cr, ci = tape['rope'][pos][(i % HS) // 2]
                if sign < 0:
                    ci = e.sub(0, ci)
                v0, v1 = vec[i], vec[i + 1]
                vec[i]     = e.sub(e.mul(v0, cr), e.mul(v1, ci))
                vec[i + 1] = e.add(e.mul(v0, ci), e.mul(v1, cr))

        xs = [list(m.emb[t]) for t in toks]          # residual stream
        tape['x0'] = [list(x) for x in xs]
        for l in range(L):
            T = tape['layers'][l]
            T['x_in'] = [list(x) for x in xs]
            # rmsnorm 1
            T['n1'] = [self._rms_f(x, m.rms_att[l]) for x in xs]
            xb = [t[0] for t in T['n1']]
            # q k v
            T['q'] = [[e.dot(v, r) for r in m.wq[l]] for v in xb]
            T['k'] = [[e.dot(v, r) for r in m.wk[l]] for v in xb]
            T['v'] = [[e.dot(v, r) for r in m.wv[l]] for v in xb]
            T['q_pre'] = [list(q) for q in T['q']]
            T['k_pre'] = [list(k) for k in T['k']]
            for pos in range(n):
                rot(T['q'][pos], pos, D)
                rot(T['k'][pos], pos, KD)
            # attention (causal, per head, cached probs)
            per = H // KV
            inv_s = e.div(self.ONE, e.sqrt(_fp(float(HS))))
            T['probs'] = [[None] * H for _ in range(n)]
            att = [[0] * D for _ in range(n)]
            for pos in range(n):
                for h in range(H):
                    g = h // per
                    Q = T['q'][pos][h * HS:(h + 1) * HS]
                    sc = []
                    for t_ in range(pos + 1):
                        s = e.dot(Q, T['k'][t_][g * HS:(g + 1) * HS])
                        sc.append(e.mul(s, inv_s))
                    mx = sc[0]
                    for s in sc[1:]:
                        if s > mx:
                            mx = s
                    ws = [e.exp(e.sub(s, mx)) for s in sc]
                    tot = 0
                    for w_ in ws:
                        tot = e.add(tot, w_)
                    it = e.div(self.ONE, tot)
                    p = [e.mul(w_, it) for w_ in ws]
                    T['probs'][pos][h] = p
                    for t_, pw in enumerate(p):
                        Vv = T['v'][t_][g * HS:(g + 1) * HS]
                        for i in range(HS):
                            att[pos][h * HS + i] = e.add(
                                att[pos][h * HS + i], e.mul(pw, Vv[i]))
            T['att'] = att
            self._tick()
            proj = [[e.dot(a, r) for r in m.wo[l]] for a in att]
            xs = [[e.add(a, b) for a, b in zip(x, p)] for x, p in zip(xs, proj)]
            T['x_mid'] = [list(x) for x in xs]
            # rmsnorm 2 + swiglu
            T['n2'] = [self._rms_f(x, m.rms_ffn[l]) for x in xs]
            xb2 = [t[0] for t in T['n2']]
            T['h1'] = [[e.dot(v, r) for r in m.w1[l]] for v in xb2]
            T['h3'] = [[e.dot(v, r) for r in m.w3[l]] for v in xb2]
            T['sig'] = []
            hb = []
            for h1, h3 in zip(T['h1'], T['h3']):
                sg = [e.div(self.ONE, e.add(self.ONE, e.exp(e.sub(0, a))))
                      for a in h1]
                T['sig'].append(sg)
                hb.append([e.mul(e.mul(a, s), b)
                           for a, s, b in zip(h1, sg, h3)])
            T['hb'] = hb
            mlp = [[e.dot(v, r) for r in m.w2[l]] for v in hb]
            xs = [[e.add(a, b) for a, b in zip(x, p)] for x, p in zip(xs, mlp)]
            self._tick()
        tape['nf'] = [self._rms_f(x, m.rms_final) for x in xs]
        xf = [t[0] for t in tape['nf']]
        tape['xf'] = xf
        logits = [[e.dot(x, r) for r in m.wcls] for x in xf]
        self._tick()
        return logits, tape

    def _rms_f(self, x, w):
        """rmsnorm forward returning (y, cache) — cache carries what the
        adjoint consumes: x, inv, and Σ(w·g·x) ingredients."""
        e = self.e
        ss = 0
        for xi in x:
            ss = e.add(ss, e.mul(xi, xi))
        ss = e.add(e.mul(ss, self.m.inv_dim), self.m.EPS)
        inv = e.div(self.ONE, e.sqrt(ss))
        y = [e.mul(e.mul(wi, xi), inv) for wi, xi in zip(w, x)]
        return y, (list(x), inv)

    def _rms_b(self, g, w, cache, gW):
        """rmsnorm adjoint: dW += g·x·inv ; dx = inv·(w·g) − x·inv³·Σ(w·g·x)/n"""
        e = self.e
        x, inv = cache
        n_inv = self.m.inv_dim
        a = [e.mul(wi, gi) for wi, gi in zip(w, g)]
        s = 0
        for ai, xi in zip(a, x):
            s = e.add(s, e.mul(ai, xi))
        inv3s = e.mul(e.mul(e.mul(inv, inv), inv), e.mul(s, n_inv))
        dx = [e.sub(e.mul(inv, ai), e.mul(xi, inv3s)) for ai, xi in zip(a, x)]
        for i, (gi, xi) in enumerate(zip(g, x)):
            gW[i] = e.add(gW[i], e.mul(e.mul(gi, xi), inv))
        return dx

    # ── loss + full backward (Theorem 2: the reverse walk) ──────────────
    def forward_backward(self, toks, target_weights=None):
        """Cross-entropy over next-token targets; returns (weighted mean
        loss_fp, grads) with grads mirroring every weight tensor.

        target_weights: optional fixed-point weight per POSITION (length n;
        weight for position p applies to predicting toks[p+1]). Default: all
        ONE — the unweighted mean, byte-identical to the original behavior.
        This is the stratification channel (docs/11 §8): external targets at
        weight 1, the model's own self-talk targets one λ-rung deeper —
        w-stratified experience, the theory's own scale ladder."""
        e, m, c = self.e, self.m, self.c
        D, HS, KD = c['dim'], c['head_size'], c['kv_dim']
        H, KV, L = c['n_heads'], c['n_kv_heads'], c['n_layers']
        n = len(toks)
        logits, tape = self._forward_tape(toks)

        # loss = Σ w_pos·(logsumexp(z) − z_target) / Σ w_pos
        # dlogits = w_pos·(softmax(z) − onehot(target)) / Σ w_pos
        Z = len(m.wcls)
        if target_weights is None:
            target_weights = [self.ONE] * (n - 1)
        wsum = 0
        for w_ in target_weights[:n - 1]:
            wsum = e.add(wsum, w_)
        inv_cnt = e.div(self.ONE, wsum)
        loss = 0
        dlog = [[0] * Z for _ in range(n)]
        for pos in range(n - 1):
            wp = e.mul(target_weights[pos], inv_cnt)
            if wp == 0:
                continue
            tgt = toks[pos + 1]
            z = logits[pos]
            mx = z[0]
            for v in z[1:]:
                if v > mx:
                    mx = v
            ex = [e.exp(e.sub(v, mx)) for v in z]
            tot = 0
            for w_ in ex:
                tot = e.add(tot, w_)
            lse = e.add(e.t.ln(tot), mx)              # LOG_EXTRACT ∘ COMP
            loss = e.add(loss, e.mul(e.sub(lse, z[tgt]), wp))
            it = e.div(self.ONE, tot)
            for j in range(Z):
                p = e.mul(ex[j], it)
                if j == tgt:
                    p = e.sub(p, self.ONE)
                dlog[pos][j] = e.mul(p, wp)

        G = self._zero_grads()
        # lm_head (tied):  dWcls[j] += dlog[j]·xf ;  dxf += dlog[j]·Wcls[j]
        dxs = [[0] * D for _ in range(n)]
        for pos in range(n - 1):
            xf = tape['xf'][pos]
            for j in range(Z):
                gj = dlog[pos][j]
                if gj == 0:
                    continue
                row = m.wcls[j]
                gr = G['emb'][j]
                for i in range(D):
                    gr[i] = e.add(gr[i], e.mul(gj, xf[i]))
                    dxs[pos][i] = e.add(dxs[pos][i], e.mul(gj, row[i]))
        self._tick()
        # final rmsnorm
        dxs = [self._rms_b(dxs[p], m.rms_final, tape['nf'][p][1],
                           G['rms_final']) for p in range(n)]
        self._tick()

        def mat_b(dy_rows, x_rows, W, gW):
            """y = W·x rows. dW += dy⊗x ; dx = Wᵀ·dy — AMP_MOD/COMP only."""
            dxr = []
            for dy, x in zip(dy_rows, x_rows):
                dx = [0] * len(x)
                for r_i, gy in enumerate(dy):
                    if gy == 0:
                        continue
                    row, grow = W[r_i], gW[r_i]
                    for j_i in range(len(x)):
                        grow[j_i] = e.add(grow[j_i], e.mul(gy, x[j_i]))
                        dx[j_i] = e.add(dx[j_i], e.mul(gy, row[j_i]))
                dxr.append(dx)
            return dxr

        for l in range(L - 1, -1, -1):
            T = tape['layers'][l]
            # mlp: x = x_mid + W2·hb
            d_hb = mat_b(dxs, T['hb'], m.w2[l], G['w2'][l])
            d_h1, d_h3 = [], []
            for pos in range(n):
                dh1p, dh3p = [], []
                for a, s, b, gh in zip(T['h1'][pos], T['sig'][pos],
                                       T['h3'][pos], d_hb[pos]):
                    a_s = e.mul(a, s)
                    dh3p.append(e.mul(gh, a_s))
                    # d/da [a·σ(a)] = σ + a·σ·(1−σ)
                    das = e.add(s, e.mul(a_s, e.sub(self.ONE, s)))
                    dh1p.append(e.mul(e.mul(gh, b), das))
                d_h1.append(dh1p)
                d_h3.append(dh3p)
            xb2 = [t[0] for t in T['n2']]
            dxb2 = mat_b(d_h1, xb2, m.w1[l], G['w1'][l])
            dxb2b = mat_b(d_h3, xb2, m.w3[l], G['w3'][l])
            dxb2 = [[e.add(a, b) for a, b in zip(r1, r2)]
                    for r1, r2 in zip(dxb2, dxb2b)]
            d_mid = [self._rms_b(dxb2[p], m.rms_ffn[l], T['n2'][p][1],
                                 G['rms_ffn'][l]) for p in range(n)]
            dxs = [[e.add(a, b) for a, b in zip(r1, r2)]
                   for r1, r2 in zip(dxs, d_mid)]      # + residual passthrough
            self._tick()

            # attention: x_mid = x_in + Wo·att
            d_att = mat_b(dxs, T['att'], m.wo[l], G['wo'][l])
            per = H // KV
            inv_s = e.div(self.ONE, e.sqrt(_fp(float(HS))))
            dq = [[0] * D for _ in range(n)]
            dk = [[0] * KD for _ in range(n)]
            dv = [[0] * KD for _ in range(n)]
            for pos in range(n):
                for h in range(H):
                    g_ = h // per
                    p = T['probs'][pos][h]
                    da = d_att[pos][h * HS:(h + 1) * HS]
                    # dV[t] += p_t·da ; dp_t = da·V[t]
                    dp = []
                    for t_, pw in enumerate(p):
                        Vv = T['v'][t_][g_ * HS:(g_ + 1) * HS]
                        acc = 0
                        for i in range(HS):
                            dv[t_][g_ * HS + i] = e.add(
                                dv[t_][g_ * HS + i], e.mul(pw, da[i]))
                            acc = e.add(acc, e.mul(da[i], Vv[i]))
                        dp.append(acc)
                    # softmax adjoint: ds_t = p_t·(dp_t − Σ dp·p)
                    dot_pp = 0
                    for a_, b_ in zip(dp, p):
                        dot_pp = e.add(dot_pp, e.mul(a_, b_))
                    Q = T['q'][pos][h * HS:(h + 1) * HS]
                    for t_ in range(pos + 1):
                        ds = e.mul(p[t_], e.sub(dp[t_], dot_pp))
                        ds = e.mul(ds, inv_s)
                        K = T['k'][t_][g_ * HS:(g_ + 1) * HS]
                        for i in range(HS):
                            dq[pos][h * HS + i] = e.add(
                                dq[pos][h * HS + i], e.mul(ds, K[i]))
                            dk[t_][g_ * HS + i] = e.add(
                                dk[t_][g_ * HS + i], e.mul(ds, Q[i]))
            # transpose-rotate dq, dk back (rotation adjoint = rotate by −θ)
            for pos in range(n):
                for vec, upto in ((dq[pos], D), (dk[pos], KD)):
                    for i in range(0, upto, 2):
                        cr, ci = tape['rope'][pos][(i % HS) // 2]
                        nci = e.sub(0, ci)
                        v0, v1 = vec[i], vec[i + 1]
                        vec[i]     = e.sub(e.mul(v0, cr), e.mul(v1, nci))
                        vec[i + 1] = e.add(e.mul(v0, nci), e.mul(v1, cr))
            self._tick()
            xb = [t[0] for t in T['n1']]
            dxb = mat_b(dq, xb, m.wq[l], G['wq'][l])
            dxb2 = mat_b(dk, xb, m.wk[l], G['wk'][l])
            dxb3 = mat_b(dv, xb, m.wv[l], G['wv'][l])
            dxb = [[e.add(e.add(a, b), c_) for a, b, c_ in zip(r1, r2, r3)]
                   for r1, r2, r3 in zip(dxb, dxb2, dxb3)]
            d_in = [self._rms_b(dxb[p], m.rms_att[l], T['n1'][p][1],
                                G['rms_att'][l]) for p in range(n)]
            dxs = [[e.add(a, b) for a, b in zip(r1, r2)]
                   for r1, r2 in zip(dxs, d_in)]
            self._tick()

        # embedding gather (tied with lm_head; both flow into G['emb'])
        for pos, t_ in enumerate(toks):
            gr = G['emb'][t_]
            for i in range(D):
                gr[i] = e.add(gr[i], dxs[pos][i])
        return loss, G

    def _zero_grads(self):
        m, c = self.m, self.c
        L = c['n_layers']
        z = lambda rows: [[0] * len(r) for r in rows]
        return {
            'emb': z(m.emb),
            'rms_att': [[0] * len(m.rms_att[l]) for l in range(L)],
            'rms_ffn': [[0] * len(m.rms_ffn[l]) for l in range(L)],
            'rms_final': [0] * len(m.rms_final),
            'wq': [z(m.wq[l]) for l in range(L)],
            'wk': [z(m.wk[l]) for l in range(L)],
            'wv': [z(m.wv[l]) for l in range(L)],
            'wo': [z(m.wo[l]) for l in range(L)],
            'w1': [z(m.w1[l]) for l in range(L)],
            'w2': [z(m.w2[l]) for l in range(L)],
            'w3': [z(m.w3[l]) for l in range(L)],
        }

    # ── Theorem 3: the step — COMP ∘ SHIFT, rate γ·λᵏ, reward e^(−β·H) ──
    def apply(self, G, gate=None):
        e = self.e
        lr = self.LR if gate is None else e.mul(self.LR, gate)
        def upd(W, gW):
            for row, grow in zip(W, gW):
                for i in range(len(row)):
                    if grow[i]:
                        row[i] = e.sub(row[i], e.mul(lr, grow[i]))
        m, L = self.m, self.c['n_layers']
        upd(m.emb, G['emb'])
        upd([m.rms_final], [G['rms_final']])
        for l in range(L):
            upd([m.rms_att[l]], [G['rms_att'][l]])
            upd([m.rms_ffn[l]], [G['rms_ffn'][l]])
            for nm in ('wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3'):
                upd(getattr(m, nm)[l], G[nm][l])

    def step(self, text, reward=None):
        """One example step. `reward=None`: pure examples channel.
        Otherwise gate the step with the MCL Boltzmann weight e^(−β·H),
        H = −reward (good outcomes ≈ full step, bad exponentially damped)."""
        e = self.e
        toks = self.m.tok.encode(text, bos=True)
        loss, G = self.forward_backward(toks)
        gate = None
        if reward is not None:
            H = e.sub(0, _fp(float(reward)))
            gate = e.exp(e.sub(0, e.mul(self.BETA, H)))
        self.apply(G, gate)
        self._tick()
        assert e.alpha_ok()
        braid, self.braid_ops = self.braid_ops, 0
        return {'loss': float(_val(loss)), 'braid_ops': braid,
                'alpha_ok': True, 'tokens': len(toks)}

    # ── Theorem 4: the fold cycle — the trained model as ONE line ───────
    def save_checkpoint(self, path):
        """Write the CURRENT weights as a genuine llama2c checkpoint
        (the model's own format; F32 encode is the sanctioned out-crossing,
        same status as text display)."""
        m, c = self.m, self.c
        hdr = struct.pack('<7i', c['dim'], c['hidden_dim'], c['n_layers'],
                          c['n_heads'], c['n_kv_heads'],
                          c['vocab_size'] if c['shared_classifier']
                          else -c['vocab_size'], c['seq_len'])
        HS = c['head_size']
        def flat(rows):
            return [x for r in rows for x in r]
        parts = [flat(m.emb)]
        for nm in ('rms_att',): parts.append(flat(m.rms_att))
        for nm in ('wq', 'wk', 'wv', 'wo'):
            parts.append([x for l in getattr(m, nm) for x in flat(l)])
        parts.append(flat(m.rms_ffn))
        for nm in ('w1', 'w2', 'w3'):
            parts.append([x for l in getattr(m, nm) for x in flat(l)])
        parts.append(list(m.rms_final))
        # freq tables (this v1 checkpoint computes RoPE on the fly; run.c
        # skips these bytes — regenerate them with the ENGINE's own
        # PHASE_COS/PHASE_SIN, the same composition the forward uses)
        e = self.e
        fcr, fci = [], []
        for pos in range(c['seq_len']):
            for j in range(HS // 2):
                val = e.mul(_fp(float(pos)), m.inv_freq[j])
                pf = e.div(val, 2 * E.PI_INT) % E.SCALE
                fcr.append(e.t.cos(pf))
                fci.append(e.t.sin(pf))
        e.t.clear()
        parts += [fcr, fci]
        with open(path, 'wb') as f:
            f.write(hdr)
            for p in parts:
                f.write(struct.pack(f'<{len(p)}f',
                                    *[float(_val(v)) for v in p]))
        return path

    def fold_line(self, path):
        """checkpoint → ModelMemory → the one α-tagged line (Theorem 4)."""
        from largemodel import ModelMemory
        mm = ModelMemory(chunk=256 * 1024)
        mm.ingest_file(path)
        assert mm.alpha_ok()
        return mm.line()
