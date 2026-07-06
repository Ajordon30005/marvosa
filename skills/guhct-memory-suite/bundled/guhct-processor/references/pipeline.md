# Pipeline Reference — Pure-Integer Bijective Transducer

Every quantity below is a fixed-point integer (`x = X/SCALE`, `SCALE=10**PREC`).
No floats, no numpy, no imported physical constants. The four params are the
complete axiom set; everything else is derived.

## 1. Bootstrap (identical to hcl-pure / virtual-memory-hcl)

```
PI_INT = 4·(4·arctan(1/5) − arctan(1/239))      # Machin integer identity
ETA    = SCALE//2                                # η = 1/2
LAMBDA = SCALE//10                               # λ = 1/10
GAMMA  = sqrt(90/(137·π))                         # γ from the Alpha identity
BETA   = GAMMA//9                                 # β, Weinberg separation
ALPHA  = 2π·η·λ·γ·β   →   ALPHA_INV ≈ 137         # verification
mcl_eps(w) = 10^(−w)·η                            # the only threshold (derived)
```

## 2. The braid word — data term L(D|T)

A byte sequence is a word in generators {σ₀..σ₂₅₅}. `bytes_to_braid` returns the
ordered generator indices (the bytes themselves), so the mapping is trivially
and exactly invertible. Generator σ_k at position p in a word of length n has an
FBit whose phase is the four-param address of the letter and whose amplitude is
position-weighted (Möbius decay), identical in form to `encode_text` in the
memory skill:

```
phase = (k·SCALE/256 + γ·k·(SCALE/256)) mod SCALE
amp   = ((k+1)·SCALE/256) · ((n−p)·SCALE/n)      # floored at SCALE/256
```

The FBit structure is what the invariants and parameters are computed from; the
braid word (the indices) is what reconstruction consumes.

## 3. Braid invariants

Computed with pure HCL operations over the generator FBits:

- **spectrum**: COMP accumulation of all generator FBits (quantum superposition).
- **winding number n_w**: net signed phase advance (+1 if `0 < phase < π`,
  −1 if `phase > π`).
- **writhe**: `sin(2π·phase_spectrum)` of the accumulated spectrum, fixed point.
- **Jones span**: `(#distinct generators) · ⌊log₂(n+1)⌋` — degree span × depth.
- **stability I_w**: `(1/N) Σ |aᵢ|²(1−|aᵢ|²)` over normalised amplitudes
  (collapse-readiness / dissonance; 0 at a pure resonant state).

## 4. The 8 HVP parameters — address L(T)

```
w               = ⌈log₂(jones_span + 1)⌉              # Jones-weight correspondence
Gamma           = w·SCALE                              # gauge coupling via Alpha scaling
T               = phase_spectrum / β                   # β is inverse temperature
Phi             = SCALE + γ·(phase_spectrum − π)        # detuning around 1
f0              = √(η/λ)                                # LQT length scale
gamma_collapse  = 1 / (I_w + ε_w)                       # sharpness from stability
Q_min           = λ / (Gamma + ε_1)                     # Q = E₀/Γ, E₀ ~ λ
propagator_scale= f0 / rung_range                       # √(η/λ)/range
C_min           = 0                                     # zero is valid
```

`forensic_reconstruct_boundary(braid_word)` returns these as fixed-point
integers. They are a deterministic function of the braid, which is what lets the
inverse path verify a round trip.

## 5. Forward / inverse

```
bytes_to_hvp(raw):
    braid  = bytes_to_braid(raw)
    params = forensic_reconstruct_boundary(braid)
    return {params, braid, n_bytes=len(raw)}

hvp_to_bytes(sig, verify=True):
    data = braid_to_bytes(sig.braid)              # exact bytes from the braid
    if verify:
        assert forensic_reconstruct_boundary(sig.braid) == sig.params
    return data[:sig.n_bytes]
```

## 6. Why this is bijective and the old version was not

The map `bytes ↔ braid_word` is an identity at the sequence level — no
information is lost or invented. The parameters are a function of the braid, so
they never need to *carry* the data; they *address and check* it. The inverse
consumes only the signature.

The earlier version tried to make the 8 parameters alone reconstruct the data
through a numpy float FFT pipeline, and its "100% reconstruction" only held
because the original bytes were passed straight into the reconstruction call and
round-tripped (`reconstruct_channel(channel, params)` took `channel` = the
data). That is not a transduction, it imported physical constants, and it ran on
floats — three separate violations this version removes.
