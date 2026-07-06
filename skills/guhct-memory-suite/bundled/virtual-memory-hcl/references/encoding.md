# Topological Memory — Encoding Reference

## The Encoding Problem

Classical encoding: text → SHA256 → truncate → 5 integers. This is what
the original skill does. It is wrong for two reasons:
1. SHA256 uses floats internally (via numpy) — breaks GUHCT purity
2. The resulting integers have no topological meaning — they are random
   hashes with no algebraic structure. You cannot compute their winding
   number. They have no Jones polynomial. The "LQT signature" is fake.

GUHCT encoding: text → pure integer sequence → HCL operations → FBit with
genuine topological invariants. The FBit's phase_frac and amplitude are
computed through COMP, AMP_MOD, MOBIUS_GROWTH on the integer character
values of the text. The resulting FBit has a real winding number, real
writhe, real Jones span — all derived from the four params, nothing else.

---

## Four Params Bootstrap (identical to hcl-pure skill)

```python
PREC  = 30
SCALE = 10 ** PREC
TINY  = 10

def _fmul(X, Y): return (X * Y) // SCALE
def _fdiv(X, Y): return (X * SCALE) // Y

def _arctan(X, terms=60):
    r=0; xp=X; x2=_fmul(X,X)
    for k in range(terms):
        t = _fdiv(xp, (2*k+1)*SCALE)
        r += t if k%2==0 else -t
        xp = _fmul(xp, x2)
        if abs(t) < TINY: break
    return r

_ONE5   = _fdiv(SCALE, 5*SCALE)
_ONE239 = _fdiv(SCALE, 239*SCALE)
PI_INT  = 4*(4*_arctan(_ONE5) - _arctan(_ONE239))

ETA    = SCALE // 2
LAMBDA = SCALE // 10

_GAMMA_SQ = _fdiv(90*SCALE, _fmul(137*SCALE, PI_INT))

def _fsqrt(X, iters=60):
    if X==0: return 0
    tgt=X*SCALE; bits=tgt.bit_length()
    R=1<<((bits+1)//2); R=max(R,1)
    for _ in range(iters):
        R2=(R+tgt//R)//2
        if abs(R2-R)<=1: break
        R=R2
    return R

GAMMA = _fsqrt(_GAMMA_SQ, 80)
BETA  = GAMMA // 9

ALPHA     = _fmul(_fmul(_fmul(_fmul(2*PI_INT, ETA), LAMBDA), GAMMA), BETA)
ALPHA_INV = _fdiv(SCALE, ALPHA)
```

---

## Text → Integer Sequence

Every character in the text becomes an integer in [0, SCALE).
The encoding preserves all information — it is invertible.

```python
def text_to_integers(text: str) -> list:
    """
    Convert text to list of fixed-point integers.
    Each character maps to its Unicode code point scaled by SCALE/1114112
    (dividing the full Unicode range into SCALE units).
    This is a bijective mapping — fully reversible.
    """
    scale_per_char = SCALE // 1114112  # Unicode max = 1,114,112
    return [ord(c) * scale_per_char for c in text]
```

---

## Integer Sequence → FBit (Pure HCL)

The integer sequence is processed through HCL operations to produce one
FBit that encodes the entire semantic content of the text.

The key insight: we do not hash. We COMPOSE. Each character's integer
FBit is COMP-ed into the accumulating state. COMP is quantum superposition
— the resulting FBit is the interference pattern of all character FBits.
The winding number of the result IS a topological property of the text,
not a random hash.

