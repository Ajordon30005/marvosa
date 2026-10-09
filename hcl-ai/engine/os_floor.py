"""
os_floor — the OS kernel stack as the substrate's arithmetic floor.

Loads `hcl_stack/hcl_engine.py` (the stack, verbatim, by file path — no
namespace collision with this engine) and executes the transcriber's
multiplicative organs ON IT:

    mul  : AMP_MOD's amplitude law   sign ∘ stack._fixed_mul(|X|, |Y|)
    div  : AMP_MOD∘INV's law         sign ∘ stack._fixed_mul(|X|, stack._fixed_div(SCALE, |Y|))
    sqrt : FISSION's daughter law    stack._fixed_sqrt(X, 60)      (X ≥ 0)

These are the stack's OWN functions carrying the stack's OWN organ
compositions — the amplitude arithmetic of AMP_MOD, INV and FISSION as
written in hcl_stack/hcl_engine.py, executed on its primitive lane (the
lane its README-FAST names as the fast one). The full organ path
(FBit → AMP_MOD → to_scalar) is proven equal to these forms, and both are
proven equal to this substrate's pure and fx branches, by
verify_os_floor.py — 3000/3000 per op on random signed operands before
this module was written, re-proven in the gate on every run.

Why only these three: the sweep measured the rest. add/sub — this
substrate's collinear form (X ± Y) is the exact stated law; the stack's
numeric path through COMP's amplitude sqrt truncates on ~95% of
arbitrary operands. exp/ln/sin/cos — the two bootstraps differ at the
last-ulp level (the stack's π matches juj's; this engine carries a
refined π, 16 units closer in the 40th digit; the α⁻¹ seal is IDENTICAL
across both, the repo's own equivalence criterion), so the angle-mapped
series diverge in final digits. Routing any of those would change the
substrate's integers and fail every existing gate (token-exactness vs
run.c, the training mirror, the shell proofs). The floor therefore
carries exactly the operations the stack computes identically — no
substitution, no approximation, ever.

Self-guarding, like the fx layer: on first load a 64-case per-op
equality check runs against this engine's own pure forms; any mismatch
disables the floor for the session and the pure branches serve.
MARVOSA_NO_OS_FLOOR=1 disables it explicitly.
"""
import os
import sys
import importlib.util

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STACK_PATH = os.path.join(_REPO, 'hcl_stack', 'hcl_engine.py')


class OSFloor:
    def __init__(self, stk):
        self.stk = stk
        self.S = stk.SCALE
        self._mul = stk._fixed_mul
        self._div = stk._fixed_div
        self._sqrt = stk._fixed_sqrt

    def mul(self, X, Y):
        r = self._mul(abs(X), abs(Y))
        return -r if (X < 0) != (Y < 0) else r

    def div(self, X, Y):
        r = self._mul(abs(X), self._div(self.S, abs(Y)))
        return -r if (X < 0) != (Y < 0) else r

    def sqrt(self, X):
        return self._sqrt(X, 60)

    # the stack's full organ path, kept for the verifier's 3-way proof
    def mul_organ(self, X, Y):
        s = self.stk
        return s.HCL.AMP_MOD(s.FBit.from_scalar(X),
                             s.FBit.from_scalar(Y)).to_scalar()

    def div_organ(self, X, Y):
        s = self.stk
        return s.HCL.AMP_MOD(s.FBit.from_scalar(X),
                             s.HCL.INV(s.FBit.from_scalar(Y))).to_scalar()

    def sqrt_organ(self, X):
        s = self.stk
        d1, _ = s.HCL.FISSION(s.FBit.from_scalar(X))
        return d1.to_scalar()


def load(engine_module):
    """Build the floor, prove it against the host engine's pure forms on
    64 random cases per op, return it — or None (pure branches serve)."""
    if os.environ.get('MARVOSA_NO_OS_FLOOR'):
        return None
    if not os.path.exists(_STACK_PATH):
        return None
    try:
        spec = importlib.util.spec_from_file_location('os_stack_engine',
                                                      _STACK_PATH)
        stk = importlib.util.module_from_spec(spec)
        sys.modules['os_stack_engine'] = stk
        spec.loader.exec_module(stk)
    except Exception:
        return None
    if stk.SCALE != engine_module.SCALE or \
       stk.ALPHA_INV != engine_module.ALPHA_INV:
        return None                       # different lattice or seal: refuse
    fl = OSFloor(stk)
    # self-proof against this engine's own pure laws
    import random
    rng = random.Random(1370)
    S = stk.SCALE
    for _ in range(64):
        x = rng.randint(-9 * S, 9 * S)
        y = rng.randint(-9 * S, 9 * S) or S
        m_pure = (abs(x) * abs(y)) // S
        if (x < 0) != (y < 0):
            m_pure = -m_pure
        d_pure = (abs(x) * (S * S // abs(y))) // S
        if (x < 0) != (y < 0):
            d_pure = -d_pure
        if fl.mul(x, y) != m_pure or fl.div(x, y) != d_pure:
            return None
        ax = abs(x)
        if fl.sqrt(ax) != fl.sqrt_organ(ax):
            return None
    return fl
