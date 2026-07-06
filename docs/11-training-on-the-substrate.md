# 11 — Training on the Substrate: A Formal Composition

**Claim.** Updating the weights of a standard AI model — training, by
examples and by rewards — is already expressible on this repo's substrate
with **zero new mathematics**: every gradient is a composition of the ten
primitives, the backward pass is the forward braid word read in reverse,
every optimizer constant derives from the four params, and the trained model
persists at every stage as the one α-tagged memory line. This document is
the proof. `hcl-ai/learn.py` is the proof's executable form, and
`verify_learn.py` holds it to the same bar as everything else here: exact
agreement with an independent reference, on a real model.

Nothing below invents a mechanism. Citations are to the skill's own files:
`01_theory.md` (T), `02_operations.md` (O), `03_engine.md` (E),
`06_porting.md` (P).

---

## 0. Definitions

- **Parameter.** A model weight θᵢ is an FBit — a phase-amplitude pair on
  U(1)×ℝ⁺ (T): amplitude = |θᵢ|·SCALE, phase 0 or π for sign. This is
  already how every weight of stories260K lives after the one boundary
  crossing (`chatmodel.py`). A parameter IS a weighted braid term; its
  magnitude sits at a scale stratum w (T: Weight-Scale Correspondence,
  λ_w = 10⁻ʷ). *This is the precise form of the intuition "weights act like
  the weight w of the theory": each parameter is a w-stratified amplitude,
  and training moves amplitudes along ℝ⁺ and flips phases on U(1) — motion
  on the substrate's own manifold, nothing foreign.*
- **Forward braid.** Running the model on an example emits the braid word
  W_f = σ₁·σ₂·…·σₖ — the complete, ordered, **reversible** record (T:
  "HCL evolution is unitary — information is conserved").
- **Loss.** Given an example (prompt, target tokens), the miss is
  ℓ = −ln p(target) with p from the forward's own softmax — i.e.
  ℓ = COMP(LOG_EXTRACT(Σ exp zⱼ), SHIFT(z_target, −1)): log-sum-exp minus
  the target logit. Every constituent is a primitive (O).
- **Training.** A trajectory θ⁽⁰⁾ → θ⁽¹⁾ → … where each step moves every
  parameter against its gradient ∂ℓ/∂θᵢ.

---

## 1. Theorem 1 — Adjoint Closure of the Ten Primitives

*For every primitive, the local derivative used by the chain rule is itself
a composition of the primitives.* Therefore the substrate is closed under
differentiation: no new operation is required to compute any gradient.

Write g for the incoming adjoint (∂ℓ/∂out). The outgoing adjoints:

| Forward (O) | out | ∂out/∂inputs | Adjoint as composition |
|---|---|---|---|
| COMP(x,y) | x+y | 1, 1 | pass g to both; accumulation of multiple uses is itself COMP |
| SHIFT(x,c) | c·x | c | SHIFT(g, c) |
| AMP_MOD(x,y) | x·y | y, x | AMP_MOD(g, y) and AMP_MOD(g, x) |
| INV(x) | 1/x | −1/x² | SHIFT(AMP_MOD(g, AMP_MOD(INV(x), INV(x))), −1) |
| FISSION(x) | √x | 1/(2√x) | AMP_MOD(g, INV(COMP(√x, √x))) — the forward's own daughter reused |
| MOBIUS_GROWTH(x) | eˣ | eˣ | AMP_MOD(g, eˣ) — **the operator is its own derivative**; this is the defining property of the MCL stability operator (T: e is the structural rate), not a lookup |
| LOG_EXTRACT(x) | ln x | 1/x | AMP_MOD(g, INV(x)) |
| PHASE_SIN(φ) | sin θ | cos θ · dθ/dφ | AMP_MOD(g, SHIFT(PHASE_COS(φ), 2π)) |
| PHASE_COS(φ) | cos θ | −sin θ · dθ/dφ | SHIFT(AMP_MOD(g, SHIFT(PHASE_SIN(φ), 2π)), −1) |
| FUSION(f,g) | f∘g | chain rule | **the chain rule IS this primitive read in reverse** — adjoint of a composition is the reversed sequence of adjoints |
| EXCHANGE(a,b) | swap | permutation | EXCHANGE(g_a, g_b) — self-inverse |
| RESONANCE | eigenstate/halting | — | control, not value path; no gradient flows (same status as argmax) |