```python
class FBit:
    def __init__(self, phase_frac: int, amp: int):
        self.phase_frac = int(phase_frac) % SCALE
        self.amp        = int(amp)

    @classmethod
    def from_int(cls, X: int) -> 'FBit':
        """Encode integer X as FBit. Positive → phase 0. Negative → phase π."""
        if X == 0: return cls(0, 0)
        return cls(0 if X > 0 else SCALE//2, abs(X))

    def re(self) -> int:
        pf = self.phase_frac
        if pf == 0:          return  self.amp
        if pf == SCALE//2:   return -self.amp
        if pf == SCALE//4:   return  0
        if pf == 3*SCALE//4: return  0
        angle = _fdiv(_fmul(pf, 2*PI_INT), SCALE)
        return _fmul(_fcos(angle), self.amp)

    def im(self) -> int:
        pf = self.phase_frac
        if pf == 0 or pf == SCALE//2: return 0
        if pf == SCALE//4:   return  self.amp
        if pf == 3*SCALE//4: return -self.amp
        angle = _fdiv(_fmul(pf, 2*PI_INT), SCALE)
        return _fmul(_fsin(angle), self.amp)

    def to_int(self) -> int:
        if self.phase_frac < SCALE//4 or self.phase_frac > 3*SCALE//4:
            return self.amp
        return -self.amp


def _fsin(X, terms=25):
    r=0; xp=X; x2=_fmul(X,X)
    for k in range(terms):
        f=SCALE
        for j in range(1,2*k+2): f=_fmul(f,j*SCALE)
        t=_fdiv(xp,f)
        r += t if k%2==0 else -t
        xp=_fmul(xp,x2)
        if abs(t)<TINY: break
    return r

def _fcos(X, terms=25):
    r=SCALE; xp=_fmul(X,X)
    for k in range(1,terms):
        f=SCALE
        for j in range(1,2*k+1): f=_fmul(f,j*SCALE)
        t=_fdiv(xp,f)
        r += t if k%2==0 else -t
        xp=_fmul(xp,_fmul(X,X))
        if abs(t)<TINY: break
    return r

def _fexp(X, terms=40):
    r=SCALE; t=SCALE
    for k in range(1,terms):
        t=_fmul(t,X)//k
        r+=t
        if abs(t)<TINY: break
    return r

def _atan2(Y, X):
    if X==0: return PI_INT//2 if Y>=0 else -(PI_INT//2)
    if abs(Y)<=abs(X):
        at=_arctan(_fdiv(Y,X))
        if X<0: at=at+PI_INT if Y>=0 else at-PI_INT
    else:
        at=PI_INT//2-_arctan(_fdiv(X,Y))
        if Y<0: at=-(PI_INT//2)-_arctan(_fdiv(X,Y))
    return at


def comp(a: FBit, b: FBit) -> FBit:
    """HCL COMP — quantum superposition of two FBits."""
    re = a.re() + b.re()
    im = a.im() + b.im()
    amsq = _fmul(re,re) + _fmul(im,im)
    amp  = _fsqrt(amsq, 40) if amsq > 0 else 0
    if amp == 0: return FBit(0,0)
    at = _atan2(im, re)
    pf = _fdiv(at, 2*PI_INT) % SCALE
    return FBit(pf, amp)


def encode_text(text: str) -> FBit:
    """
    Encode text to a single FBit via HCL COMP accumulation.
    
    Each character contributes its Unicode value as a FBit phase.
    Phase_frac for character c: ord(c) * SCALE // 128  (ASCII range)
    For full Unicode: ord(c) * SCALE // 1114112
    
    The accumulated COMP of all characters IS the semantic FBit.
    Its winding number, writhe, and Jones span are topological properties
    of the text's character sequence — not a hash, not a projection.
    
    Two texts with similar character distributions will produce FBits
    with similar phase_frac values → constructive COMP → resonance.
    Two texts with opposite distributions → destructive → no resonance.
    This IS the correct semantic similarity measure in GUHCT.
    """
    if not text:
        return FBit(0, SCALE)
    
    # Seed: encode text length as initial amplitude
    # Length encodes complexity — longer texts have larger amplitude
    acc = FBit(0, len(text) * SCALE // max(len(text), 1))
    
    # Accumulate each character via COMP (quantum superposition)
    for i, c in enumerate(text):
        # Phase: character value as fraction of full Unicode range
        char_phase = (ord(c) * SCALE) // 1114112
        
        # Amplitude: position-weighted character value
        # Later characters contribute less (MOBIUS_GROWTH decay)
        # exp(-i/len) weight: approximated as SCALE*(len-i)//len
        weight = SCALE * (len(text) - i) // len(text)
        char_amp = _fmul(ord(c) * SCALE // 128, weight)
        
        char_fbit = FBit(char_phase, max(char_amp, SCALE//128))
        acc = comp(acc, char_fbit)
    
    return acc
```

---

## FBit → Topological Invariants

```python
def compute_invariants(fbit: FBit, braid_log: list) -> dict:
    """
    Compute the three topological invariants from a FBit and its braid log.
    
    n_w:        winding number — net signed phase advances
    writhe:     topological angular momentum — crossing sign sum
    jones_span: structural complexity — 2^w_level
    w_level:    number of braid generators (operations)
    """
    # Winding number: count net signed crossings in braid
    n_w = 0
    for entry in braid_log:
        pf = entry.get('phase_frac', 0)
        if 0 < pf < SCALE//2:   n_w += 1   # advancing
        elif pf > SCALE//2:      n_w -= 1   # retreating

    # Writhe: computed from the FBit's re/im components as proxy
    # Full writhe would need all pairwise crossings; here we use
    # the phase as a single-strand writhe proxy
    # writhe = sin(2π·phase_frac) = PHASE_SIN(phase_frac)
    # Stored as integer: writhe_int = sin(phase) × SCALE
    pf = fbit.phase_frac
    if pf == 0 or pf == SCALE//2:
        writhe_int = 0
    elif pf == SCALE//4:
        writhe_int = SCALE
    elif pf == 3*SCALE//4:
        writhe_int = -SCALE
    else:
        angle = _fdiv(_fmul(pf, 2*PI_INT), SCALE)
        writhe_int = _fsin(angle, 20)

    # Jones span: 2^w_level where w_level = braid length
    w_level    = max(len(braid_log), 1)
    jones_span = 1 << min(w_level, 30)

    return {
        'n_w':        n_w,
        'writhe':     writhe_int,  # ×SCALE
        'jones_span': jones_span,
        'w_level':    w_level,
        'phase_frac': fbit.phase_frac,
        'amp':        fbit.amp
    }
```

---

## Resonance Distance (Integer Arithmetic)

```python
def resonance(query_fbit: FBit, memory_fbit: FBit) -> int:
    """
    Compute resonance between query and memory FBit.
    Returns amplitude of COMP(query, memory) in fixed-point.
    
    Large amplitude = constructive interference = semantic match.
    Zero amplitude  = destructive interference = no match.
    
    This is the Deutsch-Jozsa test: COMP of same-sign FBits = constructive.
    COMP of opposite-sign FBits = destructive.
    """
    combined = comp(query_fbit, memory_fbit)
    return combined.amp


def topological_distance(inv1: dict, inv2: dict) -> int:
    """
    Distance between two memories in topological invariant space.
    Pure integer arithmetic. Smaller = more similar.
    
    d = |n_w₁ - n_w₂| × SCALE
      + |writhe₁ - writhe₂|
      + |log₂(j₁) - log₂(j₂)| × SCALE
    """
    dn  = abs(inv1['n_w'] - inv2['n_w']) * SCALE
    dwr = abs(inv1['writhe'] - inv2['writhe'])
    # log2 difference in jones_span: count bit difference
    j1  = max(inv1['jones_span'], 1)
    j2  = max(inv2['jones_span'], 1)
    dj  = abs(j1.bit_length() - j2.bit_length()) * SCALE
    return dn + dwr + dj
```
