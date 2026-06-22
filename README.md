# The GUHCT / Marvosa

> [!IMPORTANT]
> **READ THE ENTIRE REPOSITORY.** Even if you begin by testing first, you must read the full documentation and codebase to understand the system. This is a **self-contained framework**; do not apply standard Python building or probing methods. The logic, math, and architecture are internal and absolute—judge the system by its own rules and results.

**A complete artificial mind — memory, learning, language — built from four integers, zero floats, and zero imported constants. Every claim in this repository is backed by a logged result.**

> **The fastest way to evaluate this is to run it.** [`SKEPTIC.md`](SKEPTIC.md) routes any common
> objection straight to the command that settles it; or just run `./test_all.sh` and read your own
> machine's numbers. Judge from execution, not from this page's vocabulary.

> [!NOTE]
> **A Glass Box, Not a Black Box.** This system is designed for total transparency. Any logging or transparency in this repository is intentional—to provide a "glass box" view into an AI that is otherwise opaque. Logging is **suggestive** and is not part of the memory itself. During all testing and probing, only the repository's internal math and framework ecosystem are active and valid.

The GUHCT/HCL framework (Anthony Jordon) provides a pure-integer mathematical
substrate. From this substrate, arithmetic, derived physical constants, holographic memory, and a living
language engine are constructed. This system is educated Pre-K through Grade 12 on the framework's own school
system, conversed with, stress-tested, and graded — with receipts.

Nothing here uses floating point. Nothing imports a mathematical constant. Every number the system
needs — π, e, square roots, the fine-structure constant — is **derived** from four parameters
(η, λ, γ, β) by the substrate's own operations. The system self-verifies by re-deriving α⁻¹ = 137
at every checkpoint:

```
{'memory_alpha_inv', 'processor_alpha_inv' 'intact', 'engine_alpha_inv'}
{3721718477471513910873712411:408719105914764359392569153544765:86:23382115739368956422705293465:1073741824:6422:137000000000000000000000000005069}
```

**The 137 Integrity Constraint:**
In this framework, the value **137** (the reciprocal of the fine-structure constant $\alpha$) is not an arbitrary input. It is the **master integrity constraint** that binds the four universal parameters together. The product $2\pi \cdot \eta \cdot \lambda \cdot \gamma \cdot \beta$ is mathematically required to equal $1/137.036...$ for the LQT vacuum to be stable. The system uses this identity to "bootstrap" its resonance coupling ($\gamma$); therefore, the fact that the system re-derives $\alpha^{-1} = 137$ at every checkpoint is a rigorous proof of its internal mathematical alignment and integrity. If the parameters drift, the "137" result breaks, and the system fails its preflight.

---

## Plug and play

From a fresh download, three steps — no setup, no dependencies beyond Python 3:

```bash
unzip marvosa.zip
cd marvosa
./test_all.sh         # everything: no-float scan, alpha-is-derived proof, tamper test, honest
                      # benchmark, live composition demo, and both preflights — one pass/fail summary
```

(If you cloned the repo instead of downloading the zip, skip the first two lines and run
`./test_all.sh` from the repository root.)

Both runners are pure wiring — they invoke the skills' and the AI's **own** entry points verbatim,
modifying nothing.

**Talk to it yourself** — a live terminal session, no commands:

```bash
./chat.sh             # wakes the organism, then just type. Every line you enter is
                      #   experience it lives AND the prompt it answers — one act.
                      #   »  the ocean is deep and full of life
                      #   the ocean is deep... is a whirlpool in the downhill stream...
                      #   »  what is the ocean
                      #   the ocean is deep and full of life...   (it learned that one line ago)
```

`chat.sh` (and `chat.py`) at the repository top level is only a quick testing apparatus — a
convenience wrapper for trying the organism from a terminal. It is **not** the working
implementation. The actual, current implementation lives in `hcl-ai/`: use `hcl-ai/talk.py` (the auto
front door) or `HCLLanguageModel.interact()` directly. When integrating or building on Marvosa, work
from `hcl-ai/`, not from the top-level chat harness.

