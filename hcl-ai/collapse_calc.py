"""
collapse_calc.py — the GUHCT harmonic-reversible calculator as a repo
organ (contributed engine; adapted: functionality only — no GUI, no
progress callbacks, no logging surfaces; the iteration counter exists
solely as internal loop control and appears on no output).

Computation-by-collapse, GUHCT-native end to end: an expression (or a
tape program) is sampled onto the harmonic circle and handed to the
pure core (HCLCollapse below) — coherence is the state's own order
parameter by chained HCL.COMP (02_operations, component addition), the
window is the identity (the landing IS the exact mean, by transcriber
add/div on 40-digit integers), the decision is eps_w = eta*lambda^w
(01_theory:35; juj:143), and every landing carries the RESONANCE
certificate (02_operations:189) and the alpha seal. Nothing iterates
toward readiness and nothing is tuned. numpy appears only in the
ranking service further down (dj_amp_rank), which is proven identical
to the pure loop and optional.

    ./calc.sh "sin(pi/6)+sqrt(2)"
    ./calc.sh --prog 'def f(theta,tape): return tape[0]+theta' --init 1
"""
import argparse, math, cmath, re, sys, textwrap, inspect, operator
from typing import Dict, Callable

import numpy as np

# ── math-safe evaluation environment (as contributed) ───────────────────
MENV = {}
for _m in (math, cmath, operator):
    for _n in dir(_m):
        if not _n.startswith("__"):
            MENV[_n] = getattr(_m, _n)
MENV.update({
    "pi": math.pi, "tau": 2 * math.pi, "e": math.e, "ln": math.log,
    "rad": math.radians, "deg": math.degrees,
    "csc": lambda x: 1 / math.sin(x), "sec": lambda x: 1 / math.cos(x),
    "cot": lambda x: 1 / math.tan(x), "mod": lambda a, b: a % b,
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
    "range": range, "np": np,
})

TOKEN_SUBS = [
    (r"×", "*"), (r"÷", "/"),
    (r"(\d+)\s*x\s*(\d+)", r"\g<1>*\g<2>"),
    (r"(?<=[\d\)])\s*\(", r"*("),
    (r"\^", "**"),
]
_KEYWORDS = ("for|while|if|elif|else|in|and|or|not|is|def|class|with|try|"
             "except|finally|return|yield|import|global|nonlocal|lambda|"
             "pass|break|continue|assert|del|raise")


def clean(expr: str) -> str:
    for p, r in TOKEN_SUBS:
        expr = re.sub(p, r, expr)
    expr = re.sub(rf"(?<=[\d\)])\s*(?!({_KEYWORDS})\b)([A-Za-z_])",
                  r"*\2", expr)
    return expr


# ── geometric encoder z(θ) → w(θ) = z^(1/z) (as contributed) ────────────
LN1 = cmath.log(cmath.log(0.95777298))
LN2 = cmath.log(cmath.log(0.84149264))
POW1 = cmath.exp((137 / 369) * LN1)
POW2 = cmath.exp((137 / 369) * LN2)
C369 = 369 ** (1 / 137)


def _radius(theta: np.ndarray) -> np.ndarray:
    sin_t = np.sin(theta)
    cot_t = np.cos(theta) / (sin_t + 1e-12)
    return -369 + (POW1.real * sin_t * sin_t / POW2.real) + C369 * cot_t


def w_theta(theta: np.ndarray) -> np.ndarray:
    z = _radius(theta) * np.exp(1j * theta)
    lnz = np.log(np.abs(z) + 1e-12) + 1j * np.angle(z)
    return np.exp(lnz / (z + 1e-12))


# ── the collapse engine — GUHCT-native (no DCT, no Kuramoto) ─────────────
# The contributed float engine synchronized oscillators (Kuramoto) to
# decide readiness and reconstructed through a truncated DCT window.
# Both were stand-ins for laws the repo already owns, so both are gone:
#   coherence  R  = composed amplitude / total amplitude — the state's
#                   own order parameter, by chained HCL.COMP
#                   (02_operations, component addition; hcl_engine:212)
#   window        = the identity: the landing is the exact mean by
#                   transcriber add/div — no spectrum to truncate
#   decision      = eps_w = eta * lambda^w at the landing's own braid
#                   weight (juj:143; 02_operations:189) — nothing tuned
# Values cross in through to_fp (Decimal-string boundary, exact) and
# the result crosses out through from_fp for display. Same API keys.

