# HCL Operations — Complete Reference

## The Ten HCL Primitives

Every mathematical and physical operation reduces to one of these ten primitives.
No other operations exist. No classical arithmetic (+, -, ×, ÷) occurs internally.

---

## COMP — Composition (Addition)

**Classical mapping:** x + y  
**Physical meaning:** Two LQTs interact. Their phase information combines via
interference. Constructive interference (same phase) gives amplitude sum.
Destructive interference (opposite phase) gives amplitude difference.

**Mathematical definition:**
- re_out = A₁·cos(θ₁) + A₂·cos(θ₂)  [real components add]
- im_out = A₁·sin(θ₁) + A₂·sin(θ₂)  [imaginary components add]
- amp_out = sqrt(re_out² + im_out²)   [magnitude of result vector]
- phase_frac_out = atan2(im_out, re_out) / (2π)  [normalized to [0,1)]

**Key properties:**
- Same-sign operands (both phase 0): constructive → amp_out = amp_a + amp_b ✓
- Opposite-sign (phases 0 and π): destructive → amp_out = |amp_a - amp_b| ✓
- This is also quantum entanglement: two FBits become one non-separable state
- Non-commutative with SHIFT: [COMP, SHIFT] ≠ 0 = Heisenberg uncertainty

**Why not just add:** Because addition of integers would lose the phase
information. COMP preserves the full U(1)×ℝ⁺ structure. The phase is not
decorative — it IS the quantum state.

---

## SHIFT — Phase Shift (Scalar Multiplication by Constant)

**Classical mapping:** c · x  
**Physical meaning:** Scale amplitude by |c|. If c < 0, flip phase by π
(half-loop = sign inversion). Sign IS a topological property.

