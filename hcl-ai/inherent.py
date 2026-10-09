"""
inherent.py — THE WEIGHT OPERATOR (MST): weights without pre-training.

The thesis (docs/13): a model's weights are one point in an inherent
space the substrate already owns — the window/filter that shapes input
into output. The n-invariant law (skills/hcl-pure/references/01_theory,
05_proofs) says: never search "all n" — build the OPERATOR whose logic
does not change with n, and universality follows because only finite n
are ever instantiated. Applied here: do not FIND weights by descent over
data and do not ENUMERATE weight-space; construct the operator that,
given any demanded input->output behavior, INSTANTIATES the satisfying
weights exactly. Where demands leave freedom (the inherent remainder),
selection collapses by the substrate's own lottery — Grover's iteration
exactly as written in 04_quantum: oracle = sign flip, diffusion =
2*mean - amp, iterations floor(pi/4 * sqrt(N)) from the MCL resonance
condition — landing on the marked candidate by structure, not intuition.

Exactness lemma (proven in-repo, verify_fastpath): integer-valued
fixed-points multiply WITHOUT truncation — (a*SCALE)*(b*SCALE)//SCALE =
a*b*SCALE exactly. The operator therefore works over integer-valued
input lattices (sign/one-hot/binary patterns) with EXACT equality in the
runner's own truncating arithmetic; derivation is fraction-free integer
elimination (every interior division exact by construction), pure
composition of engine ops.

    python3 verify_inherent.py       # the proof, 05_proofs style
"""
import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, 'engine'), os.path.join(_HERE, 'port')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hcl_engine import HCLTranscriber, SCALE, ALPHA_INV, _fixed_div, _fixed_sqrt


class WeightOperator:
    """The scale-invariant operator: same lines at dim 8 and dim 288.
    derive(X, Y) instantiates W (one output row) with dot(W, x_i) == y_i
    EXACTLY for every demanded pair, over integer-valued input lattices."""

    def __init__(self):
        self.t = HCLTranscriber()

    # ── the operator ────────────────────────────────────────────────────
    def derive(self, X, Y):
        """X: m demanded inputs (each dim d) forming a UNIT-TRIANGULAR
        LATTICE FRAME — row i has X[i][i] = SCALE, X[i][j] = k*SCALE for
        j < i (any integers k), zeros above: a coordinate system of the
        space. Y: m demanded outputs (any fixed-point). Returns W (dim d,
        zeros on the free coordinates — the inherent remainder) with
        runner-dot(W, x_i) == y_i EXACTLY for every demand. Forward
        substitution in pure integers — exact ALWAYS, by construction,
        at ANY d and m: the operator's lines never change with n."""
        m, d = len(X), len(X[0])
        W = [0] * d
        for i in range(m):
            assert X[i][i] == SCALE, "unit diagonal (the frame's law)"
            s_ = Y[i]
            for j in range(i):
                kj = X[i][j] // SCALE            # lattice coefficient
                if kj:
                    s_ -= kj * W[j]              # exact: integer times int
            W[i] = s_
        return W

    # ── the runner's own arithmetic ─────────────────────────────────────
    def run(self, W, x):
        """Exactly the MST runner's op: the transcriber's fused dot."""
        return self.t.dot(x, W)

    # ── the lottery (verbatim math of 04_quantum's Grover) ──────────────
    def lottery(self, n_items, marked):
        """Iterate the whole candidate space in superposition; oracle =
        sign flip on the marked; diffusion = 2*mean - amp; iterations
        floor(pi/4 * sqrt(N)) from the MCL resonance condition. Collapse
        (argmax — the runner's own MCL selection) lands on the marked by
        structure."""
        from hcl_engine import PI_INT, _fixed_sqrt, SCALE as _S
        sqN = _fixed_sqrt(n_items * _S, 80)      # convention: R = sqrt(X*S)
        iters = max(1, (PI_INT * sqN) // (4 * _S * _S))
        amp0 = _fixed_div(SCALE, _fixed_sqrt(n_items * SCALE, 60))
        amps = [amp0] * n_items
        for _ in range(iters):
            amps[marked] = -amps[marked]                    # oracle: SHIFT(-1)
            mean = sum(amps) // n_items                     # exact collinear COMP
            amps = [2 * mean - a for a in amps]             # diffusion
        pick = max(range(n_items), key=lambda i: abs(amps[i]))
        p_marked = (amps[marked] * amps[marked]) // SCALE   # amplitude^2
        return {'pick': pick, 'iterations': iters,
                'p_marked': p_marked, 'alpha_ok': self.alpha_ok()}

    def alpha_ok(self):
        return self.t.alpha_check() if hasattr(self.t, 'alpha_check') else \
            abs(ALPHA_INV - 137 * SCALE) < SCALE


if __name__ == '__main__':
    op = WeightOperator()
    X = [[SCALE if j == i else 0 for j in range(8)] for i in range(8)]
    Y = [(i + 1) * SCALE // 7 for i in range(8)]
    W = op.derive(X, Y)
    print("derived W (no training):", [w for w in W[:4]], "…")
    print("exact on demand 3:", op.run(W, X[3]) == Y[3])
    print("lottery:", op.lottery(64, 41))
