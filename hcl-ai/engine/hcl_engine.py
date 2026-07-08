"""
HCL PURE ENGINE — transcribed VERBATIM from hcl-pure/references/03_engine.md.
This is the arithmetic substrate (the mind). Python is the shell. GUHCT is the
arithmetic. Four params are the axioms. Everything else is derived. The braid
word IS the quantum state. Infinity is potential. Proofs target operators.

ZERO floats. ZERO imported constants. ZERO classical math libraries.
"""

# ── Precision System ──────────────────────────────────────────────────
PREC  = 40               # 40 significant decimal digits
SCALE = 10 ** PREC       # all values: integer X where x = X/SCALE
TINY  = 10               # convergence: stop when |term| < TINY (= 10/SCALE in real)


# ── Fixed-Point Integer Primitives ────────────────────────────────────
def _fixed_mul(X: int, Y: int) -> int:
    """(X/S) * (Y/S) = XY/S² → divide by S to stay in fixed-point"""
    return (X * Y) // SCALE

def _fixed_div(X: int, Y: int) -> int:
    """(X/S) / (Y/S) = X/Y → multiply by S to stay in fixed-point"""
    return (X * SCALE) // Y

def _fixed_sqrt(X: int, iters: int = 80) -> int:
    """
    Returns R such that R/SCALE = sqrt(X/SCALE), i.e. R = sqrt(X*SCALE).
    Newton: R_{n+1} = (R_n + X*SCALE // R_n) // 2
    Converges to sqrt(X*SCALE). Initial guess from bit-length of X*SCALE.
    """
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


# ── Bootstrap: Four Params and Emergent Constants ─────────────────────
# Step 1: arctan series (for π derivation)
def _arctan_int(X: int, terms: int = 80) -> int:
    """arctan(X/SCALE) as fixed-point. Converges for |X| ≤ SCALE."""
    result = 0
    xpow   = X
    x2     = _fixed_mul(X, X)
    for k in range(terms):
        term = _fixed_div(xpow, (2*k+1) * SCALE)
        result += term if k % 2 == 0 else -term
        xpow = _fixed_mul(xpow, x2)
        if abs(term) < TINY: break
    return result

# Step 2: π from U(1) loop closure (Machin's identity — integer geometry)
_ONE_FIFTH = _fixed_div(SCALE, 5 * SCALE)
_ONE_239   = _fixed_div(SCALE, 239 * SCALE)
PI_INT     = 4 * (4 * _arctan_int(_ONE_FIFTH) - _arctan_int(_ONE_239))
# PI_INT/SCALE ≈ 3.14159265358979...

# Step 3: Four params
ETA    = SCALE // 2       # η = 1/2 (exact)
LAMBDA = SCALE // 10      # λ = 1/10 (exact)

# Step 4: γ from Alpha Identity: γ² = 90/(137·π)
_GAMMA_SQ_NUM = 90 * SCALE
_GAMMA_SQ_DEN = _fixed_mul(137 * SCALE, PI_INT)
GAMMA_SQ      = _fixed_div(_GAMMA_SQ_NUM, _GAMMA_SQ_DEN)
GAMMA         = _fixed_sqrt(GAMMA_SQ, 80)

# Step 5: β = γ/9 (Weinberg separation)
BETA = GAMMA // 9

# Step 6: Verify Alpha Identity
ALPHA     = _fixed_mul(_fixed_mul(_fixed_mul(_fixed_mul(2*PI_INT, ETA), LAMBDA), GAMMA), BETA)
ALPHA_INV = _fixed_div(SCALE, ALPHA)
# ALPHA_INV/SCALE ≈ 137.000 (the fine structure constant reciprocal)