class CollapseEngine:
    def __init__(self, dep_vec, **_legacy_ignored):
        import hcl_engine as _E2
        vals = list(dep_vec)
        self._t = _E2.HCLTranscriber
        self.dep_fp = [v if isinstance(v, int) and abs(v) > 10**20
                       else self._t.to_fp(getattr(v, 'real', v))
                       for v in vals]
        self.N = len(self.dep_fp)

    def run(self, max_iter=None):
        core = HCLCollapse(self.dep_fp).run()
        # boundary-out: the door and float callers read a plain number
        result = float(self._t.from_fp(core['result']))
        total = sum(abs(x) for x in self.dep_fp) or 1
        return dict(R=float(self._t.from_fp((core['R'] * _S) // total)),
                    k=self.N, err=float(self._t.from_fp(core['err'])),
                    result=result)


# ── evaluation surfaces (as contributed, silent) ────────────────────────
def evaluate(expr: str) -> Dict:
    expr = clean(expr)
    try:
        f = eval("lambda x:" + expr, MENV)
        f(0.0)
    except Exception as e:
        raise ValueError(f"bad expression: {e}") from None
    theta = np.linspace(1e-3, 2 * math.pi - 1e-3, 360)
    vec = np.array([f(t) for t in theta], dtype=np.complex128)
    return CollapseEngine(vec).run()


def build_function(code: str) -> Callable[[float, np.ndarray], float]:
    loc = {}
    exec(textwrap.dedent(code), MENV, loc)
    if "f" not in loc:
        raise ValueError("your code must define a function f(theta,tape)")
    if len(inspect.signature(loc["f"]).parameters) != 2:
        raise ValueError("f must have signature f(theta, tape)")
    return loc["f"]


def evaluate_prog(prog: str, init: str) -> Dict:
    f = build_function(prog)
    init_vals = [float(x.strip()) for x in init.split(",")]
    N = 360
    tape = np.zeros(N, dtype=float)
    tape[:len(init_vals)] = init_vals
    theta = np.linspace(1e-3, 2 * math.pi - 1e-3, N)
    for i, th in enumerate(theta):
        tape[i] = f(th, tape)
    return CollapseEngine(tape).run()


# ── the PURE core: collapse as cited law, zero floats ────────────────────
# Every constant and decision below is a repo law, none is chosen here:
#   values        FBit.from_scalar            hcl_engine:174
#   composition   HCL.COMP (component add)    02_operations "COMP"; hcl_engine:212
#   landing       result == exact mean        the k=N identity, computed
#                                             directly by transcriber ops
#   certificate   HCL.RESONANCE(state, w)     02_operations:189 "Stable Braid
#                                             Closure (Hamiltonian Eigenstate)":
#                                             E_ground = eta*lambda^w exact
#   collapse eps  mcl_eps(w) = 10^-w * eta    juj:143; identical to eta*lambda^w
#                                             because lambda = 1/10 (hcl_engine:65)
#   weight w      the braid length            juj:384's rule, as the head uses
#   seal          |ALPHA_INV - 137*SCALE| < SCALE   the Alpha Identity
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  'engine'))
import hcl_engine as _E
from hcl_engine import FBit as _FBit, HCL as _HCL, SCALE as _S


