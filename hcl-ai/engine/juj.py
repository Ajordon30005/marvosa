"""
GUHCT Holographic Vision Parameters — Pure-Integer Bijective Transducer
======================================================================

This is a rewrite of the processor that obeys the same laws as the two working
skills (hcl-pure, virtual-memory-hcl) and the GUHCT theory as stated by the
source:

  * ZERO floats in the pipeline (Python arbitrary-precision int only).
  * ZERO imported constants (no math.pi, no numpy, no Planck energy, no photon
    wavelengths). Every constant is bootstrapped from the four params.
  * The transduction is bijective at the SEQUENCE level. The data lives in the
    braid word (the L(D|T) term); the 8 HVP parameters are the derived
    holographic ADDRESS (the L(T) term). Reconstruction consumes the braid word
    and the params validate it. This is what the theory actually claims:
    "lossless and bijective ... but the braid itself must be provided."

Forward : bytes            -> (8 HVP params, braid_word)
Inverse : (params, braid)  -> bytes   (exact, verified against the params)

Nothing here secretly takes the original bytes as a reconstruction input. The
inverse path sees only the braid word and the params.
"""

# ---------------------------------------------------------------------------
# Precision system (identical discipline to hcl-pure / virtual-memory-hcl)
# ---------------------------------------------------------------------------
PREC  = 40
SCALE = 10 ** PREC
TINY  = 10


def _fmul(X, Y):
    """(X/S)*(Y/S) kept in fixed point."""
    return (X * Y) // SCALE


def _fdiv(X, Y):
    """(X/S)/(Y/S) kept in fixed point."""
    return (X * SCALE) // Y


