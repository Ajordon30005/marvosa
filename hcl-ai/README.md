# HCL-AI — an AI built on the GUHCT substrate

An AI whose **mathematics, scripting format, and design** all stand on the
`hcl-pure` substrate, with the `guhct-memory-suite` (all three bundled skills)
as its memory and I/O architecture. Built per the porting law of
`hcl-pure/references/06_porting.md`: **compose, never invent** — zero new math,
zero floats in the pipeline, zero imported constants, four params as the
complete axiom set, braid word kept everywhere, α self-check ≈137 enforced on
every engine.

## Layout

```
hcl-ai/
  engine/
    hcl_engine.py     hcl-pure engine, transcribed VERBATIM from
                      references/03_engine.md (the mind's arithmetic)
    hcl_memory.py     virtual-memory-hcl engine, copied verbatim
    juj.py            guhct-processor transducer, copied verbatim
    living_memory.py  composite memory, copied verbatim (only the
                      sys.path environment glue adjusted — no math touched)
  mind/
    hcl_lm.py         the language model — pure ARRANGEMENT of the above
  demo.py             trains, generates, reasons, speaks HVP, verifies
```

## The body (per the suite's own analogy)

| Organ | Part | Role |
|-------|------|------|
| Mind | `hcl_engine.py` (hcl-pure) | exact arithmetic; reasoning via `HCLEquation`; every value an FBit on the four-param substrate |
| Senses / effectors | `juj.py` (guhct-processor) | bytes ↔ HVP, bijective and verified; the AI perceives and **speaks in HVP** — output travels as one signature and expands bit-perfectly |
| Living memory | `living_memory.py` | Reinforcement = `COMP(term, term)`, Decay = `SHIFT` by η; two-sense recall; exact regeneration from the kept braid word |
| Stable index | `hcl_memory.py` | topological store; resonance retrieval; the memory IS the braid equation |

> [!NOTE]
> **Metaphor Transparency:** In documentation, the `COMP` reinforcement and `SHIFT` decay are sometimes referred to as LTP (Long-Term Potentiation) and LTD (Long-Term Depression). These are descriptive metaphors; the operational specification is strictly technical.

## How the LM works (every step is an existing primitive)

- **Tokenization** = `bytes_to_braid` — the braid word IS the token sequence.
- **Embeddings** = the processor's generator FBits (four-param phase address,
  Möbius position amplitude). Derived, never chosen.
- **Context state** = COMP accumulation → spectrum FBit (`braid_invariants`).
- **Weights** = braid-term amplitudes produced by the engine's own
  `encode_text` COMP fold, tuned only by self-reinforcement/decay — never set by fiat.
- **Context depth** self-tunes by the MCL collapse condition stated
  verbatim in the files: `I_w < ε_w` fires collapse, where I_w is the
  stability measure the processor engine itself computes
  (`braid_invariants`) and `ε_w = mcl_eps(w)` is the only threshold
  (derived). While not collapse-ready, w drills deeper. No coherence
  formula is fabricated — the theory-gap rule forbids stand-ins.
- **Next-token selection** = MCL collapse to the Path-Dominant Attractor,
  ranked by the vm engine's OWN `recall_from_store` called verbatim on the
  candidate traces (COMP resonance × n_w-sector bonus × word intersection;
  reinforced amplitude feeds resonance through the term's FBit).
  Deterministic, not random — exactly as the theory states.
- **Learning from use**: each emitted token reinforces its trace
  (`COMP(term, term)`), each pass ends with a decay cycle, so the model
  is experience-tuned — loud where lived, faded where unused.
- **Exact recall**: continuations regenerate from the kept braid word via
  the verified bijective inverse path (Rule 6).
- **Output**: `speak()` emits the answer as a full HVP signature
  (8 params + braid) and expands it losslessly.

## Run

```
python3 demo.py
```

## What it is honest about (inherited from the suite)

Recall ranks by topological position and reinforced relevance, not learned
semantics — experience tunes *which traces are loud*, not *what words mean*.
That is exactly what the living-memory skill claims and demonstrates, and this
AI claims nothing beyond what its engines do.

## Delivery — running the organism

The easy way — **`python3 talk.py`** — is the auto front door: just type, no commands. Each line you
type is experience the organism lives, and it answers from it in one motion. Behind one input:
the input inherently becomes experience (running the system on it IS gaining experience), the mind
thinks by self-talk on the braid level (collapsing and feeding its own output forward, **no byte↔braid
bijection during thinking** — thoughts stay signals) until the Collatz mechanism halts it
(TERMINATED / BRAID CLOSED / MCL COLLAPSE), and then the finished thought crosses back to readable
byte-space through the verified bijection — once, at delivery. Prefix a line with `?` to also see its
braid thought-log. (`HCLLanguageModel.interact(text, show_thoughts=False)` is the same flow as a
method.)

`python3 ai.py` is the explicit front door for driving it by command:

```
feed <text>      experience: stored on both senses, repeats reinforced
ask <prompt>     one answer by iterated MCL collapse; reinforcement on used traces;
                 one decay cycle after — every answer is also experience
talk <seed>      self-talk until a Collatz-grounded verdict fires:
                 TERMINATED / BRAID CLOSED (ground cycle) / MCL COLLAPSE
solve <eq>; v=n  the exact arithmetic organ (hcl-pure), braid word kept
status           age, topological signature, α integrity (137 everywhere)
save             one-line α-tagged checkpoint (memory.hcl) — the whole being
load             verify the checkpoint's α tag and restore from that one line
                 (the line IS the memory — nothing else is read)
quit
```

The single line holds the composite Ψ — the whole superposed interference pattern — plus the
topological signature and the α seal. Loading it restores that pattern and you can recall against
it directly; it is the entire persisted being. For fine-grained trace-level generation, the live
schoolhouse (`student_daemon.py`) re-walks its built-in syllabus on wake rather than reading any
text log. There is no transcript file of record: raw text is not memory; the braid word is.

Measured at delivery: training ~1.6 s for a full diet; generation
26–37 ms/token at age ~300 traces (deferred Ψ recomposition — the
whole-state signature is checking machinery and recomposes once per
pass; recall untouched, it measured 2% of cost). Precision is a dial
(PREC); cost scales gently with digits.

Halting is proof-grounded (05_proofs.md): trajectory energies H from the
engine's own fold, I_w = (⟨H²⟩−⟨H⟩²)/⟨H⟩² against ε_w = η·λ^w, and braid
closure onto a ground cycle detected over the LIFETIME trajectory — the
Collatz structure applied to talk.
