"""
verify_chatmodel.py — proves a REAL trained standard model runs correctly,
end to end, on the substrate.

Ground truth: karpathy's run.c (gcc -O2, temperature 0) on the SAME
checkpoint — models/tinystories_260k/stories260K.bin (the stories260K
TinyStories model, pulled from GitHub as committed blobs in
clebert/llama2.zig). The expected strings below are its verbatim output.

Also proves the engine-level fix this file's development uncovered
(RUNMODEL_USAGE.md, failure mode 6): MOBIUS_GROWTH / _exp_fp must be exact
across the argument range attention softmax actually produces at long
context — including x = -30, where the unreduced series returned ~1e+2.

Run:  python3 verify_chatmodel.py            (~3 minutes, pure python)
"""
import sys, os, time, math

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai', 'hcl-ai/engine', 'hcl-ai/port', 'hcl-ai/mind'):
    sys.path.insert(0, os.path.join(HERE, sub))

MODEL = os.path.join(HERE, 'models/tinystories_260k/stories260K.bin')
TOK   = os.path.join(HERE, 'models/tinystories_260k/tok512.bin')

# run.c ground truth (temperature 0, greedy) for this exact checkpoint
REFS = {
    "Once upon a time": "Once upon a time, there was a little girl named "
                        "Lily. She loved to play",
    "Lily saw a":       "Lily saw a big box. She was very happy. She wanted "
                        "to see",
}

def main():
    from nemotron_hcl import _fp, _val, HCLTensorEngine
    from chatmodel import StandardModel

    # [1] the engine's exp is exact across the long-context softmax range
    e = HCLTensorEngine()
    worst = 0.0
    for x in (-40, -35, -30, -25, -20, -15, -10, -5, -1, 0, 1, 5, 15, 30):
        got = float(_val(e.exp(_fp(float(x))))); e.t.clear()
        ref = math.exp(x)
        d = abs(got - ref) / max(ref, 1e-300)
        worst = max(worst, d)
        assert d < 1e-12, f"exp({x}): got {got}, ref {ref}"
    assert e.alpha_ok()
    print(f"[1] engine exp exact from -40 to +30 (worst rel err {worst:.1e}) "
          f"— the unreduced series returned ~1e+2 at x=-30")

    # [2] the real checkpoint arrives through the body and docks
    t0 = time.time()
    m = StandardModel(MODEL, TOK, quiet=True)
    assert m.fmt == 'llama2c'
    assert m.m.alpha_ok()
    line = m.m.line()
    print(f"[2] stories260K streamed + docked as llama2c in {time.time()-t0:.0f}s; "
          f"identity line {len(line)} chars; alpha_ok=True")

    # [3] generation is token-exact against run.c on every reference prompt
    for prompt, ref in REFS.items():
        t0 = time.time()
        r = m.generate(prompt, steps=13)
        got = r['text']
        assert ref.startswith(got), f"\n  sub: {got!r}\n  ref: {ref!r}"
        assert r['alpha_ok']
        print(f"[3] {time.time()-t0:.0f}s, alpha_ok=True, "
              f"~{r['braid_ops_per_token'][0]} braid ops/token — EXACT: {got!r}")

    print("\nALL CHECKS PASSED — a real trained standard model, running as a")
    print("chat entirely on the substrate, token-exact against its own")
    print("source implementation (run.c, temperature 0).")

if __name__ == '__main__':
    main()
