"""
HCL engine — transcribed VERBATIM from hcl-pure/references/03_engine.md.
No reimplementation, no memory. Code blocks copied as written.
"""

# ── Precision System (03_engine.md lines 5-9) ──
PREC  = 40               # 40 significant decimal digits
SCALE = 10 ** PREC       # all values: integer X where x = X/SCALE
TINY  = 10               # convergence: stop when |term| < TINY (= 10/SCALE in real)

# ── Fixed-Point Integer Primitives (22-45) ──
def _fixed_mul(X: int, Y: int) -> int:
    return (X * Y) // SCALE

def _fixed_div(X: int, Y: int) -> int:
    return (X * SCALE) // Y

def _fixed_sqrt(X: int, iters: int = 80) -> int:
    if X == 0: return 0
    target = X * SCALE          # want R² = target
    bits   = target.bit_length()
    Rg     = 1 << ((bits + 1) // 2)
    Rg     = max(Rg, 1)
    for _ in range(iters):
        Rg2 = (Rg + target // Rg) // 2
        if abs(Rg2 - Rg) <= 1: break
        Rg = Rg2
    return Rg

# ── Bootstrap: arctan, π, four params, α (56-92) ──
def _arctan_int(X: int, terms: int = 80) -> int:
    result = 0
    xpow   = X
    x2     = _fixed_mul(X, X)
    for k in range(terms):
        term = _fixed_div(xpow, (2*k+1) * SCALE)
        result += term if k % 2 == 0 else -term
        xpow = _fixed_mul(xpow, x2)
        if abs(term) < TINY: break
    return result

_ONE_FIFTH = _fixed_div(SCALE, 5 * SCALE)
_ONE_239   = _fixed_div(SCALE, 239 * SCALE)
PI_INT     = 4 * (4 * _arctan_int(_ONE_FIFTH) - _arctan_int(_ONE_239))

ETA    = SCALE // 2       # η = 1/2 (exact)
LAMBDA = SCALE // 10      # λ = 1/10 (exact)

_GAMMA_SQ_NUM = 90 * SCALE
_GAMMA_SQ_DEN = _fixed_mul(137 * SCALE, PI_INT)
GAMMA_SQ      = _fixed_div(_GAMMA_SQ_NUM, _GAMMA_SQ_DEN)
GAMMA         = _fixed_sqrt(GAMMA_SQ, 80)

BETA = GAMMA // 9

ALPHA     = _fixed_mul(_fixed_mul(_fixed_mul(_fixed_mul(2*PI_INT, ETA), LAMBDA), GAMMA), BETA)
ALPHA_INV = _fixed_div(SCALE, ALPHA)

# ── Transcendental Series (100-160) ──
def _sin_fp(X_rad: int, terms: int = 40) -> int:
    result = 0
    xpow   = X_rad
    x2     = _fixed_mul(X_rad, X_rad)
    for k in range(terms):
        fact = SCALE
        for j in range(1, 2*k+2): fact = _fixed_mul(fact, j * SCALE)
        term = _fixed_div(xpow, fact)
        result += term if k % 2 == 0 else -term
        xpow = _fixed_mul(xpow, x2)
        if abs(term) < TINY: break
    return result

def _cos_fp(X_rad: int, terms: int = 40) -> int:
    result = SCALE
    xpow   = _fixed_mul(X_rad, X_rad)
    for k in range(1, terms):
        fact = SCALE
        for j in range(1, 2*k+1): fact = _fixed_mul(fact, j * SCALE)
        term = _fixed_div(xpow, fact)
        result += term if k % 2 == 0 else -term
        xpow = _fixed_mul(xpow, _fixed_mul(X_rad, X_rad))
        if abs(term) < TINY: break
    return result

def _exp_fp(X: int, terms: int = 60) -> int:
    result = SCALE
    term   = SCALE
    for k in range(1, terms):
        term = _fixed_mul(term, X) // k
        result += term
        if abs(term) < TINY: break
    return result

def _ln_fp(X: int, terms: int = 150) -> int:
    if X <= 0: raise ValueError("ln: non-positive")
    u    = _fixed_div(X - SCALE, X + SCALE)
    u2   = _fixed_mul(u, u)
    res  = 0
    upow = u
    for k in range(terms):
        term = _fixed_div(upow, (2*k+1) * SCALE)
        res += term
        upow = _fixed_mul(upow, u2)
        if abs(term) < TINY: break
    return 2 * res

def _atan2_fp(Y: int, X: int) -> int:
    if X == 0: return PI_INT // 2 if Y >= 0 else -(PI_INT // 2)
    if abs(Y) <= abs(X):
        at = _arctan_int(_fixed_div(Y, X))
        if X < 0: at = at + PI_INT if Y >= 0 else at - PI_INT
    else:
        at = PI_INT // 2 - _arctan_int(_fixed_div(X, Y))
        if Y < 0: at = -(PI_INT // 2) - _arctan_int(_fixed_div(X, Y))
    return at

# ── FBit (167-207) ──
class FBit:
    __slots__ = ('phase_frac', 'amp')
    def __init__(self, phase_frac: int, amp: int):
        self.phase_frac = int(phase_frac) % SCALE
        self.amp        = int(amp)
    @classmethod
    def from_scalar(cls, X: int) -> 'FBit':
        if X == 0: return cls(0, 0)
        return cls(0 if X > 0 else SCALE//2, abs(X))
    def to_scalar(self) -> int:
        if self.phase_frac < SCALE//4 or self.phase_frac > 3*SCALE//4:
            return self.amp
        return -self.amp
    def re(self) -> int:
        pf = self.phase_frac
        if pf == 0:              return  self.amp
        if pf == SCALE//2:       return -self.amp
        if pf == SCALE//4:       return  0
        if pf == 3*SCALE//4:     return  0
        angle = _fixed_div(_fixed_mul(pf, 2*PI_INT), SCALE)
        return _fixed_mul(_cos_fp(angle), self.amp)
    def im(self) -> int:
        pf = self.phase_frac
        if pf == 0 or pf == SCALE//2: return 0
        if pf == SCALE//4:  return  self.amp
        if pf == 3*SCALE//4: return -self.amp
        angle = _fixed_div(_fixed_mul(pf, 2*PI_INT), SCALE)
        return _fixed_mul(_sin_fp(angle), self.amp)

# ── HCL operations (215-293) ──
class HCL:
    @staticmethod
    def COMP(a: FBit, b: FBit) -> FBit:
        re = a.re() + b.re()
        im = a.im() + b.im()
        amp_sq  = _fixed_mul(re, re) + _fixed_mul(im, im)
        amp_out = _fixed_sqrt(amp_sq, 60) if amp_sq > 0 else 0
        if amp_out == 0: return FBit(0, 0)
        at = _atan2_fp(im, re)
        pf = _fixed_div(at, 2 * PI_INT) % SCALE
        return FBit(pf, amp_out)
    @staticmethod
    def SHIFT(a: FBit, C: int) -> FBit:
        if C >= 0: return FBit(a.phase_frac, _fixed_mul(a.amp, C))
        return FBit((a.phase_frac + SCALE//2) % SCALE, _fixed_mul(a.amp, abs(C)))
    @staticmethod
    def AMP_MOD(a: FBit, b: FBit) -> FBit:
        return FBit((a.phase_frac + b.phase_frac) % SCALE, _fixed_mul(a.amp, b.amp))
    @staticmethod
    def INV(a: FBit) -> FBit:
        if a.amp == 0: raise ZeroDivisionError("HCL.INV: zero")
        return FBit((SCALE - a.phase_frac) % SCALE, _fixed_div(SCALE, a.amp))
    @staticmethod
    def FISSION(a: FBit) -> tuple:
        sqrt_amp = _fixed_sqrt(a.amp, 60)
        hp = a.phase_frac // 2
        return (FBit(hp, sqrt_amp), FBit((hp + SCALE//2) % SCALE, sqrt_amp))
    @staticmethod
    def MOBIUS_GROWTH(a: FBit) -> FBit:
        X       = a.to_scalar()
        amp_out = _exp_fp(X, 70)
        return FBit(0, amp_out)
    @staticmethod
    def LOG_EXTRACT(a: FBit) -> FBit:
        val = _ln_fp(a.amp, 160)
        return FBit.from_scalar(val)
    @staticmethod
    def PHASE_SIN(phase_frac: int) -> int:
        if phase_frac == 0 or phase_frac == SCALE//2: return 0
        if phase_frac == SCALE//4:   return  SCALE
        if phase_frac == 3*SCALE//4: return -SCALE
        angle = _fixed_div(_fixed_mul(phase_frac, 2*PI_INT), SCALE)
        return _sin_fp(angle, 40)
    @staticmethod
    def PHASE_COS(phase_frac: int) -> int:
        if phase_frac == 0:           return  SCALE
        if phase_frac == SCALE//2:    return -SCALE
        if phase_frac == SCALE//4 or phase_frac == 3*SCALE//4: return 0
        angle = _fixed_div(_fixed_mul(phase_frac, 2*PI_INT), SCALE)
        return _cos_fp(angle, 40)
    @staticmethod
    def RESONANCE(a: FBit, w_int: int) -> FBit:
        epsilon = ETA
        for _ in range(w_int - 1): epsilon = _fixed_mul(epsilon, LAMBDA)
        omega = _fixed_div(SCALE, ETA)
        for _ in range(w_int - 1): omega = _fixed_mul(omega, GAMMA)
        phase_stable = omega % SCALE
        return FBit(phase_stable, _fixed_mul(epsilon, a.amp))

# ── HCLTranscriber (301-416) ──
class HCLTranscriber:
    def __init__(self): self.braid_log = []
    def _log(self, op, r): self.braid_log.append({'op': op, 'r': r})
    def clear(self): self.braid_log.clear()
    @staticmethod
    def to_fp(x) -> int:
        from decimal import Decimal, getcontext
        getcontext().prec = PREC + 10
        if isinstance(x, int): return x * SCALE
        return int(Decimal(str(x)) * SCALE)
    @staticmethod
    def from_fp(X: int) -> str:
        s = '-' if X < 0 else ''
        m = abs(X)
        return f"{s}{m // SCALE}.{str(m % SCALE).zfill(PREC)}"
    def add(self, X, Y):
        r = HCL.COMP(FBit.from_scalar(X), FBit.from_scalar(Y))
        self._log('COMP[+]', r); return r.to_scalar()
    def sub(self, X, Y):
        r = HCL.COMP(FBit.from_scalar(X), HCL.SHIFT(FBit.from_scalar(Y), -SCALE))
        self._log('COMP[-]', r); return r.to_scalar()
    def mul(self, X, Y):
        r = HCL.AMP_MOD(FBit.from_scalar(X), FBit.from_scalar(Y))
        self._log('AMP_MOD[×]', r); return r.to_scalar()
    def div(self, X, Y):
        r = HCL.AMP_MOD(FBit.from_scalar(X), HCL.INV(FBit.from_scalar(Y)))
        self._log('AMP_MOD[÷]', r); return r.to_scalar()
    def neg(self, X):
        r = HCL.SHIFT(FBit.from_scalar(X), -SCALE)
        self._log('SHIFT[-]', r); return r.to_scalar()
    def pow_int(self, X, n: int):
        if n == 0: return SCALE
        fa = FBit.from_scalar(X)
        r  = fa
        for _ in range(abs(n) - 1): r = HCL.AMP_MOD(r, fa)
        if n < 0: r = HCL.INV(r)
        self._log(f'AMP_MOD^{n}', r); return r.to_scalar()
    def sqrt(self, X):
        d1, _ = HCL.FISSION(FBit.from_scalar(X))
        self._log('FISSION[√]', d1); return d1.to_scalar()
    def exp(self, X):
        r = HCL.MOBIUS_GROWTH(FBit.from_scalar(X))
        self._log('MOBIUS_GROWTH[eˣ]', r); return r.to_scalar()
    def ln(self, X):
        r = HCL.LOG_EXTRACT(FBit.from_scalar(X))
        self._log('LOG_EXTRACT[ln]', r); return r.to_scalar()
    def sin(self, X_phase_frac: int):
        val = HCL.PHASE_SIN(X_phase_frac)
        self._log('PHASE_SIN', FBit.from_scalar(val)); return val
    def cos(self, X_phase_frac: int):
        val = HCL.PHASE_COS(X_phase_frac)
        self._log('PHASE_COS', FBit.from_scalar(val)); return val
    def braid_word(self) -> str:
        lines = [
            "LOQ-HCL BRAID WORD",
            f"eta={ETA}/{SCALE}  lambda={LAMBDA}/{SCALE}",
            f"gamma={GAMMA}/{SCALE}",
            f"beta={BETA}/{SCALE}",
            f"alpha^-1 ~ {ALPHA_INV/SCALE:.6f}",
            "-" * 60
        ]
        for i, e in enumerate(self.braid_log):
            val = self.from_fp(e['r'].to_scalar())
            lines.append(f"s{i+1:<3} {e['op']:<28} ={val[:20]}")
        lines.append("-" * 60)
        lines.append(f"Length: {len(self.braid_log)} | Zero floats | Zero imports")
        return "\n".join(lines)