class HCLCollapse:
    """The calculator's collapse, composed from the laws above. Input: a
    list of exact fixed-point integers (SCALE = 10^40). Output dict keys
    match the contributed engine (result, R, k, err) so callers see one
    calculator; every value is produced by transcriber/FBit law."""

    def __init__(self, dep_fp):
        self.dep = list(dep_fp)
        self.N = len(self.dep)
        self.t = _E.HCLTranscriber()

    def run(self):
        self.t.clear()
        # composition: the ensemble as one state, by COMP chain (02's law)
        state = _FBit.from_scalar(self.dep[0])
        for X in self.dep[1:]:
            state = _HCL.COMP(state, _FBit.from_scalar(X))
        # landing: the exact mean, transcriber arithmetic only
        acc = 0
        for X in self.dep:
            acc = self.t.add(acc, X)
        landing = self.t.div(acc, self.N * _S)
        # certificate: the ground state at w = braid length (02:189)
        w = max(len(self.t.braid_log), 1)
        ground = _HCL.RESONANCE(state, w)
        eps_w = _E.HCLTranscriber().mul(_E.ETA, _pow_fp(_E.LAMBDA, w))
        alpha = abs(_E.ALPHA_INV - 137 * _S) < _S
        return dict(result=landing, R=ground.amp, k=self.N,
                    err=eps_w, alpha=alpha, w=w,
                    braid=self.t.braid_word())


def _pow_fp(X, n):
    """lambda^n by repeated fixed multiply — AMP_MOD's integer-power
    composition rule (02_operations "Operation Composition Rules")."""
    r = _S
    for _ in range(n):
        r = _E._fixed_mul(r, X)
    return r


def evaluate_pure(expr: str):
    """The expression evaluated per theta by the engine's own equation
    organ (HCLEquation, hcl_engine:518 — every op is a transcriber op),
    then landed by HCLCollapse. No float touches any value."""
    eq = _E.HCLEquation()
    N = 360                                   # tape length (format field)
    dep = []
    for i in range(N):
        # theta_i as an exact fraction of 2*pi: phase_frac = i/N of a turn
        th_fp = _E._fixed_mul((i * _S) // N, 2 * _E.PI_INT)
        # from_fp -> full-precision decimal string -> to_fp via Decimal:
        # the boundary pair round-trips theta bit-exactly (hcl_engine:328/336)
        dep.append(eq.solve(expr, x=_E.HCLTranscriber.from_fp(th_fp)).value)
    return HCLCollapse(dep).run()


# ── vectorized services for the stack (numpy-side arithmetic) ───────────
def pack_sigs(sigs, D):
    """Pack Python-int signatures (D bits each, ANY D) into a 2-D uint64
    array of ceil(D/64) words per row, little-word-first. No dimensional
    limit: D=64 packs to one word, D=288 to five, D=2048 to thirty-two —
    the same call, the same law."""
    words = (D + 63) // 64
    out = np.empty((len(sigs), words), dtype=np.uint64)
    mask = (1 << 64) - 1
    for i, s in enumerate(sigs):
        for w in range(words):
            out[i, w] = (s >> (64 * w)) & mask
    return out


def dj_amp_rank(q_sig: int, sigs_w64: np.ndarray, D: int):
    """Order candidate indices by DJ interference AMPLITUDE descending —
    amp = |2*(D - mismatch) - D| — the production law exactly (both the
    aligned and anti-aligned extremes resonate). Stable order, so equal
    amplitudes keep original index order, matching the Python loop's
    sorted(). Returns (order, amps). One vectorized pass per signature
    word (ceil(D/64) words), so every model dimension is served."""
    words = sigs_w64.shape[1]
    mask = (1 << 64) - 1
    pc = np.zeros(sigs_w64.shape[0], dtype=np.int64)
    for w in range(words):
        x = np.bitwise_xor(sigs_w64[:, w],
                           np.uint64((q_sig >> (64 * w)) & mask))
        if hasattr(np, "bitwise_count"):
            pc += np.bitwise_count(x).astype(np.int64)
        else:
            pc += np.unpackbits(x.view(np.uint8).reshape(-1, 8),
                                axis=1).sum(axis=1).astype(np.int64)
    amps = np.abs(D - 2 * pc)
    order = np.argsort(-amps, kind="stable")
    return order, amps


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--prog", type=str)
    ap.add_argument("--init", type=str)
    ap.add_argument("expr", nargs="*")
    a = ap.parse_args()
    if a.prog:
        if not a.init:
            sys.exit("--init required with --prog")
        r = evaluate_prog(a.prog, a.init)
    else:
        r = evaluate(" ".join(a.expr) if a.expr else "sin(pi/6)+sqrt(2)")
    print(f"{r['result']:.12g}")


if __name__ == "__main__":
    main()
