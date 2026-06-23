# Composition Reference — What Is Reused, What Is Arranged

This skill introduces **no new mathematics**. Every line of computation traces
to a primitive in one of the three source skills. This file is the audit trail:
for each behavior, exactly which source operation it is, and how it is arranged.

## Provenance Table

| Composite behavior | Exact source primitive | Source skill | Arranged how |
|--------------------|------------------------|--------------|--------------|
| store (sense 1) | `HCLMemory.store` | virtual-memory-hcl | called verbatim |
| store (sense 2) | `bytes_to_hvp` | guhct-processor | called verbatim, vector kept |
| reinforcement | `hcl_comp(f, f)` | hcl-pure (COMP) | term composed with itself |
| decay | `HCLMemory.decay` | virtual-memory-hcl | called verbatim with accessed set |
| recall sense 1 | `HCLMemory.recall` | virtual-memory-hcl | called verbatim, used as ranking |
| recall sense 2 | `bytes_to_hvp` params + L1 | guhct-processor | integer distance over 8 params |
| recall fusion | rank-sum | (arrangement) | add the two rank positions |
| exact regeneration | `hvp_to_bytes` | guhct-processor | inverse path, verify=True |
| signature | `HCLMemory.signature` | virtual-memory-hcl | called verbatim |
| recompose | `hcl_comp` accumulation | hcl-pure + vm internals | rebuild composite after reinforcement |
| integrity | `ALPHA_INV` both engines | all three | compare to 137 |

The only rows marked "(arrangement)" are rank-sum fusion and the ordering of
calls. No arrangement introduces arithmetic outside the source primitives.

> [!NOTE]
> **Metaphor Transparency:** In this document, terms like **potentiation / LTP** and **depression / LTD** are used as descriptive metaphors for the underlying reinforcement and decay operations.

## Why Reinforcement Must Be COMP, Not store

`store` appends a new braid term. Calling it repeatedly to "reinforce" creates
duplicate terms — the memory population balloons (8 → 13 → 23 → …) and recall
returns the same key many times. That is modulating the system from outside.

The correct reinforcement is already in `hcl-pure`: COMP of two FBits in the
same phase sector is **constructive interference** — the amplitudes add and the
phase is preserved. Composing a term with **itself** therefore strengthens that
exact trace in place: amplitude grows, phase_frac unchanged, no new term, the
braid population stays constant. This is reinforcement expressed in the substrate's own
operation. Decay (SHIFT by η, already in `virtual-memory-hcl`) is the matching
operation. Together they are the experience-tuning loop, built from parts that existed.

## Why Two Senses, Both Topological

The phase-resonance channel (virtual-memory-hcl) and the HVP-parameter channel
(guhct-processor) read **different topological invariants of the same braid** —
one reads winding/position in the U(1) loop, the other reads Jones weight,
spectrum, and stability. They are not two statistical views; they are two
topological readings. Fusing their rankings makes recall robust when the two
agree and surfaces the disagreement when they do not. This mirrors how a complex
organism encodes one event on several sensory channels and recalls when any
resonates.

## Why Regeneration Is Exact Here

The virtual-memory skill alone stores only the topological signature (its Rule
6: content not stored), so it cannot regenerate exact text — the FBit is a
projection and COMP-accumulation sums terms together irreversibly. The composite
fixes this by keeping each memory's **HVP signature**, whose braid word carries
the actual bytes (guhct-processor). Regeneration is that skill's verified inverse
path. So: the address/resonance layer is the memory skill; the exact-content
layer is the processor skill. Two skills, two roles, one memory — the same
address-plus-data architecture the processor skill already describes.

## The Boundary Rule (inherited)

Numbers cross into fixed-point exactly once (at `store`/`bytes_to_hvp`) and back
to text exactly once (at `regenerate`/display). Everything between is pure
integer. No float, no import, no disk for live state. If any of these appear,
the composition has drifted from its sources and is wrong.