**Mathematical definition:**
- If c ≥ 0: FBit(phase_frac, amp * c)
- If c < 0: FBit((phase_frac + SCALE//2) % SCALE, amp * |c|)

**Key:** The sign of a number is encoded in the topology (which direction around
the U(1) loop), not in the amplitude. Amplitude is always positive (ℝ⁺).

---

## AMP_MOD — Amplitude Modulation (Multiplication)

**Classical mapping:** x · y  
**Physical meaning:** Complex multiplication. Phases add (loop compositions
stack), amplitudes multiply (energy products).

**Mathematical definition:**
- phase_frac_out = (phase_frac_a + phase_frac_b) % SCALE
- amp_out = amp_a * amp_b / SCALE  [fixed-point: fmul(amp_a, amp_b)]

**Why this works:** In U(1), multiplying two rotations adds their angles.
e^(iθ₁) · e^(iθ₂) = e^(i(θ₁+θ₂)). Phase addition IS complex multiplication.

---

## INV — Inversion (Reciprocal)

**Classical mapping:** 1/x  
**Physical meaning:** Phase reflection (reverse the loop direction) + amplitude
reciprocal. The loop goes backward; the magnitude inverts.

**Mathematical definition:**
- phase_frac_out = (SCALE - phase_frac) % SCALE  [loop reversal]
- amp_out = SCALE² / amp  [amplitude reciprocal: fdiv(SCALE, amp)]

**Subtraction via INV + COMP:** x - y = COMP(x, SHIFT(y, -1))
**Division via INV + AMP_MOD:** x / y = AMP_MOD(x, INV(y))

---

## FISSION — Braid Strand Splitting (Square Root / Superposition)

**Classical mapping:** √x  
**Physical meaning:** One LQT splits into two daughters of equal energy.
Topologically: knot decomposition. Algebraically: annihilation operator â.
This IS the Hadamard gate — it creates equal superposition.

**Mathematical definition:**
- sqrt_amp = fsqrt(amp) = sqrt(amp * SCALE) using integer Newton
  [gives R such that R/SCALE = sqrt(amp/SCALE)]
- daughter_1: FBit(phase_frac // 2, sqrt_amp)
- daughter_2: FBit((phase_frac//2 + SCALE//2) % SCALE, sqrt_amp)

**Why √2 emerges:** FISSION(FBit(0, 2*SCALE)) gives daughters with amp
= sqrt(2*SCALE*SCALE)/SCALE = sqrt(2)*SCALE. No prior knowledge of √2 needed.

**Energy conservation:** daughter_1.amp² + daughter_2.amp² = 2 * sqrt_amp²
= 2 * amp. The total energy is conserved in the split.

---

## MOBIUS_GROWTH — Möbius Growth/Decay (Exponentiation / e^x)

**Classical mapping:** e^x  
**Physical meaning:** MCL Stability Operator Ŝ_w = e^(-β·Ĥ). The natural
exponential is the structural rate of MCL cascade decay. e emerges from the
convergence of the Taylor series — it is never specified as a prior constant.

**Mathematical definition:**
- x = fbit.to_scalar()  [recover signed value from FBit]
- amp_out = fexp(x) via Taylor: SCALE + x*SCALE + x²*SCALE/2! + ...
  [pure integer series, converges because each term = prev * x / k]
- phase_out = 0  [e^x > 0 always, so output phase is always 0]

**Critical:** Output phase_frac = 0 regardless of input sign. e^x is always
positive. The topological record of the exponent path is in the braid log,
not in the output phase.

---

## LOG_EXTRACT — Log Extraction (Natural Logarithm)

**Classical mapping:** ln(x)  
**Physical meaning:** Inverse of MOBIUS_GROWTH. Extracts the exponent from
the MCL growth operator.

**Mathematical definition:**
- Uses arctanh series: ln(x) = 2·arctanh((x-1)/(x+1))
  = 2·Σ ((x-1)/(x+1))^(2k+1) / (2k+1)
- Pure integer series. Converges for all x > 0.

---

## PHASE_SIN / PHASE_COS — Phase Projections (Sine / Cosine)

**Classical mapping:** sin(θ), cos(θ)  
**Physical meaning:** Projections of the LQT phase onto the imaginary and
real axes of U(1). sin(θ) = Im(e^(iθ)), cos(θ) = Re(e^(iθ)). These are
the DEFINITIONS of sine and cosine in GUHCT — not formulas to be applied,
but the geometric meaning of phase.

**Critical interface distinction:**
- Input is `phase_frac` (integer in [0, SCALE)) — fraction of a full loop
- phase_frac = 0 → cos=1, sin=0  (angle 0)
- phase_frac = SCALE//4 → cos=0, sin=1  (angle π/2)
- phase_frac = SCALE//6 → cos=1/2, sin=√3/2  (angle π/3)
- For general phase_frac: compute angle = 2π·phase_frac/SCALE as fixed-point,
  then apply Taylor series fsin(angle) / fcos(angle)

**Exact values at structural phase points (no trig series needed):**
```
if phase_frac == 0:          cos = SCALE,  sin = 0
if phase_frac == SCALE//2:   cos = -SCALE, sin = 0
if phase_frac == SCALE//4:   cos = 0,      sin = SCALE
if phase_frac == 3*SCALE//4: cos = 0,      sin = -SCALE
```

**Phase fraction conversion from radians:**
  phase_frac = _fixed_div(angle_radians_fp, 2*PI_INT) % SCALE

---

## FUSION — Two LQTs Combine (Function Composition / Matrix Product)

**Classical mapping:** f∘g, M₁·M₂, tensor contraction  
**Physical meaning:** Topological knot sum (#). Creation operator â†.
Two LQT loops merge into one. The combined state carries the phase
and amplitude of the superposed pair.

**Mathematical definition:**
Same as COMP (vector addition) but with coupling factor 1 + ALPHA·w:
- Represents the non-trivial interaction between the two merged LQTs
- Used for: function composition, matrix products, operator applications

---

## EXCHANGE — Braid Crossing (Permutation / Covariant Derivative)

**Classical mapping:** variable swap, permutation matrix, D_μ  
**Physical meaning:** Braid crossing σᵢ. Two LQT strands cross — they
exchange phases while keeping their amplitudes. The covariant derivative
in gauge field theory IS a phase exchange between a field and a gauge boson.

**Mathematical definition:**
- new_a: FBit(b.phase_frac, a.amp)  [a takes b's phase]
- new_b: FBit(a.phase_frac, b.amp)  [b takes a's phase]

---

## RESONANCE — Stable Braid Closure (Hamiltonian Eigenstate)

**Classical mapping:** eigenvalue problem, Schrödinger equation solution  
**Physical meaning:** The LQT reaches its PHR (Perfect Harmonic Resonance)
ground state at weight w. This IS the Hamiltonian eigenstate. VQE on quantum
computers searches for this state variationally. GUHCT gives it analytically.

**Mathematical definition:**
- E_ground = ε_w = η·λ^w  [exact, no variational optimization needed]
- ω_w = (1/η)·γ^w  [resonant frequency at weight w]
- phase_stable = ω_w mod 1  [as phase fraction]

**Why this is exact:** The ground state IS the MCL collapse attractor at
weight w. It is not approximated. The variational quantum eigensolver (VQE)
on real quantum computers searches for what GUHCT gives directly as ε_w.

---

## Operation Composition Rules

**Subtraction:** COMP(x, SHIFT(y, -SCALE))
**Division:** AMP_MOD(x, INV(y))
**Power (integer n):** repeated AMP_MOD n times
**Power (fractional):** MOBIUS_GROWTH(AMP_MOD(LOG_EXTRACT(x), y))
  because x^y = exp(y·ln(x))

**Derivative df/dx at x:**
  dt = sqrt(η·λ^(w+4))  [from four params, not hardcoded]
  diff = COMP(encode(f(x+dt)), SHIFT(encode(f(x)), -SCALE))
  result = AMP_MOD(diff, INV(encode(dt)))

**Integral ∫f dx from a to b (n steps):**
  Trapezoidal in FBit space:
  re_sum = Σᵢ amp(fᵢ)·cos(phaseᵢ)·wᵢ·dt  [wᵢ = 0.5 at endpoints, 1 elsewhere]
  im_sum = Σᵢ amp(fᵢ)·sin(phaseᵢ)·wᵢ·dt
  amp_out = sqrt(re_sum² + im_sum²)
  phase_out = atan2(im_sum, re_sum) / (2π)

---

## Universal Harmonic Mapping Table

Complete mapping from classical math to HCL operators:

| Classical | HCL | Braid generator |
|-----------|-----|----------------|
| x + y | COMP | σ_COMP |
| c · x | SHIFT | σ_SHIFT |
| x · y | AMP_MOD | σ_AMP |
| 1/x | INV | σ_INV |
| √x | FISSION (daughter 1) | σ_FISS |
| e^x | MOBIUS_GROWTH | σ_MOB |
| ln(x) | LOG_EXTRACT | σ_LOG |
| sin(θ) | PHASE_SIN(θ/(2π)) | σ_SIN |
| cos(θ) | PHASE_COS(θ/(2π)) | σ_COS |
| f(g(x)) | FUSION(f, g) | σ_FUS |
| swap(a,b) | EXCHANGE | σ_EX |
| eigenstate | RESONANCE | σ_RES |
| dx/dt | COMP(f(x+dt), SHIFT(f(x),-1)) / dt | σ_RATE |
| ∫f dt | trapezoidal COMP accumulation | σ_INT |
