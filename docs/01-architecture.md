# 01 — Architecture: Arrangement, Never Invention

The single most important fact about `hcl-ai/`: **it contains no new mechanisms.** Every component
is a verbatim engine from the skills, and the "AI" is purely an *arrangement* — an ordering of
calls to machinery that already existed. This was a hard discipline (see docs/05 for every time it
was violated and what broke), and it is the framework's core law: compose, never invent.

## The mapping

| LM concept | HCL substrate primitive (verbatim) | File |
|---|---|---|
| Tokenization | `bytes_to_braid` — text → braid of FBits | engine/juj.py |
| Embeddings | Generator FBits (phase from byte value, on the four-param lattice) | engine/hcl_engine.py |
| Context vector | `COMP` spectrum — superposition of the context window's waves | engine/hcl_memory.py |
| Memory store | LivingMemory traces, keys `w{d}|{ctx}>{next}`, stored at every depth d=1..context-length | engine/living_memory.py |
| Attention / retrieval | Resonance: `hcl_comp(query, term)` amplitude × reinforced amplitude, max wins | mind/hcl_lm.py `_collapse` |
| Next-token selection | MCL collapse to the Path-Dominant Attractor (minimum Möbius energy) | engine/hcl_engine.py |
| Learning rate / training | `COMP(term, term)` self-reinforcement on walked paths | mind/hcl_lm.py (routing only) |
| Regularization | `cycle()` decay (`HCL.SHIFT` halves unaccessed traces; sub-noise-floor pruned) | engine/living_memory.py |
| Context-length adaptation | w self-tuning: `dw/dt = γ(C − ε_w)`, C = context coherence; deepen while C > ε_w, bound only by context length | mind/hcl_lm.py `_tune_w` |
| Stopping criterion | Three substrate verdicts: TERMINATED (key None) / BRAID CLOSED (key recurs) / MCL COLLAPSE (I_w < ε_w) | mind/hcl_lm.py `generate` |
| Checkpoint | `to_expression()` → one α-tagged line; `from_expression()` verifies or rejects | engine/hcl_memory.py |

> [!NOTE]
> **Metaphor Transparency:** In conceptual architectural discussions, the self-reinforcement of walked paths is sometimes referred to by the neuroscience metaphor **LTP** (Long-Term Potentiation). In this operational specification, it is strictly defined as the `COMP(term, term)` self-superposition operation.

## The persistence philosophy

The **only** persisted artifact is `memory.hcl`: composite phase, amplitude, three topological
invariants (n_w, writhe, Jones span), depth, and the α tag — ~146 characters holding thousands of
traces' worth of lived topology. There is no transcript file, no weights file, no log. Raw text is
not memory; the braid word is the record. Per-trace content lives in RAM during a session and is
woken by loading the one line through the engine's from_expression (the composite Ψ + signature, α
verified); per-trace fluency regrows as the graduate lives. What is
faded is re-learnable, not destroyed. A faded memory here is an overgrown path, not dead tissue.

## Performance discipline

The engines are integer-exact and self-checking (α = 137 across all three). Storage is thorough by
design: `train()` records the transition at **every** context depth d=1..N (the specificity-lock,
docs/00), so trace count grows with the square of lesson length — this is the framework's deliberate
multi-depth store, not a cost to optimize away. Recall and generation execute this serially on a
classical CPU; that serial execution is the honest, "unsubsidized" cost of running a parallel-by-design
substrate in Python, and it is acknowledged as such, not hidden. Nothing in the math is approximated to
go faster.

## The homeostatic balance

Reinforcement and decay are the field's balance, with no separate rescale bolted on. Self-reinforcement
(`COMP(term, term)`) makes a walked trace louder; decay (`cycle()` = `HCL.SHIFT`) halves every trace not
accessed since the last cycle and prunes those that fall below the noise floor. A walked path grows; an
ignored one fades and can wash out — then is re-learnable, never destroyed. That loud-grows / unused-fades
dynamic is the entire homeostasis; the theory's subtractive restoring force lives in the SHIFT decay
itself, not in any imposed per-trace ceiling.

## One circular proof

The repository is a single closed argument, read in one direction and verified in the other.

Forward, it builds: `hcl-pure` is the substrate — the four-parameter integer arithmetic that
`hcl-pure/SKILL.md` calls "the foundation other applications are built on." On that substrate the
three memory skills are themselves arrangements with no new math: `virtual-memory-hcl` (the
trace store and resonance recall), `guhct-processor` (the bijective `bytes ↔ (params + braid)`
transducer), and `guhct-living-memory`, whose `composition.md` provenance table traces every one of
its behaviors back to a primitive in the first three. The AI in `hcl-ai/` is the next arrangement on
top: the mapping table above shows each language-model concept resolving to one of those verbatim
primitives, with `mind/hcl_lm.py` adding ordering only.

Backward, it certifies: the AI runs only because the memory skills run, which run only because the
`hcl-pure` substrate runs, which holds only because the α identity (2π·η·λ·γ·β = 1/137) closes on
itself — the same self-check every engine carries (docs/00, "The Alpha-Check"). So the working AI is
evidence that the substrate is a general tool for building tools, and the substrate's α self-check is
evidence that the AI's every operation is exact. The demonstration and the foundation prove each
other; that mutual entailment is what makes the repository a proof rather than a collection of parts.