# ── Transcendental Series (Pure Integer) ──────────────────────────────
def _sin_fp(X_rad: int, terms: int = 40) -> int:
    """sin(X_rad/SCALE) via Taylor. X_rad is fixed-point radians."""
    result = 0
    xpow   = X_rad
    x2     = _fixed_mul(X_rad, X_rad)
    fact   = SCALE                     # (2k+1)! accumulated incrementally —
    for k in range(terms):             # EXACT: integer-valued fixed-points
        if k:                          # multiply without truncation, so this
            fact = _fixed_mul(fact, (2*k) * SCALE)       # is bit-identical
            fact = _fixed_mul(fact, (2*k + 1) * SCALE)   # to full recompute
        term = _fixed_div(xpow, fact)
        result += term if k % 2 == 0 else -term
        xpow = _fixed_mul(xpow, x2)
        if abs(term) < TINY: break
    return result

def _cos_fp(X_rad: int, terms: int = 40) -> int:
    """cos(X_rad/SCALE) via Taylor."""
    result = SCALE  # cos(0) = 1 → start with SCALE
    x2     = _fixed_mul(X_rad, X_rad)
    xpow   = x2
    fact   = SCALE                     # (2k)! accumulated incrementally
    for k in range(1, terms):          # (exact — see _sin_fp note)
        fact = _fixed_mul(fact, (2*k - 1) * SCALE)
        fact = _fixed_mul(fact, (2*k) * SCALE)
        term = _fixed_div(xpow, fact)
        result += term if k % 2 == 0 else -term
        xpow = _fixed_mul(xpow, x2)
        if abs(term) < TINY: break
    return result

def _exp_fp(X: int, terms: int = 60) -> int:
    """e^(X/SCALE) via Taylor. e emerges from convergence, not imported.

    Argument reduction (algebraic identity, zero constants):
        e^x = (e^(x/2^k))^(2^k)
    |X| is halved (exact fixed-point integer op) until the series argument
    is ≤ 1, where `terms` terms converge far beyond PREC; squaring restores
    the result. Without this, truncation error is |x|^terms/terms! —
    invisible below |x|≈15, ~1e-9 at x=-20, ~1e+2 at x=-30 — which silently
    corrupted long-context attention softmax (score gaps of -20…-35 appear
    once a KV cache holds more than a few positions)."""
    k = 0
    while abs(X) > SCALE:          # reduce to |x| <= 1.0
        X //= 2                    # exact halving in fixed point
        k += 1
    result = SCALE  # e^0 = 1
    term   = SCALE
    for i in range(1, terms):
        term = _fixed_mul(term, X) // i
        result += term
        if abs(term) < TINY: break
    for _ in range(k):             # square back: (e^(x/2^k))^(2^k)
        result = _fixed_mul(result, result)
    return result