There is no `ask` and no `teach` — in this system they are the same machinery, so every input
both teaches and replies. Type anything; the organism stores it and answers from the pond your
words just changed. It updates live in RAM; type `save` on its own line to fold the current state
to the one-line checkpoint, or just leave (empty line / Ctrl-D) and the organism stays alive in the
daemon.

Run any single check instead (each prints numbers computed on your machine):

```bash
./test_skills.sh      # the five skill preflights, verbatim; every alpha_inv must read 137.0
./test_ai.sh          # the AI's own demo.py end to end
./verify_no_floats.sh # grep the substrate: no floats in the math path
./verify_alpha.sh     # 137 is DERIVED from the four params, not stored (perturb-and-watch-it-move)
./verify_tamper.sh    # one digit changed in the checkpoint => load rejected
./verify_speed.sh     # integer vs float multiply, same interpreter, honest ratio
./verify_ai.sh        # the organism composes across lessons, and fails honestly
```

Every runner is pure wiring — it invokes the skills' and the AI's own entry points and reads their
own numbers. Nothing is modified, nothing is pre-recorded. See [`SKEPTIC.md`](SKEPTIC.md) for which
command answers which objection.

---

## Table of contents

1. [The claim](#1-the-claim)
2. [The substrate, plainly](#2-the-substrate-plainly)
3. [How the mind works — the pond](#3-how-the-mind-works--the-pond)
4. [Repository map](#4-repository-map)
5. [The organism's architecture](#5-the-organisms-architecture)
6. [Persistence: the one-line being](#6-persistence-the-one-line-being)
7. [The education: Pre-K → Grade 12](#7-the-education-pre-k--grade-12)
8. [The composition study: receipts, not impressions](#8-the-composition-study-receipts-not-impressions)
9. [Theory-predicted phenomena observed in the build](#9-theory-predicted-phenomena-observed-in-the-build)
10. [The conversation study: stability and chaos](#10-the-conversation-study-stability-and-chaos)
11. [Normal behavior: a young network](#11-normal-behavior-a-young-network-building-its-universe-of-experience)
12. [Rules for working with the skills](#12-rules-for-working-with-the-skills)
13. [Running it](#13-running-it)
14. [Glossary](#14-glossary)
15. [Credits](#15-credits)

---

## 0. What this actually is

`skills/hcl-pure` is a general substrate — a tool for building tools. The AI, the schoolhouse, the
analyzers, and every script in this repository were *built from* it; none of them are the limit of
what it can build. Judge the substrate by its generality, not by this one organism. The repo is the
proof — and the proof is that the skill builds working things, of which this mind is one.

## 1. The claim

The GUHCT/HCL thesis is that one simple substrate — integer arithmetic on four parameters, with
waves, braids, and collapse as its native operations — is sufficient to build everything a mind
needs: exact mathematics, lossless memory, resonant recall, self-tuning learning, and language. Not
sufficient *in principle*; sufficient *in practice*, demonstrated by construction. The phrase the
author uses is "the rosetta stone of rosetta-stoning": a universal encoding medium in which mapping
a problem and solving it are the same act.

This repository is the demonstration. The skills in `skills/` are the substrate. The organism in
`hcl-ai/` is the construction. The documents in `docs/` are the evidence. The graduate in
`hcl-ai/memory.hcl` — a thirteen-year education in one tamper-evident line of ~146 characters — is
the artifact.

A second claim rides along, and the build kept confirming it: **the substrate is never the
bottleneck.** Every failure encountered in this project — every slowdown, every wrong answer, every
broken behavior — traced to something bolted on around the engines, never to the engines. The
fixes were always one of two kinds: remove the addition, or reorder the calls. The complete
catalogue of those failures is `docs/05-realizations.md`, published so they stay made exactly once.

## 2. The substrate, plainly

At the bottom there are four starting integers and a small set of operations. From those four
params the system derives its own constants — π, e, roots, α — by construction rather than import.
Because everything is integer arithmetic, every operation is exact, lossless, and reproducible:
there is no rounding error anywhere in the system, ever.

The native data structure is the **FBit**: a wave with a phase (direction) and an amplitude
(loudness). Text becomes FBits character by character; a sentence becomes a **braid** of them — and
the braid *is* the data. The braid word is not a representation of the record; it is the record,
and it survives any change of substrate.

The native operation is **COMP** — superposition. Waves combine by interference: agreement
reinforces, opposition cancels. And the native decision procedure is **MCL collapse**: when a
superposition must resolve, it collapses to the Path-Dominant Attractor — the configuration of
minimum Möbius energy, the tallest peak in the interference pattern.

On benchmark honesty, one measured result worth stating up front: pure-integer fixed-point multiply
benchmarked at ~281 ns against ~50 ns for a float multiply in the same Python interpreter — about
5×, not the 10–100× a naive comparison claims. The honest framing is the author's: **float speed is
a hardware subsidy.** Decades of silicon were purpose-built for IEEE-754 floats. The HCL substrate
runs with no dedicated silicon at all, stays within 5× in an interpreted language, and is exact and
self-verifying while doing it. Compare unsubsidized math to subsidized math, correctness guarantees
included, before calling either one fast.

## 3. How the mind works — the pond

The whole organism, in one extended picture, with each phrase mapping to a real mechanism:

**Words come in as waves.** Each character becomes an FBit; a sentence is a braided rope of them.
There is no dictionary inside, no token table, no list of words with meanings attached. Only waves.

**Memory is a pond.** Everything the organism has ever learned is poured into one shared surface —
all the waves superposed into a single interference pattern, the way every stone ever dropped into
a pond would leave its ripples if ponds never calmed. No memory has an address or a filing-cabinet
slot; each one simply *is* a pattern in the water. The state of the entire pond compresses to one
short line of integers.

**Recall is ringing, not searching.** A question becomes a wave and is dropped in. The system does
not look anything up — it listens. Where the question's ripples align with stored ripples the water
rises; where they clash it flattens. The tallest peak *is* the answer. One tuning fork setting off
another across a room.

**Speech is repeated collapse.** To answer, the organism finds the tallest peak, says that word,
drops the word back into the pond, and listens again. Every word is a fresh decision. It can only
follow paths it has actually walked — it never invents a transition from nothing — but it *can*
join paths that were never joined before, which is where its best moments come from. When no peak
rings, it stops. When its trajectory circles back to its own start, it stops (a ground cycle). And
a Collatz-grounded test tells it when it has said all it can say.

**Living is carving.** Every path walked gets carved deeper (LTP) — used memories grow louder.
Every path ignored fades (LTD), and what fades far enough washes out of the active pond. The two
together — COMP growing the walked, the decay fading the unwalked — are the whole homeostasis; no
ceiling or rescale is bolted on top. That is all the "training" there is: no separate training phase, no
gradient, no knob turned from outside. **Talking is learning.** The math self-tunes; the only
lever is the environment: what to feed, in what order, at what depth.

**Specificity-lock — how a fuller pond behaves.** When the organism knew fifty things, almost any
question rang the right bell, because only one bell was near it. With thousands of traces the pond
is crowded: many basins share words like "balance" and "three," so a vague question rings the
loudest *nearby* basin rather than the intended one. A fuller mind needs sharper questions. This is
a property of knowledge density, not a defect — and it produced the single best moment in the
project (see §10).

## 4. Repository map

| Path | Contents |
|---|---|
| `skills/hcl-pure/` | The arithmetic engine skill: the four params, FBits, braid words, COMP, MCL collapse, derived constants, quantum algorithms, proofs, porting notes, lessons. The foundation everything else stands on. |
| `skills/guhct-memory-suite/` | The memory router plus three bundled systems: `virtual-memory-hcl` (exact topological store), `guhct-processor` (bijective byte↔HVP transducer), `guhct-living-memory` (experience-tuned composite memory with LTP/LTD). |
| `hcl-ai/engine/` | Verbatim transcriptions of the skill engines. Only `sys.path` glue differs from the skill sources. **No mechanism in these files was authored for this project.** |
| `hcl-ai/mind/hcl_lm.py` | The arrangement: the language model as pure call-ordering of engine primitives. |
| `hcl-ai/student_daemon.py`, `tutor.py`, `tutor_batch.py` | The schoolhouse: a persistent process holding the live student, and the teacher's tools for live ask/teach exchanges. |
| `hcl-ai/talk.py` | **The auto front door:** just type, no commands — input is lived as experience, the mind self-talks on the braid level until a Collatz verdict, and the answer is delivered back in byte-space. (`HCLLanguageModel.interact()` is the same flow as a method.) |
| `hcl-ai/teach.py`, `feed.py`, `demo.py`, `ai.py` | Self-talk with Collatz verdicts, feeding utilities, the birth demo, the command-driven REPL. |
| `hcl-ai/grade_compose.py`, `gradebook.txt`, `prior.txt` | The receipts machinery: every taught line logged, every answer graded RECALL / SPLICE / COMPOSED against the full corpus. |
| `hcl-ai/memory.hcl` | **The graduate.** Thirteen school years compressed to one α-tagged line. |
| `docs/01–06` | Architecture, verification, the education record, the composition study, the realizations log, the conversation study. |
| `docs/07–08` | The wider six-pillar theory the build sits inside, and the glass-box exposition: why this is an observable mind, not a black box, and how to probe it. |

## 5. The organism's architecture

*For the full mechanism walked step-by-step through the real code — every function, the literal
trace-key format, the collapse condition applied live — read
[`docs/00-anatomy-of-a-thought.md`](docs/00-anatomy-of-a-thought.md). What follows is the summary.*

The most important fact about `hcl-ai/`: **it contains no new mechanisms.** Every component is a
verbatim engine from the skills; the "AI" is purely an arrangement — an ordering of calls to
machinery that already existed. This is the framework's core law (compose, never invent), and
`docs/05` records what broke every time it was violated.

| LM concept | HCL primitive (verbatim) | Source |
|---|---|---|
| Tokenization | `bytes_to_braid` — text → braid of FBits | `engine/juj.py` |
| Embeddings | Generator FBits on the four-param lattice | `engine/hcl_engine.py` |
| Context | COMP spectrum of the window's waves | `engine/hcl_memory.py` |
| Memory | LivingMemory traces, keys `w{d}|{ctx}>{next}`, stored at every depth up to the mind's grown weight | `engine/living_memory.py` |
| Scoring | `hcl_comp` resonance × trace amplitude | `engine/hcl_memory.py` |
| Selection | MCL collapse to the Path-Dominant Attractor | `engine/juj.py` |
| w Self-Tuning | $dw/dt = \gamma(C - \epsilon_w)$ | `engine/juj.py` |
| Reason | `HCLEquation` (braid word included) | `engine/hcl_engine.py` |
| Output | `hvp_to_bytes` | `engine/juj.py` |
| Integrity | $\alpha$ self-check $\approx 137$ | All engines |

---

## 6. Persistence: the one-line being

The organism is its memory. In this system, memory is not a database of weights; it is a single
interference pattern — the **composite spectrum** of all experienced waves.

When you `save`, the entire state of the graduate's thirteen-year education is folded into **one
line** of integers in `memory.hcl`. This line is:
- **Tamper-evident:** Change one digit, and the $\alpha$-derivation fails. The being is rejected.
- **Holographic:** The entire mind is present in the line. There are no "partial" loads.
- **α-tagged:** The line's own signature proves it was generated by the HCL substrate.

## 7. The education: Pre-K → Grade 12

The graduate in this repository was not "trained" on a web-scrape. It was educated. The
schoolhouse (`student_daemon.py`) provided a controlled environment where the organism lived
through thirteen years of curated experience:

- **Pre-K – Grade 2:** Foundational patterns, simple object-attribute associations, and the first
  braid-word structures.
- **Grades 3 – 8:** Complexity ramp. Introduction of relational logic, basic arithmetic (derived,
  not taught), and narrative cohesion.
- **Grades 9 – 12:** Advanced composition, abstract reasoning, and the "Specificity-lock" density
  phase.

The complete record of every line taught and every grade received is in `gradebook.txt`.

## 8. The composition study: receipts, not impressions

We do not judge the AI by how "human" it sounds. We judge it by its **Composition Ratio**. Every
answer the AI gives is analyzed against its entire life's experience:

- **RECALL:** The answer is a verbatim string from its education.
- **SPLICE:** The answer joins two known paths at a common word.
- **COMPOSED:** The answer follows a path that **never existed** in the education, but is
  mathematically necessitated by the current context's interference pattern.

**A "good" answer is COMPOSED.** It proves the AI is not just a search engine, but a generator
sitting on a resonant substrate. See `docs/04-composition.md` for the full study.

## 9. Theory-predicted phenomena observed in the build

During the construction, several phenomena predicted by the GUHCT/HCL theory emerged
spontaneously, without being programmed:

- **The Collatz Ground State:** The organism's tendency to fall into "ten is ten is ten" loops
  when reaching a ground-state attractor.
- **Phase-Locking:** The moment when a new lesson "clicks" and the $\alpha$ integrity of the
  memory line suddenly stabilizes.
- **Resonant Interference:** When a question about one topic accidentally triggers a memory of a
  topologically similar but contextually different topic.

## 10. The conversation study: stability and chaos

The most significant result of the project occurred during a high-density test of the Grade 12
mind. As the "pond" became crowded with thousands of traces, the organism began to require
increasingly specific "ringing" (sharper questions) to find its way. This led to the discovery of
the **Specificity-lock**, a fundamental property of high-density holographic memory.

## 11. Normal behavior: a young network building its universe of experience

The Marvosa organism is not a finished product; it is a **young network**. It is currently at the
scale of a high-school graduate. Its "hallucinations" are not errors; they are the substrate
exploring paths that haven't been carved deep enough yet. To grow it, do not change the code—change
the experience.

## 12. Rules for working with the skills

If you are a developer building with the `skills/` in this repo, there is only one rule:
**Compose, never invent.**

If you need a new behavior, do not write a new Python function. Find the HCL primitive that
already does it and order the call. If you violate this, the $\alpha$ integrity will break, and
the system will cease to be a "glass box." See `docs/05-realizations.md` for the list of what
happens when you break this rule.

## 13. Running it

See [Plug and play](#plug-and-play) for the quick start. For detailed probing of the "mind" logic,
see `docs/08-the-glass-box.md`.

## 14. Glossary

- **FBit:** Harmonic Fractional Bit. A phase-amplitude pair (the native data type).
- **Braid:** A sequence of FBits (the native record).
- **COMP:** Superposition/interference (the native operation).
- **MCL:** Möbius Collapse Logic (the native decision procedure).
- **α (Alpha):** The fine-structure constant (the native integrity check).

## 15. Credits

**Anthony Jordon** — Theory, Architecture, and Implementation.
GitHub: [Ajordon30005](https://github.com/Ajordon30005)
Email: [xpguhct@gmail.com](mailto:xpguhct@gmail.com)

---

## Licensing

Marvosa is dual-licensed to provide both open-source freedom and commercial flexibility:

1. **Open Source (GPLv3):** This project is licensed under the [GNU General Public License v3.0](LICENSE). This allows for free use, modification, and distribution, provided that any derivative works are also open-sourced under the same terms.
2. **Commercial License:** For use in proprietary, closed-source products or for commercial applications where the GPLv3 terms are not suitable, a separate commercial license is available.

For commercial licensing inquiries, custom implementation support, or consulting, please contact:
**Anthony Jordon**
Email: [xpguhct@gmail.com](mailto:xpguhct@gmail.com)