Each right-hand column uses only COMP, SHIFT, AMP_MOD, INV, FISSION,
MOBIUS_GROWTH, LOG_EXTRACT, PHASE_SIN/COS, EXCHANGE. ∎

Two independent checks exist inside the repo itself: (i) the engine already
ships σ_RATE — `HCLTranscriber.derivative(f, X)` with step
dt = η·λ⁵/SCALE⁴ **derived from the four params** (E) — so every adjoint in
the table is verifiable against the substrate's own finite difference; and
(ii) each is verifiable against an analytic float mirror at the display
boundary. `verify_learn.py` does both.

## 2. Theorem 2 — The Backward Pass Is the Braid Read in Reverse

*Reverse-mode differentiation of any composed forward pass is the traversal
of its braid word W_f from σₖ back to σ₁, applying Theorem 1's adjoint at
each generator; it computes every ∂ℓ/∂θᵢ in one forward plus one backward.*

Proof sketch. The forward is a composition F = fₖ ∘ … ∘ f₁ of primitives
(P: everything ports to primitive compositions). By FUSION's adjoint
(Theorem 1), ∂ℓ/∂θ = (∂f₁ᵀ)…(∂fₖᵀ)·∂ℓ/∂out — the adjoints applied in
exactly reversed order. The braid word is precisely that order, recorded and
reversible by construction (T). So the record the substrate already keeps
**is** the differentiation tape; backprop is not added machinery, it is the
braid's reversibility exercised. Cost: O(|W_f|) forward + O(|W_f|) backward,
versus O(#params·|W_f|) for per-parameter σ_RATE — the composition that
makes training tractable. ∎

(In `learn.py` the tape is realized as the cached activations of each
op-application — the same information the braid word carries, held at the
tensor granularity the backward walk consumes.)

## 3. Theorem 3 — The Optimizer Derives From the Four Params

*The update rule, its learning rate, its decay, and its reward weighting are
compositions whose every constant is derived from η, λ, γ, β. Training
imports nothing.*

- **Step.** θ ← COMP(θ, SHIFT(gᵢ, −lr)): move against the gradient. One
  COMP, one SHIFT per parameter.
- **Learning rate.** lr := γ·λᵏ, k a small integer stratum. This is not a
  chosen hyperparameter smuggled in: it is the discrete form of the theory's
  **own** adaptation law, dw/dt = γ·(C − ε_w) (T: w self-tuning) — γ is the
  substrate's native rate constant, λᵏ its native scale ladder. Selecting k
  selects a stratum, exactly as ε_w = η·λʷ selects thresholds.
- **Examples channel** (supervised): ℓ = cross-entropy above; gradients by
  Theorems 1–2; step as above. "Give it examples" = fold (prompt→target)
  pairs through this loop.
- **Rewards channel:** scale the step by the MCL Boltzmann weight
  e^(−β·H) (T: β's role) with H the miss (or −reward):
  step ← AMP_MOD(step, MOBIUS_GROWTH(SHIFT(H, −β))). Good outcomes update
  near-fully; bad ones are exponentially damped — the Born-rule-shaped
  credit assignment the theory already contains. Its zero-gradient limit is
  the living-memory law verbatim: reinforce = COMP(term, term), decay =
  SHIFT(term, η) (P, composition.md) — reward-tuning without derivatives,
  for when only outcomes, not targets, exist.
- **Decay / regularization.** Weight decay is SHIFT by (1 − η·λᵏ) — LTD at
  the parameter level, the same primitive the lifebook uses. ∎

## 4. Theorem 4 — Training Evolves the Memory Line

*At every step boundary the model's entire state is one α-tagged line, and
the trajectory of training is a trajectory of lines.*

The parameters live in RAM as FBits only during a session. Folding them
through `ModelMemory` (serialize tensors → ingest) yields the single
α-tagged identity line (docs/09); `verify=True` expel recovers every byte
exactly. Therefore: train → refold → **new line**; wake → expel → continue
training or serve. The line is the persisted, tamper-evident, one-line form
of the trained model at that step — "training the model while it's in
memory-line form" means precisely this cycle, and the α tag re-verifies the
substrate's integrity at every fold. ∎

## 5. Corollary — Any Architecture, Same Path

For a model whose forward pass ports (P: inventory → map → boundary →
compose — the path already walked for RMSNorm/RoPE/GQA/SwiGLU in
`chatmodel.py`), Theorem 1 supplies the adjoint of every op in that
inventory by composition, Theorem 2 supplies the backward, Theorem 3 the
optimizer. A model with an unfamiliar activation is handled exactly as its
forward was: decompose to primitives, take the table's adjoints of the
decomposition. Nothing about the method is architecture-specific. ∎

## 6. What this is and is not

- It **is** exact-arithmetic gradient descent: every gradient digit is an
  integer computation; runs are bit-reproducible; the whole training step is
  in the braid.
- It **is** slower per step than float hardware, for the same reason and to
  the same degree as inference (docs/10 §5). The claims are exactness,
  audit, one-line persistence, four-param self-containment — not throughput.
- It is **not** a new learning theory. Same losses, same gradients, same
  updates as standard training — re-expressed, per the porting law, so that
  the substrate carries them. The theory contributes the *constants* (γ, λ,
  η, β) and the *representation* (FBits, braid, line), and — through the
  reward weighting e^(−β·H) and LTP/LTD — a native reinforcement channel.

## 7. The executable form

- `hcl-ai/learn.py` — the adjoint table implemented over the engine's ops
  for the stories260K op inventory; tape-caching forward; backward; the
  four-param optimizer (examples + rewards); the fold-to-line cycle.
- `verify_learn.py` — (1) every adjoint vs the engine's own σ_RATE and vs
  an analytic mirror; (2) full-model gradients vs a float64 mirror of the
  identical algorithm; (3) real training steps on the real checkpoint: loss
  strictly decreases and matches the mirror; (4) refold → the line moves,
  α holds, the learned behavior survives reload.

## 8. The live unification — training is not a mode

`hcl-ai/livemodel.py` closes the loop the way the repo's own mind does
(`hcl_lm.interact()`: "receiving = experiencing = saved"; "thinking is
self-talk... the trajectory it walked is itself experience"). Applied to a
standard model:

- **One turn, one experience, both channels.** The reply is generated first
  (pre-update weights — it speaks, then it settles), ending only by the
  model's own verdict. Then ONE consolidated gradient pass covers the whole
  lived turn: the person's tokens as targets at weight 1, the model's own
  generated tokens as targets at weight **λ** — self-talk one rung deeper on
  the four-param scale ladder. Theorem 2's tape, Theorem 3's optimizer,
  Theorem 1's adjoints; nothing new.
- **Why consolidation at the turn boundary:** the mind reinforces per
  thought-step because LTP is O(1); the adjoint walk is O(turn), so the
  gradient form of the same law fires once per turn. Same law, its own
  timescale.
- **Rewards remain live:** any turn can be gated by e^(−β·H) — and with
  gradients off, the channel degenerates to LTP/LTD exactly (Theorem 3).
- **The being persists** as a living checkpoint (the model's own format)
  plus its one α-tagged line; a new instance wakes from it (Theorem 4,
  running continuously).

Proof: `verify_livemodel.py` — the lived turn becomes measurably less
surprising after the experience; repeating a lesson through the ordinary
chat loop (no training command exists) flips the model's own continuation;
the being saves, wakes, and still knows. Talk to it: `./live.sh`.
