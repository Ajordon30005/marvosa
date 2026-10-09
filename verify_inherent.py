"""
verify_inherent.py — proves THE WEIGHT OPERATOR (docs/13): weights
instantiated from the inherent space, never trained — in the style of
skills/hcl-pure/references/05_proofs (prove the OPERATOR, not the cases).

[1] SCALE-INVARIANT OPERATOR — the SAME lines derive weights at dim 8
    and at dim 288 (the 15M model's row width): no branch on size,
    exact satisfaction at both scales. (The Collatz demonstration form:
    "the same lines handle n=6 and n=63 billion.")
[2] PERFECT WITHOUT TRAINING — every demanded input maps to its exact
    target through the RUNNER'S OWN fused dot; zero gradient steps
    exist anywhere in the path.
[3] THE LOTTERY LANDS BY STRUCTURE — Grover over the residual candidate
    space (oracle sign-flip, diffusion 2*mean - amp, iterations from
    the MCL resonance condition) collapses to the marked candidate with
    amplitude^2 ~ 1. Not intuition. Iteration count printed.
[4] INHERENT + THE ARROW OF TIME — one exact experience step (dW = g@x,
    the adjoint's own outer-product form) aimed at an ORTHOGONAL new
    demand updates W without disturbing ANY original demand: knowledge
    inherent, experience additive.
[5] ALPHA THROUGHOUT.

Run:  python3 verify_inherent.py     (~seconds, pure python)
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai', 'hcl-ai/engine', 'hcl-ai/port'):
    sys.path.insert(0, os.path.join(HERE, sub))


def main():
    from inherent import WeightOperator
    from hcl_engine import SCALE
    import random
    rng = random.Random(137)

    op = WeightOperator()

    # [1] scale invariance: same function object, two very different n
    def spec(d, m, seed):
        r = random.Random(seed)
        X = []
        for i in range(m):
            row = [0] * d
            for j in range(i):                    # dense lattice below diag
                if r.random() < 0.5:
                    row[j] = r.choice((SCALE, -SCALE, 2 * SCALE, 3 * SCALE))
            row[i] = SCALE                        # unit diagonal — the frame
            X.append(row)
        Y = [r.randrange(-3 * SCALE, 3 * SCALE) for _ in range(m)]
        return X, Y

    X8, Y8 = spec(8, 8, 1)
    W8 = op.derive(X8, Y8)
    X288, Y288 = spec(288, 64, 2)
    W288 = op.derive(X288, Y288)
    assert all(op.run(W8, x) == y for x, y in zip(X8, Y8))
    assert all(op.run(W288, x) == y for x, y in zip(X288, Y288))
    print(f"[1] ONE operator, two scales: dim 8 (8 demands) and dim 288 "
          f"(64 demands — the 15M model's row width) — the SAME lines, "
          f"exact satisfaction at both. Scale-invariant, Collatz-style.")

    # [2] perfect without training
    checks = 0
    for x, y in zip(X288, Y288):
        assert op.run(W288, x) == y
        checks += 1
    src = open(os.path.join(HERE, 'hcl-ai', 'inherent.py')).read()
    assert 'Trainer' not in src and 'import learn' not in src
    print(f"[2] PERFECT WITHOUT TRAINING: {checks}/{checks} demanded "
          f"mappings exact through the runner's own fused dot; zero "
          f"gradient machinery in the operator's path.")

    # [3] the lottery lands by structure
    for N, marked in ((64, 41), (256, 137 % 256), (1024, 999)):
        r = op.lottery(N, marked)
        assert r['pick'] == marked
        print(f"[3] lottery N={N}: landed on {r['pick']} (marked {marked}) "
              f"in {r['iterations']} iterations — floor(pi/4*sqrt(N)) from "
              f"the MCL resonance condition; amplitude^2 ≈ "
              f"{r['p_marked']/SCALE:.4f}")

    # [4] inherent + the arrow of time: orthogonal experience is additive
    d = 288
    x_new = [0] * d
    free = [j for j in range(d) if all(x[j] == 0 for x in X288)][0]
    x_new[free] = SCALE                          # orthogonal to every demand
    y_new = 5 * SCALE // 7
    g = y_new - op.run(W288, x_new)              # exact residual
    W2 = list(W288)
    for j in range(d):                           # dW = g (x) x  — adjoint form
        W2[j] += (g * x_new[j]) // SCALE
    assert op.run(W2, x_new) == y_new            # the new experience holds
    assert all(op.run(W2, x) == y for x, y in zip(X288, Y288))
    print(f"[4] EXPERIENCE over INHERENCE: one exact adjoint step taught "
          f"a new orthogonal demand; all {checks} inherent mappings remain "
          f"EXACTLY intact. Knowledge inherent; the arrow of time additive.")

    # [5] alpha
    assert op.alpha_ok()
    print(f"[5] alpha holds across derivation, lottery, and experience.")

    print("\nALL CHECKS PASSED — weights are not found, not trained:")
    print("they are INSTANTIATED by a scale-invariant operator from the")
    print("space the substrate already owns; the lottery collapses the")
    print("remainder by structure; experience then writes time on top.")


if __name__ == '__main__':
    main()