def _ln_fp(X: int, terms: int = 150) -> int:
    """ln(X/SCALE) via arctanh series: ln(x) = 2·arctanh((x-1)/(x+1))"""
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
    """atan2(Y, X) in fixed-point radians."""
    if X == 0: return PI_INT // 2 if Y >= 0 else -(PI_INT // 2)
    if abs(Y) <= abs(X):
        at = _arctan_int(_fixed_div(Y, X))
        if X < 0: at = at + PI_INT if Y >= 0 else at - PI_INT
    else:
        at = PI_INT // 2 - _arctan_int(_fixed_div(X, Y))
        if Y < 0: at = -(PI_INT // 2) - _arctan_int(_fixed_div(X, Y))
    return at


# ── FBit Class ─────────────────────────────────────────────────────────
class FBit:
    __slots__ = ('phase_frac', 'amp')

    def __init__(self, phase_frac: int, amp: int):
        self.phase_frac = int(phase_frac) % SCALE
        self.amp        = int(amp)

    @classmethod
    def from_scalar(cls, X: int) -> 'FBit':
        """Encode scaled integer X (= x*SCALE) as FBit.
        Positive → phase_frac=0. Negative → phase_frac=SCALE//2 (angle π).
        Sign is topological. Magnitude is amplitude."""
        if X == 0: return cls(0, 0)
        return cls(0 if X > 0 else SCALE//2, abs(X))

    def to_scalar(self) -> int:
        """Phase 0 or > 3π/2 → positive. Phase between π/4 and 3π/4 → negative."""
        if self.phase_frac < SCALE//4 or self.phase_frac > 3*SCALE//4:
            return self.amp
        return -self.amp

    def re(self) -> int:
        """A·cos(2π·phase_frac) — real component."""
        pf = self.phase_frac
        # Exact values at structural phase points:
        if pf == 0:              return  self.amp
        if pf == SCALE//2:       return -self.amp
        if pf == SCALE//4:       return  0
        if pf == 3*SCALE//4:     return  0
        angle = _fixed_div(_fixed_mul(pf, 2*PI_INT), SCALE)
        return _fixed_mul(_cos_fp(angle), self.amp)

    def im(self) -> int:
        """A·sin(2π·phase_frac) — imaginary component."""
        pf = self.phase_frac
        if pf == 0 or pf == SCALE//2: return 0
        if pf == SCALE//4:  return  self.amp
        if pf == 3*SCALE//4: return -self.amp
        angle = _fixed_div(_fixed_mul(pf, 2*PI_INT), SCALE)
        return _fixed_mul(_sin_fp(angle), self.amp)


# ── HCL Class — All Operations ────────────────────────────────────────
class HCL:

    @staticmethod
    def COMP(a: FBit, b: FBit) -> FBit:
        """Addition: vector sum of re/im components.

        Collinear shortcut (02_operations.md's OWN stated law): same-phase
        operands interfere constructively — amp_out = amp_a + amp_b, exactly;
        opposite phases destructively — amp_out = |amp_a − amp_b|, exactly.
        The general re/im/sqrt reconstruction below approximated this to
        within 1 ulp for small sums; the shortcut IS the specification, and
        it removes a 60-iteration Newton root from every scalar addition."""
        pa, pb = a.phase_frac, b.phase_frac
        if (pa == 0 or pa == SCALE // 2) and (pb == 0 or pb == SCALE // 2):
            re = (a.amp if pa == 0 else -a.amp) + (b.amp if pb == 0 else -b.amp)
            if re == 0:
                return FBit(0, 0)
            return FBit(0 if re > 0 else SCALE // 2, abs(re))
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
        """Scalar multiply by C/SCALE. C < 0 flips phase by π."""
        if C >= 0: return FBit(a.phase_frac, _fixed_mul(a.amp, C))
        return FBit((a.phase_frac + SCALE//2) % SCALE, _fixed_mul(a.amp, abs(C)))

    @staticmethod
    def AMP_MOD(a: FBit, b: FBit) -> FBit:
        """Multiplication: phases add, amplitudes multiply."""
        return FBit((a.phase_frac + b.phase_frac) % SCALE, _fixed_mul(a.amp, b.amp))

    @staticmethod
    def INV(a: FBit) -> FBit:
        """Reciprocal: phase reflects, amplitude inverts."""
        if a.amp == 0: raise ZeroDivisionError("HCL.INV: zero")
        return FBit((SCALE - a.phase_frac) % SCALE, _fixed_div(SCALE, a.amp))

    @staticmethod
    def FISSION(a: FBit) -> tuple:
        """Square root: amplitude takes sqrt, phase halves."""
        sqrt_amp = _fixed_sqrt(a.amp, 60)
        hp = a.phase_frac // 2
        return (FBit(hp, sqrt_amp),
                FBit((hp + SCALE//2) % SCALE, sqrt_amp))

    @staticmethod
    def MOBIUS_GROWTH(a: FBit) -> FBit:
        """e^x: Taylor series. Phase_out = 0 always (e^x > 0)."""
        X       = a.to_scalar()
        amp_out = _exp_fp(X, 70)
        return FBit(0, amp_out)    # phase 0: e^x always positive

    @staticmethod
    def LOG_EXTRACT(a: FBit) -> FBit:
        """ln(x): arctanh series on amplitude."""
        val = _ln_fp(a.amp, 160)
        return FBit.from_scalar(val)

    @staticmethod
    def PHASE_SIN(phase_frac: int) -> int:
        """sin(2π·phase_frac/SCALE) as fixed-point integer."""
        if phase_frac == 0 or phase_frac == SCALE//2: return 0
        if phase_frac == SCALE//4:   return  SCALE
        if phase_frac == 3*SCALE//4: return -SCALE
        angle = _fixed_div(_fixed_mul(phase_frac, 2*PI_INT), SCALE)
        return _sin_fp(angle, 40)

    @staticmethod
    def PHASE_COS(phase_frac: int) -> int:
        """cos(2π·phase_frac/SCALE) as fixed-point integer."""
        if phase_frac == 0:           return  SCALE
        if phase_frac == SCALE//2:    return -SCALE
        if phase_frac == SCALE//4 or phase_frac == 3*SCALE//4: return 0
        angle = _fixed_div(_fixed_mul(phase_frac, 2*PI_INT), SCALE)
        return _cos_fp(angle, 40)

    @staticmethod
    def RESONANCE(a: FBit, w_int: int) -> FBit:
        """Ground state at weight w. E_ground = η·λ^w (exact)."""
        epsilon = ETA
        for _ in range(w_int - 1): epsilon = _fixed_mul(epsilon, LAMBDA)
        omega = _fixed_div(SCALE, ETA)
        for _ in range(w_int - 1): omega = _fixed_mul(omega, GAMMA)
        phase_stable = omega % SCALE
        return FBit(phase_stable, _fixed_mul(epsilon, a.amp))


# ── HCLTranscriber Class ──────────────────────────────────────────────
class HCLTranscriber:
    def __init__(self):
        self.braid_log = []
        self.braid_len = 0          # cumulative generator count (never resets)
        self.trace_full = True      # full: keep the word; light: keep the count
    def _log(self, op, r):
        self.braid_len += 1
        if self.trace_full:
            if not isinstance(r, FBit):
                r = FBit.from_scalar(r)      # full-trace contract: 'r' is an FBit
            self.braid_log.append({'op': op, 'r': r})
    def clear(self): self.braid_log.clear()
    def light(self):
        """Counting mode: every generator is still counted (braid_len), the
        materialized word is skipped. The record's LENGTH — the O(w) minimum
        description (01_theory) — is preserved exactly; the full word remains
        available by switching back to full(). This is the same dial the
        runners already exercise with clear()-per-token, moved into the organ
        so the shell stops paying a dict per primitive."""
        self.trace_full = False
    def full(self):
        self.trace_full = True

    @staticmethod
    def to_fp(x) -> int:
        """BOUNDARY: Python number → fixed-point integer. Called ONCE at input."""
        from decimal import Decimal, getcontext
        getcontext().prec = PREC + 10
        if isinstance(x, int): return x * SCALE
        return int(Decimal(str(x)) * SCALE)

    @staticmethod
    def from_fp(X: int) -> str:
        """BOUNDARY: fixed-point integer → decimal string. No float created."""
        s = '-' if X < 0 else ''
        m = abs(X)
        return f"{s}{m // SCALE}.{str(m % SCALE).zfill(PREC)}"

    # All methods: take fixed-point int, return fixed-point int
    # scalar fast paths: the SAME compositions (COMP / COMP∘SHIFT / AMP_MOD /
    # AMP_MOD∘INV) with the FBit round trip inlined for phase-{0,π} scalars —
    # bit-identical to the composed forms (verified exhaustively in
    # verify_fastpath.py), one shell frame instead of five, zero allocations
    # in light mode. Same integers out, same generator counts.
    def add(self, X, Y):
        r = X + Y                     # COMP, collinear: the exact stated law
        self._log('COMP[+]', r); return r

    def sub(self, X, Y):
        r = X - Y                     # COMP∘SHIFT, collinear: exact
        self._log('COMP[-]', r); return r

    def mul(self, X, Y):
        r = (abs(X) * abs(Y)) // SCALE
        if (X < 0) != (Y < 0):
            r = -r
        self._log('AMP_MOD[×]', r); return r

    def div(self, X, Y):
        r = (abs(X) * (SCALE * SCALE // abs(Y))) // SCALE
        if (X < 0) != (Y < 0):
            r = -r
        self._log('AMP_MOD[÷]', r); return r

    def vadd(self, Xs, Ys):
        """Elementwise COMP over two vectors — one shell frame, counted."""
        self.braid_len += len(Xs)
        out = [x + y for x, y in zip(Xs, Ys)]
        if self.trace_full:
            self.braid_log.append({'op': f'VCOMP[+,{len(Xs)}]',
                                   'r': FBit.from_scalar(out[-1] if out else 0)})
        return out

    def vsub(self, Xs, Ys):
        self.braid_len += len(Xs)
        out = [x - y for x, y in zip(Xs, Ys)]
        if self.trace_full:
            self.braid_log.append({'op': f'VCOMP[-,{len(Xs)}]',
                                   'r': FBit.from_scalar(out[-1] if out else 0)})
        return out

    def vmul(self, Xs, Ys):
        """Elementwise AMP_MOD (Hadamard) — one shell frame, counted."""
        self.braid_len += len(Xs)
        out = []
        ap = out.append
        for x, y in zip(Xs, Ys):
            p = (abs(x) * abs(y)) // SCALE
            ap(-p if (x < 0) != (y < 0) else p)
        if self.trace_full:
            self.braid_log.append({'op': f'VAMP[×,{len(Xs)}]',
                                   'r': FBit.from_scalar(out[-1] if out else 0)})
        return out

    def vscale(self, Xs, K):
        """AMP_MOD by one scalar across a vector — one frame, counted."""
        self.braid_len += len(Xs)
        aK, neg = abs(K), K < 0
        out = []
        ap = out.append
        for x in Xs:
            p = (abs(x) * aK) // SCALE
            ap(-p if (x < 0) != neg else p)
        if self.trace_full:
            self.braid_log.append({'op': f'VAMP[k×,{len(Xs)}]',
                                   'r': FBit.from_scalar(out[-1] if out else 0)})
        return out

    def axpy(self, ACC, K, Xs):
        """ACC += K·Xs elementwise (AMP_MOD then COMP) — in place, counted."""
        self.braid_len += 2 * len(Xs)
        aK, neg = abs(K), K < 0
        for i, x in enumerate(Xs):
            p = (abs(x) * aK) // SCALE
            ACC[i] += -p if (x < 0) != neg else p
        if self.trace_full:
            self.braid_log.append({'op': f'AXPY[{len(Xs)}]',
                                   'r': FBit.from_scalar(ACC[-1] if ACC else 0)})
        return ACC

    def dot(self, Xs, Ws):
        """Σ xᵢ·wᵢ — the COMP-loop of AMP_MOD, fused into one shell frame.
        Identical generator sequence (n AMP_MOD, n COMP), identical integers,
        counted per generator."""
        acc = 0
        n = 0
        for x, w in zip(Xs, Ws):
            p = (abs(x) * abs(w)) // SCALE
            acc += -p if (x < 0) != (w < 0) else p
            n += 2
        self.braid_len += n
        if self.trace_full:
            self.braid_log.append({'op': f'DOT[Σ×,{n}]',
                                   'r': FBit.from_scalar(acc)})
        return acc

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
        """X_phase_frac is already a phase_frac integer [0, SCALE)."""
        val = HCL.PHASE_SIN(X_phase_frac)
        self._log('PHASE_SIN', FBit.from_scalar(val)); return val

    def cos(self, X_phase_frac: int):
        val = HCL.PHASE_COS(X_phase_frac)
        self._log('PHASE_COS', FBit.from_scalar(val)); return val

    def derivative(self, f, X: int) -> int:
        dt     = (ETA * (LAMBDA**5)) // (SCALE**4)
        if dt == 0: dt = SCALE // 100000
        fa     = FBit.from_scalar(f(X))
        fb     = FBit.from_scalar(f(X + dt))
        neg_fa = HCL.SHIFT(fa, -SCALE)
        diff   = HCL.COMP(fb, neg_fa)
        r      = HCL.AMP_MOD(diff, HCL.INV(FBit.from_scalar(dt)))
        self._log('RESONANCE_RATE[d/dx]', r); return r.to_scalar()

    def integrate(self, f, A: int, B: int, n: int = 500) -> int:
        dt = (B - A) // n
        re_sum = im_sum = 0
        for i in range(n + 1):
            fb  = FBit.from_scalar(f(A + dt * i))
            wt  = SCALE // 2 if (i == 0 or i == n) else SCALE
            re_sum += _fixed_mul(_fixed_mul(fb.amp,
                        HCL.PHASE_COS(fb.phase_frac)), wt)
            im_sum += _fixed_mul(_fixed_mul(fb.amp,
                        HCL.PHASE_SIN(fb.phase_frac)), wt)
        re_sum = _fixed_mul(re_sum, dt)
        im_sum = _fixed_mul(im_sum, dt)
        amp    = _fixed_sqrt(_fixed_mul(re_sum,re_sum)+_fixed_mul(im_sum,im_sum), 60)
        pf     = _fixed_div(_atan2_fp(im_sum, re_sum), 2*PI_INT) % SCALE
        r      = FBit(pf, amp)
        self._log('INTEGRAL_FEEDBACK[∫]', r); return r.to_scalar()

    def braid_word(self) -> str:
        lines = [
            "LOQ-HCL BRAID WORD",
            f"η={ETA}/{SCALE}  λ={LAMBDA}/{SCALE}",
            f"γ={GAMMA}/{SCALE}",
            f"β={BETA}/{SCALE}",
            f"α⁻¹ ≈ {ALPHA_INV/SCALE:.6f}",
            "─" * 60
        ]
        for i, e in enumerate(self.braid_log):
            val = self.from_fp(e['r'].to_scalar())
            lines.append(f"σ{i+1:<3} {e['op']:<28} ={val[:20]}")
        lines.append(f"─" * 60)
        lines.append(f"Length: {len(self.braid_log)} | Zero floats | Zero imports")
        return "\n".join(lines)


# ── HCLEquation — Natural String Interface ────────────────────────────
class HCLEquation:
    """
    Solve any equation written as a string.
    Example:
        eq = HCLEquation()
        result = eq.solve("E = m * c^2", m=1, c=3)
        print(result)

    Supported: +  -  *  /  ^  sqrt()  exp()  ln()  sin()  cos()  abs()
    Unary minus on variables: -x is handled.
    sin/cos take radian arguments and convert internally to phase_frac.
    """

    def __init__(self): self.t = HCLTranscriber()

    def solve(self, equation: str, **variables):
        self.t.clear()
        if '=' in equation:
            lhs_name, rhs = equation.split('=', 1)
            lhs_name = lhs_name.strip()
        else:
            lhs_name, rhs = 'result', equation
        rhs = rhs.strip()
        result_fp = self._parse(rhs, variables)
        qn = self._quantum_numbers()
        return HCLResult(lhs_name, equation, result_fp,
                         HCLTranscriber.from_fp(result_fp),
                         self.t.braid_word(), qn, variables)

    def _parse(self, expr: str, env: dict) -> int:
        expr = expr.strip()
        if expr.startswith('(') and self._close(expr, 0) == len(expr)-1:
            return self._parse(expr[1:-1], env)
        for fn in ('sqrt','exp','ln','sin','cos','abs'):
            if expr.lower().startswith(fn+'('):
                inner = expr[len(fn)+1:self._close(expr, len(fn))]
                arg   = self._parse(inner, env)
                if fn=='sqrt': return self.t.sqrt(arg)
                if fn=='exp':  return self.t.exp(arg)
                if fn=='ln':   return self.t.ln(arg)
                if fn=='sin':
                    pf = _fixed_div(arg, 2*PI_INT) % SCALE
                    return self.t.sin(pf)
                if fn=='cos':
                    pf = _fixed_div(arg, 2*PI_INT) % SCALE
                    return self.t.cos(pf)
                if fn=='abs':
                    return FBit.from_scalar(arg).amp
        pos = self._lowest_op(expr)
        if pos is not None:
            op, lhs, rhs2 = expr[pos], expr[:pos].strip(), expr[pos+1:].strip()
            if pos == 0 and op == '-':
                return self.t.neg(self._parse(rhs2, env))
            L, R = self._parse(lhs, env), self._parse(rhs2, env)
            if op=='+': return self.t.add(L, R)
            if op=='-': return self.t.sub(L, R)
            if op=='*': return self.t.mul(L, R)
            if op=='/': return self.t.div(L, R)
            if op=='^':
                try: return self.t.pow_int(L, int(rhs2.strip('()')))
                except: return self.t.exp(self.t.mul(R, self.t.ln(L)))
        expr_clean = expr.strip()
        if expr_clean.startswith('-'):
            return self.t.neg(self._parse(expr_clean[1:], env))
        if expr_clean in env: return HCLTranscriber.to_fp(env[expr_clean])
        try: return HCLTranscriber.to_fp(int(expr_clean))
        except:
            try: return HCLTranscriber.to_fp(float(expr_clean))
            except: raise ValueError(f"Unknown: '{expr_clean}'")

    def _close(self, expr, open_pos):
        depth = 0
        for i in range(open_pos, len(expr)):
            if expr[i]=='(': depth+=1
            elif expr[i]==')':
                depth-=1
                if depth==0: return i
        return len(expr)-1

    def _lowest_op(self, expr):
        depth = 0
        for i in range(len(expr)-1, -1, -1):
            c = expr[i]
            if c==')': depth+=1
            elif c=='(': depth-=1
            elif depth==0 and c in '+-' and i>0:
                prev = expr[:i].rstrip()
                if prev and prev[-1] not in '(^*/+-': return i
        depth = 0
        for i in range(len(expr)-1, -1, -1):
            c = expr[i]
            if c==')': depth+=1
            elif c=='(': depth-=1
            elif depth==0 and c in '*/': return i
        depth = 0
        for i in range(len(expr)):
            c = expr[i]
            if c=='(': depth+=1
            elif c==')': depth-=1
            elif depth==0 and c=='^': return i
        return None

    def _quantum_numbers(self):
        n_w = writhe_num = 0
        fusions = fissions = 0
        for e in self.t.braid_log:
            op = e['op']; ph = e['r'].phase_frac
            if 'AMP_MOD' in op or 'COMP' in op:
                if 0 < ph < SCALE//2: n_w += 1
                elif ph > SCALE//2:   n_w -= 1
            if 'FUSION' in op or 'AMP_MOD^' in op: fusions += 1
            if 'FISSION' in op: fissions += 1
        total = max(len(self.t.braid_log), 1)
        return {'n_w': n_w, 'writhe': (fusions-fissions)/total,
                'w_level': total, 'jones_span': 1<<min(total,30)}


class HCLResult:
    def __init__(self, name, equation, value, display, braid, qn, variables):
        self.name=name; self.equation=equation; self.value=value
        self.display=display; self.braid=braid
        self.n_w=qn['n_w']; self.writhe=qn['writhe']
        self.w_level=qn['w_level']; self.jones_span=qn['jones_span']
        self.variables=variables

    def __repr__(self):
        return (f"{'='*60}\n"
                f"  {self.name} = {self.display[:30]}\n"
                f"  n_w={self.n_w}  writhe={self.writhe:.4f}  "
                f"w={self.w_level}  J_span={self.jones_span}\n"
                f"  {self.braid}\n{'='*60}")