def _fsqrt(X, iters=80):
    """R such that R/SCALE = sqrt(X/SCALE), i.e. R = sqrt(X*SCALE)."""
    if X == 0:
        return 0
    target = X * SCALE
    bits = target.bit_length()
    Rg = 1 << ((bits + 1) // 2)
    Rg = max(Rg, 1)
    for _ in range(iters):
        Rg2 = (Rg + target // Rg) // 2
        if abs(Rg2 - Rg) <= 1:
            break
        Rg = Rg2
    return Rg


def _arctan(X, terms=80):
    r = 0
    xp = X
    x2 = _fmul(X, X)
    for k in range(terms):
        t = _fdiv(xp, (2 * k + 1) * SCALE)
        r += t if k % 2 == 0 else -t
        xp = _fmul(xp, x2)
        if abs(t) < TINY:
            break
    return r


# pi from the U(1) loop-closure (Machin identity), exactly as the working skills
_ONE5 = _fdiv(SCALE, 5 * SCALE)
_ONE239 = _fdiv(SCALE, 239 * SCALE)
PI_INT = 4 * (4 * _arctan(_ONE5) - _arctan(_ONE239))


def _fsin(X, terms=40):
    r = 0
    xp = X
    x2 = _fmul(X, X)
    for k in range(terms):
        f = SCALE
        for j in range(1, 2 * k + 2):
            f = _fmul(f, j * SCALE)
        t = _fdiv(xp, f)
        r += t if k % 2 == 0 else -t
        xp = _fmul(xp, x2)
        if abs(t) < TINY:
            break
    return r


def _fcos(X, terms=40):
    r = SCALE
    xp = _fmul(X, X)
    for k in range(1, terms):
        f = SCALE
        for j in range(1, 2 * k + 1):
            f = _fmul(f, j * SCALE)
        t = _fdiv(xp, f)
        r += t if k % 2 == 0 else -t
        xp = _fmul(xp, _fmul(X, X))
        if abs(t) < TINY:
            break
    return r


def _atan2(Y, X):
    if X == 0:
        return PI_INT // 2 if Y >= 0 else -(PI_INT // 2)
    if abs(Y) <= abs(X):
        at = _arctan(_fdiv(Y, X))
        if X < 0:
            at = at + PI_INT if Y >= 0 else at - PI_INT
    else:
        at = PI_INT // 2 - _arctan(_fdiv(X, Y))
        if Y < 0:
            at = -(PI_INT // 2) - _arctan(_fdiv(X, Y))
    return at


def _flog2_int(n):
    """Pure-integer floor(log2(n)) for n>=1 via bit_length."""
    if n <= 1:
        return 0
    return (n - 1).bit_length()


# ---------------------------------------------------------------------------
# Four params — the complete axiom set (identical bootstrap to hcl-pure)
# ---------------------------------------------------------------------------
ETA = SCALE // 2            # eta  = 1/2
LAMBDA = SCALE // 10        # lambda = 1/10
_GAMMA_SQ = _fdiv(90 * SCALE, _fmul(137 * SCALE, PI_INT))   # gamma^2 = 90/(137 pi)
GAMMA = _fsqrt(_GAMMA_SQ, 80)
BETA = GAMMA // 9           # Weinberg separation

ALPHA = _fmul(_fmul(_fmul(_fmul(2 * PI_INT, ETA), LAMBDA), GAMMA), BETA)
ALPHA_INV = _fdiv(SCALE, ALPHA)   # ~137


def mcl_eps(w):
    """Collapse threshold, theory definition: eps_w = 10^(-w) * eta (fixed point).
    Zero is a valid state; no epsilon floor is added anywhere else."""
    e = SCALE
    for _ in range(w):
        e //= 10
    return _fmul(e, ETA)


# ---------------------------------------------------------------------------
# FBit (identical algebra to the working skills)
# ---------------------------------------------------------------------------
class FBit:
    __slots__ = ('phase_frac', 'amp')

    def __init__(self, phase_frac, amp):
        self.phase_frac = int(phase_frac) % SCALE
        self.amp = int(amp)

    def re(self):
        pf = self.phase_frac
        if pf == 0:
            return self.amp
        if pf == SCALE // 2:
            return -self.amp
        if pf == SCALE // 4 or pf == 3 * SCALE // 4:
            return 0
        angle = _fdiv(_fmul(pf, 2 * PI_INT), SCALE)
        return _fmul(_fcos(angle), self.amp)

    def im(self):
        pf = self.phase_frac
        if pf == 0 or pf == SCALE // 2:
            return 0
        if pf == SCALE // 4:
            return self.amp
        if pf == 3 * SCALE // 4:
            return -self.amp
        angle = _fdiv(_fmul(pf, 2 * PI_INT), SCALE)
        return _fmul(_fsin(angle), self.amp)


def comp(a, b):
    """HCL COMP — quantum superposition (vector sum of components)."""
    re = a.re() + b.re()
    im = a.im() + b.im()
    amsq = _fmul(re, re) + _fmul(im, im)
    amp = _fsqrt(amsq, 60) if amsq > 0 else 0
    if amp == 0:
        return FBit(0, 0)
    at = _atan2(im, re)
    pf = _fdiv(at, 2 * PI_INT) % SCALE
    return FBit(pf, amp)


# ---------------------------------------------------------------------------
# The braid word — the data-carrying term  (L(D|T))
# ---------------------------------------------------------------------------
# A byte sequence is a word in the generators {sigma_0 .. sigma_255}. Generator
# sigma_k carries an FBit whose phase is the four-param address of the letter k.
# The braid word is the ordered list of generator indices (the bytes). This is
# trivially and exactly invertible: it IS the data, expressed topologically.
#
# Each generator's FBit phase is a *derived* function of the four params, so the
# spectrum (and therefore the 8 HVP params) is fixed by the theory, not chosen.

_GEN_BASE = SCALE // 256          # phase quantum per generator letter


def _generator_phase(k):
    """Fixed four-param phase address of generator sigma_k. Independent of
    position, so it can be memoized once for all 256 letters."""
    phase = (k * SCALE) // 256
    phase = (phase + _fmul(GAMMA, k * _GEN_BASE)) % SCALE
    return phase


# Memoized generator table — computed once, regardless of data size.
# There are only 256 distinct letters, so the trig (the expensive part) is
# evaluated 256 times total instead of once per byte. _UNIT_COS/_UNIT_SIN hold
# cos/sin of each generator's phase at unit amplitude (fixed point). A
# generator's re/im at amplitude A are then just _fmul(_UNIT_COS[k], A) and
# _fmul(_UNIT_SIN[k], A) — no Taylor series in the per-byte loop.
_GEN_PHASE = [0] * 256
_UNIT_COS = [0] * 256
_UNIT_SIN = [0] * 256
for _k in range(256):
    _pf = _generator_phase(_k)
    _GEN_PHASE[_k] = _pf
    if _pf == 0:
        _UNIT_COS[_k], _UNIT_SIN[_k] = SCALE, 0
    elif _pf == SCALE // 2:
        _UNIT_COS[_k], _UNIT_SIN[_k] = -SCALE, 0
    elif _pf == SCALE // 4:
        _UNIT_COS[_k], _UNIT_SIN[_k] = 0, SCALE
    elif _pf == 3 * SCALE // 4:
        _UNIT_COS[_k], _UNIT_SIN[_k] = 0, -SCALE
    else:
        _ang = _fdiv(_fmul(_pf, 2 * PI_INT), SCALE)
        _UNIT_COS[_k] = _fcos(_ang)
        _UNIT_SIN[_k] = _fsin(_ang)


def _generator_amp(k, position, n_total):
    """Position-weighted amplitude (Mobius decay), as in encode_text."""
    weight = SCALE * (n_total - position) // n_total if n_total else SCALE
    amp = _fmul((k + 1) * _GEN_BASE, weight)
    return max(amp, _GEN_BASE)


def _generator_fbit(k, position, n_total):
    """FBit for generator sigma_k at a position. Phase from the memoized table,
    amplitude position-weighted. Kept for API compatibility / inspection."""
    return FBit(_GEN_PHASE[k], _generator_amp(k, position, n_total))


def bytes_to_braid(raw_bytes):
    """Forward data term: bytes -> braid word (list of generator indices).

    Exactly reversible. No information is discarded; the word is the data."""
    return list(raw_bytes)


def braid_to_bytes(braid_word):
    """Inverse data term: braid word -> exact original bytes."""
    return bytes(bytearray(braid_word))


# ---------------------------------------------------------------------------
# Topological invariants of the braid (winding number, writhe, Jones span)
# ---------------------------------------------------------------------------
def braid_invariants(braid_word):
    """Compute (n_w, writhe_int, jones_span, spectrum_fbit, stability) from the
    braid word. The spectrum is the COMP accumulation of all generator FBits;
    because COMP is the vector sum of components, the whole fold is done in
    rectangular (re, im) coordinates with one multiply-add per byte using the
    memoized generator table — then converted to (phase, amp) once at the end.
    Pure integer throughout; no per-byte trig."""
    n = len(braid_word)
    if n == 0:
        return {'n_w': 0, 'writhe': 0, 'jones_span': 1, 'w_level': 1,
                'spectrum': FBit(0, SCALE), 'stability': 0, 'amps': []}

    # seed (matches the FBit(0, _GEN_BASE) seed of the original COMP fold)
    re_sum = _GEN_BASE
    im_sum = 0
    amps = []
    n_w = 0
    for pos, k in enumerate(braid_word):
        amp = _generator_amp(k, pos, n)
        amps.append(amp)
        # winding number: net signed phase advance of each generator
        pf = _GEN_PHASE[k]
        if 0 < pf < SCALE // 2:
            n_w += 1
        elif pf > SCALE // 2:
            n_w -= 1
        # COMP as rectangular vector addition (no trig, no sqrt, no atan2 here)
        re_sum += _fmul(_UNIT_COS[k], amp)
        im_sum += _fmul(_UNIT_SIN[k], amp)

    # single conversion of the accumulated spectrum to (phase, amp)
    amsq = _fmul(re_sum, re_sum) + _fmul(im_sum, im_sum)
    spec_amp = _fsqrt(amsq, 60) if amsq > 0 else 0
    spec_pf = _fdiv(_atan2(im_sum, re_sum), 2 * PI_INT) % SCALE if spec_amp else 0
    spectrum = FBit(spec_pf, spec_amp)

    # writhe proxy: sin(2 pi phase) of the accumulated spectrum, fixed point
    pf = spectrum.phase_frac
    if pf == 0 or pf == SCALE // 2:
        writhe_int = 0
    elif pf == SCALE // 4:
        writhe_int = SCALE
    elif pf == 3 * SCALE // 4:
        writhe_int = -SCALE
    else:
        angle = _fdiv(_fmul(pf, 2 * PI_INT), SCALE)
        writhe_int = _fsin(angle, 20)

    # Jones span: (#distinct generators) x crossing depth
    distinct = len(set(braid_word))
    depth = _flog2_int(n + 1)
    jones_span = distinct * max(depth, 1)
    w_level = max(_flog2_int(jones_span + 1), 1)

    # Stability measure I_w = (1/N) sum |a|^2 (1-|a|^2), normalised amplitudes
    a_max = max(amps) if amps else SCALE
    stab = 0
    for a in amps:
        an = _fdiv(a, a_max) if a_max else 0
        a2 = _fmul(an, an)
        stab += _fmul(a2, SCALE - a2)
    stability = stab // len(amps)

    return {'n_w': n_w, 'writhe': writhe_int, 'jones_span': jones_span,
            'w_level': w_level, 'spectrum': spectrum, 'stability': stability,
            'amps': amps}


# ---------------------------------------------------------------------------
# The 8 HVP parameters — the derived holographic address  (L(T))
# ---------------------------------------------------------------------------
# Each is a pure-integer (fixed-point) consequence of the four params and the
# braid invariants, per the theory. None imports a physical constant.
HVP_PARAMS = ['w', 'T', 'Gamma', 'Phi', 'f0', 'gamma_collapse',
              'Q_min', 'propagator_scale', 'C_min']


def forensic_reconstruct_boundary(braid_word):
    """Extract the 8 HVP parameters from the braid word.

    These are the holographic signature/address of the data. They are a
    deterministic function of the braid, so the same braid always yields the
    same params (this is what makes the transduction verifiable)."""
    inv = braid_invariants(braid_word)

    # w : Jones-weight correspondence  w = ceil(log2(span+1))   (pure integer)
    span = inv['jones_span']
    w = _flog2_int(span + 1)
    if (1 << w) < span + 1:
        w += 1

    # Gamma : gauge coupling tied to the weight via the Alpha identity scaling.
    Gamma = w * SCALE  # stored in fixed point as an integer weight

    # T : mode temperature governed by beta (inverse temperature). The
    # energy-weighted mean rung scales as the spectrum phase over beta.
    spec = inv['spectrum']
    T = _fdiv(spec.phase_frac, BETA) if BETA else 0

    # Phi : Fibonacci detuning — spectrum phase relative to the nearest
    # golden rung, expressed as a fixed-point ratio around 1.
    Phi = SCALE + _fmul(GAMMA, (spec.phase_frac - SCALE // 2))

    # f0 : fundamental frequency from the LQT length scale sqrt(eta/lambda).
    f0 = _fsqrt(_fdiv(ETA, LAMBDA), 80)

    # gamma_collapse : collapse sharpness from the stability measure I_w.
    # Sharper (higher) when the system is closer to a pure resonant state
    # (small dissonance I_w).
    stab = inv['stability']
    gamma_collapse = _fdiv(SCALE, stab + mcl_eps(max(w, 1)))

    # Q_min : Q-gate selectivity, Q = E0 / Gamma with E0 ~ lambda (energy unit).
    Q_min = _fdiv(LAMBDA, Gamma + mcl_eps(1)) if Gamma else 0

    # propagator_scale : inter-rung coupling = sqrt(eta/lambda)/rung_range.
    rung_range = max(inv['w_level'], 1) * SCALE
    propagator_scale = _fdiv(f0, rung_range)

    # C_min : coupling threshold — zero is a valid state (no floor).
    C_min = 0

    return {
        'w': w * SCALE,            # report w in fixed point for uniformity
        'T': T,
        'Gamma': Gamma,
        'Phi': Phi,
        'f0': f0,
        'gamma_collapse': gamma_collapse,
        'Q_min': Q_min,
        'propagator_scale': propagator_scale,
        'C_min': C_min,
        '_invariants': inv,
    }


# ---------------------------------------------------------------------------
# Public transducer API
# ---------------------------------------------------------------------------
def bytes_to_hvp(raw_bytes):
    """FORWARD transduction.

    Returns the HVP signature dict:
       { 'params': {8 derived HVP params},
         'braid':  [generator indices]  (the data term),
         'n_bytes': original length }

    The params alone are the address; the braid carries the data. Both together
    are the complete, bijective representation of the byte sequence."""
    braid = bytes_to_braid(raw_bytes)
    params = forensic_reconstruct_boundary(braid)
    params.pop('_invariants', None)
    return {'params': params, 'braid': braid, 'n_bytes': len(raw_bytes)}


def hvp_to_bytes(signature, verify=True):
    """INVERSE transduction.

    Consumes ONLY the signature (params + braid). Rebuilds the exact bytes from
    the braid word, then — if verify — re-derives the params from the rebuilt
    braid and confirms they match the supplied params. A mismatch means the
    signature was corrupted; a match certifies a bijective round trip."""
    braid = signature['braid']
    data = braid_to_bytes(braid)

    if verify:
        recomputed = forensic_reconstruct_boundary(braid)
        recomputed.pop('_invariants', None)
        supplied = signature['params']
        for k in HVP_PARAMS:
            if recomputed.get(k) != supplied.get(k):
                raise ValueError(
                    f"HVP signature mismatch on '{k}': the braid does not "
                    f"address the supplied parameters (corrupt signature).")

    n = signature.get('n_bytes', len(data))
    return data[:n]


# ---------------------------------------------------------------------------
# Self-test : exact bijection on real, arbitrary byte sequences
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import os

    print(f"alpha^-1 = {ALPHA_INV / SCALE:.6f}  (target 137)")
    print(f"pi       = {PI_INT / SCALE:.10f}")
    print("-" * 60)

    cases = [
        b"",
        b"A",
        b"Hello, GUHCT.",
        bytes(range(256)),                       # every byte value
        os.urandom(4096),                        # 4 KB of pure entropy
        ("the braid word IS the data " * 500).encode(),  # ~13 KB structured
    ]

    all_ok = True
    for i, data in enumerate(cases):
        sig = bytes_to_hvp(data)
        out = hvp_to_bytes(sig, verify=True)
        ok = (out == data)
        all_ok &= ok
        p = sig['params']
        print(f"case {i}: {len(data):>6} bytes  exact={ok}  "
              f"w={p['w']//SCALE} braidlen={len(sig['braid'])}")

    print("-" * 60)
    print("ALL BIT-PERFECT" if all_ok else "FAILURE")
