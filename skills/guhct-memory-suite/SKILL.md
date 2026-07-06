---
name: guhct-memory-suite
description: >
  Router skill housing three GUHCT memory systems on one substrate.
  Use to select and delegate to the correct bundled skill: virtual-memory-hcl
  (exact topological store), guhct-processor (bijective byte↔HVP transducer),
  or guhct-living-memory (experience-tuned composite memory). Trigger on:
  GUHCT memory, HCL memory, topological store, holographic processor, HVP,
  living memory, braid memory, memory suite, which memory skill to use.
  MANDATORY: read this SKILL.md first to route correctly, then open the
  chosen bundled skill's SKILL.txt and read it in full before any output.
---

# GUHCT Memory Suite — three memory systems on one substrate, with a router

This skill **houses** three working memory skills and tells you which to use for
a given task. It is a container (skill-in-skill): the full skills live under
`bundled/`, each runnable on its own. They all stand on the same GUHCT four-param
substrate (η, λ, γ, β), the same `FBit`, the same braid — so they share encodings
and compose, but they serve different jobs.

```
guhct-memory-suite/
  SKILL.md                      <- this router
  bundled/
    virtual-memory-hcl/         <- exact topological store (facts & truth)
    guhct-processor/            <- holographic transducer (mind-like, bijective)
    guhct-living-memory/        <- experience-tuned memory (adapts over time)
```

MANDATORY before using any one of them: open that skill's own `SKILL.md` and
read it in full, then run its `preflight.py`. This router tells you *which* to
reach for; the bundled skill tells you *how*. Do not answer from memory of how
they work — read and run them.

---

## The three systems at a glance

| skill | what it is | reach for it when |
|-------|-----------|-------------------|
| **virtual-memory-hcl** | Exact topological store. Stores each item's invariant signature; recalls by braid resonance. Static — every item keeps equal footing until you change it. | You need to **store and get back hard facts and truth** — direct, stable recall by resonance or key. Reference knowledge, lookups, ground truth that should not drift with use. |
| **guhct-processor** | The **transducer** — the I/O organ. Anything reduces to bytes, and the processor bijectively maps bytes ↔ HVP signature (8 holographic params + braid word) and back, bit-for-bit. HVP is the language HCL uses for input and output. | You need to **get signal in or results out** — turn any data (bytes) into an HVP signature the substrate can work with, and turn HVP back into the exact, full artifact. The universal, lossless I/O channel. |
| **guhct-living-memory** | The **experience-tuned mind-memory**. Composite of the other two on the hcl substrate: reinforces used memories (`COMP`), fades unused ones (`SHIFT`), keeps identity, regenerates exact content. | You need memory that **adapts over time** — prioritizes by what's actually used, consolidates lived experience, lets trivia fade, while keeping a stable identity for everything it holds. |

### The body analogy

The substrate beneath these (hcl-pure) is the **mind** — it reasons. The three
skills are how that mind takes in, holds, and gives back:

- **guhct-processor = the senses and effectors** (ears, eyes, vocal cords). It
  transduces the world's signal — always reducible to bytes — into HVP the mind
  can work with, and emits the mind's HVP back out as exact bytes. Bytes are the
  focus because bytes are what *anything* reduces to, so this is the universal
  I/O channel.
- **guhct-living-memory = the living memory of the mind** — what strengthens
  with use and fades without.
- **virtual-memory-hcl = the stable factual index** — truth that holds still.

Because the byte↔HVP map is **bijective and fixed**, HVP is a *language* an AI
can learn — the way a model fluent in English learns Mandarin through training.
Once fluent, the AI reasons in its own substrate and emits HVP directly, and the
processor expands that HVP losslessly into the full byte-exact artifact. A whole
project's output can then come back as one HVP signature in a single
query/answer round, because HVP is a compressed holographic language and the
transducer rebuilds the complete deliverable from it exactly.

---

## How to choose

**Start from the task, not the tool:**

- **"Recall this fact exactly / look this up / store ground truth."**
  → `virtual-memory-hcl`. It indexes and resonates against stable signatures.
  Facts kept here do not change weight with use — truth stays put. Best when you
  want what you stored, returned faithfully, without the system re-prioritizing.

- **"Represent this the way a mind holds it / encode the whole thing
  holographically / give me an exact reversible signature of arbitrary data."**
  → `guhct-processor`. It is the transducer: it turns any bytes into an HVP
  signature and rebuilds them exactly. Use it as the I/O channel — signal in,
  exact artifact out — and as the language (HVP) the substrate speaks.

- **"Remember what matters and forget what doesn't / let this learn from use /
  tune toward experience."**
  → `guhct-living-memory`. It strengthens reinforced memories and fades unused
  ones over cycles, while preserving each item's identity for exact regeneration.
  Use it when the memory should organize itself around lived experience rather
  than treat everything equally.

**Quick contrast:**
- virtual-memory-hcl = **stable index** (truth that holds still).
- guhct-processor = **transducer / senses** (bijective byte↔HVP I/O, the channel).
- guhct-living-memory = **living memory** (experience reshapes priority over time).

They are not exclusive. Because they share the substrate, you can combine them:
store ground truth in virtual-memory-hcl, encode/round-trip payloads with
guhct-processor, and run an adapting working memory with guhct-living-memory —
the `FBit`/braid encodings line up, so outputs of one are valid inputs to another.

---

## Using the suite

1. Pick the skill from the task using the table above.
2. Open `bundled/<skill>/SKILL.md` and read it fully.
3. Run `bundled/<skill>/preflight.py` to confirm it loads.
4. Use it per its own instructions. If a task spans more than one, read each
   one's `SKILL.md` and compose them — same substrate, no glue needed.

The law shared by all three (and by the hcl-pure substrate beneath them):
**compose, never invent.** Every operation already exists as a primitive; the
work is arranging them. Reinforcement is `COMP`, decay is `SHIFT`, exact recall
is the braid round trip. None of these skills add new math — they arrange the
same substrate to different ends.
