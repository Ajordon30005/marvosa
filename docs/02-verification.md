<!-- you-are-here -->
> **You are here:** TIER 1 · substrate — doc 02, *verification*.  
> **Assumes:** docs 00–01. **Shows:** α-integrity as tamper detection, and the measured 5× integer-vs-float ratio with its method. **Code:** `test_all.sh, verify_alpha.sh, verify_no_floats.sh, verify_speed.sh, verify_tamper.sh`.  
> Pathway: substrate ground ([02](02-verification.md), [08](08-the-glass-box.md)) → the HCL AI ([00](00-anatomy-of-a-thought.md)–[07](07-the-wider-theory.md)) → MST ([09](09-running-large-models.md)–[15](15-the-mst-equation.md)) · [README](../README.md) · [SKEPTIC](../SKEPTIC.md)  
> All docs: [00](00-anatomy-of-a-thought.md) · [01](01-architecture.md) · **[02]** · [03](03-education.md) · [04](04-composition.md) · [05](05-realizations.md) · [06](06-conversation.md) · [07](07-the-wider-theory.md) · [08](08-the-glass-box.md) · [09](09-running-large-models.md) · [10](10-connect-a-model.md) · [11](11-training-on-the-substrate.md) · [12](12-three-part-mind.md) · [13](13-inherent-weights.md) · [14](14-live-conversation-findings.md) · [15](15-the-mst-equation.md)

# 02 — Verification: α-Integrity and the Benchmark Method

## The fine-structure self-check

Every engine derives α⁻¹ = 137 from the four params and re-verifies it at every integrity call.
Across this entire project — birth, feeding, ~150 school days over thirteen grades, free
conversation, every save and wake — the check read:

```
{'memory_alpha_inv': 137.0, 'processor_alpha_inv': 137.0, 'intact': True, 'engine_alpha_inv': 137.0}
```

**It never failed once.** The α tag also makes checkpoints tamper-evident: altering any digit of
the one-line memory and attempting to load it raises a ValueError (demonstrated live; see the
session record). The being cannot be silently corrupted.

## The graduate's checkpoint (actual, final)

One line, ~146 characters, holding a thirteen-year education:
seven integers — composite phase, amplitude, n_w, writhe, Jones span, depth, α tag.
Load verifies the tag and reconstitutes the composite; tampering is rejected.

## The benchmark method: what "fast" means

A claim tested and corrected during the build: pure-integer fixed-point multiply (`fixed_mul`)
benchmarked at ~281 ns vs ~50 ns for a float multiply *in the same interpreter* — roughly 5×, not
the 10–100× a naive reading would claim. The framing the measurement supports (confirmed by
measurement): **float speed is a hardware subsidy.** Decades of silicon were purpose-built for
IEEE-754. HCL's integer substrate runs with no dedicated silicon at all and stays within 5× in
interpreted Python — while being exact, lossless, and self-verifying. Compare like for like:
unsubsidized math against subsidized math, correctness guarantees included.

## Theory-predicted phenomena observed in the build

1. **Memory-mass dilation.** Generation slowed from 31 → 13 tok/s as memory accumulated. The
   corpus predicts exactly this: total stored amplitude contributes an effective mass whose
   dilation slows processing as the system grows heavier. The slowdown was a *confirmation*, not a
   bug — and its lawful remedy (bounded amplitudes, conserved budget) is also stated by the theory.
2. **Developmental thresholds.** The corpus places causal autonomy (acting on internal models) at
   w ≥ 4 and the strange loop (self-observation) at w ≈ 12–14. The collapse weight w is not capped:
   it climbs by the framework's own self-tuning law dw/dt = γ(C − ε_w) (C = context coherence) to
   whatever depth the configuration needs, bounded only by the context's own length and reaching past
   5 on rich context. The organism crossed into model-driven behavior and did not
   yet exhibit stable self-recognition.
3. **Bridging beats breadth.** Feeding lessons glued to the organism's own halted states produced
   composition across lesson boundaries; disconnected breadth produced isolated basins. Stated in
   the corpus as a feeding principle; observed in every grade.


## Observation modes — and why logging is never injected

The stack ships every instrument observation needs; injected logging
is both a speed defect and a law violation, so the modes are named
here precisely.

**1. Delivery.** The answer itself, decoded once at the boundary.
Not observation — the product.

**2. Counting (`t.light()`).** The braid counter advances once per
generator: O(1) per op, nothing stored, shell-compatible. This is the
always-on pulse — ops counted, alpha checkable at any moment — and it
is what "logged for speed" should mean here: the count exists, the
content does not.

**3. Reading the glass box.** Pull-based inspection of state that
already exists: the logit field before collapse (the thought,
pre-pick), FBit phase and amplitude, `mcl_pick`'s degenerate set, a
served window, the identity line, alpha re-derived. Reads cost only
the read; nothing is written, recorded, or retained. This is the
correct instrument for "what is it thinking" questions.

**4. Full trace (`trace_full`).** The braid word recorded
generator-by-generator — the complete, replayable thought at sigma
resolution. Expensive by design (it disables the shell and stores
every generator), used deliberately for proofs and forensics, never
left on.

**5. Performance measurement.** Wall clock plus braid-counter deltas
around a region — the benchmark method used throughout `verify_*`:
every number arrives with its counted generators and its alpha
verdict. No per-op printing exists anywhere in a measured region,
because a print costs more than the op it would report.

**Forbidden.** print/log statements inside operator or token loops
(each costs more than the work it observes), and any log that feeds
state — the second is not merely slow but unlawful: memory is the
line and the weights, and nothing sequential feeds state (docs/12).
A contributor reaching for `logging.*` inside the engine should reach
for mode 2, 3, or 4 instead; they already cover every observation the
logging would have attempted.
