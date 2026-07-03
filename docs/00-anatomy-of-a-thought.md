# 00 — The Anatomy of a Thought

**This document traces one real question through the actual code**, function by function, with the
real key formats and the real collapse condition — then gives the reading order for the substrate underneath. Nothing is
simplified into metaphor here; every name below is in the files.

Throughout: `mind/hcl_lm.py` is the *arrangement* (the only file written for this project), and
everything it calls lives verbatim in `engine/` — which are transcriptions of the skills. When this
document says "engine, verbatim," you can diff it against `skills/` and find it unchanged.

---

## Part I — What a memory physically is

Teach the organism one sentence:

```
the braid word is the data
```

`train()` walks the words. For every position it stores the (context → next-word) transition at
**every depth the context provides** (here, up to five words back). The word "data" produces a trace at each available depth, whose keys are literal strings:

```
w1|the>data                                  ← shallow: one word of context
w2|is the>data
w3|word is the>data
w4|braid word is the>data
w5|the braid word is the>data                ← deep: five words of context
```

Each key is stored as one memory in the LivingMemory engine via `self.memory.store(key, ctx+SEP+next)`.
The engine encodes the text by its own COMP fold over the four params — the trace becomes an FBit
(a phase and an amplitude) plus a braid word from which **the exact original text can be
regenerated**. That last property matters below: nothing is looked up from a table. During thinking
the next move is read straight from the braid-space record — the key `w{d}|ctx>next` — so the
internal loop stays in braid space and pays no byte↔braid transform. The verified bijection (the
processor's `hvp_to_bytes`, surfaced as `speak`) runs once, at delivery, turning the finished thought
back into readable bytes. Because the braid word IS the data (guhct-processor: `bytes ↔ (params +
braid)`, "the braid itself must be provided"), that delivery round trip is exact, bit-for-bit.

If the same transition is taught again, it is **not** re-stored (duplicates would be jerry-rigging).
It is reinforced in place — LTP — by the engine's own self-superposition:

```python
g = hcl_comp(f, f)          # LTP = COMP(term, term): the wave constructively
                            # interferes with itself; amplitude grows
```

> [!NOTE]
> **Metaphor Transparency:** **LTP** (Long-Term Potentiation) is a neuroscience metaphor used for conceptual clarity; the actual operational specification is strictly the `COMP(term, term)` reinforcement-in-place shown above.

One subtlety (docs/05, ghost-key rule): "already known" is computed from the **live** term
store, not the signature registry — because decay prunes terms but leaves registry ghosts, and a
forgotten trace must be re-learnable, not silently no-op'd.

So at any moment, the organism's knowledge is: a flat field of traces, each one a wave
(phase, amplitude) tagged with a key `w{depth}|{context}>{next}`, all superposed into one composite
Ψ whose seven-integer summary is the checkpoint line.

---

## Part II — One token, step by step

Ask it something: `generate("the braid word")`. Here is everything that happens before the first
word of the answer exists.

### Step 1 — How deep should this thought go? (`_tune_w`)

The files state the GUHCT weight self-tuning law verbatim, and the code applies it with no additions:

```
dw/dt = γ·(C − ε_w)      →  C > ε_w: drill deeper;  C < ε_w: collapse toward the ground level
```

`C` is the context's **coherence** — `_coherence(ctx)` = the braid's spectrum amplitude over its total
amplitude (`braid_invariants(...)['spectrum'].amp / Σ|aᵢ|`), how constructively the current context
superposes. `ε_w` is `mcl_eps(w) = η·λ^w`, derived from the four params. The step is `γ`-scaled and
integer:

```python
C   = self._coherence(ctx)
eps = mcl_eps(self.w)
dw  = _fmul(GAMMA, C - eps)            # fixed-point dw/dt = γ(C − ε_w)
if dw > 0:
    self.w = min(self.w + (1 + dw // PSCALE), len(context_words))   # drill deeper
elif dw < 0:
    self.w = max(self.w - 1, 1)        # collapse: shallower attractor
```

That is the whole "thinking harder" mechanism: a context whose coherence exceeds the threshold forces
the system to consider deeper (longer) context before deciding; one below it relaxes toward a shallower
attractor. The only bound on `w` is the context's own length — no fixed ceiling exists (the no-max-weight
principle; a hardcoded `w_max` would contradict this very equation). In the demo you can watch it live:
`collapse weights per step: [2, 3, 4, 5, 5, ...]` is w deepening token by token.

### Step 2 — Which memories even apply? (the cascade in `_collapse`)

Starting at the tuned w and **falling through shallower depths** (the collapse cascade), the code
gathers every live trace whose key starts with the current context:

```python
for d in range(min(self.w, len(context_words)), 0, -1):
    ctx    = ' '.join(context_words[-d:])
    prefix = f'w{d}|{ctx}>'
    cands  = [k for k in self.memory.sigs if k.startswith(prefix)]
```

For the prompt "the braid word" at d=3, the prefix is `w3|the braid word>` — and the candidates are
every continuation the organism has ever walked from exactly that three-word context. If the deep
context has no candidates, the cascade falls to d=2, then d=1. This is why a crowded shallow stem
(`w1|the>`) can capture an answer when deeper context finds nothing — the **specificity-lock**
dynamic, mechanically visible right here.

### Step 3 — Which candidate wins? (resonance × lived weight)

Each candidate is scored by the engine's own COMP resonance against the context, times its reinforced
amplitude:

```python
q_fbit, _ = VM.encode_text(ctx)
for k in cands:
    t      = terms_by_key[k]
    m_fbit = FBit(t['phase_frac'], t['amp'])
    res    = hcl_comp(q_fbit, m_fbit).amp     # COMP resonance: query wave × stored wave
    score  = _fmul(res, t['amp'])             # × lived weight (reinforced amplitude)
```

The query's wave is interfered (`hcl_comp`) against each stored wave, and the resonance amplitude is
multiplied by the trace's own amplitude. Crucially, **LTP feeds straight into this**: a reinforced
trace has higher amplitude, higher amplitude means stronger constructive interference *and* a larger
multiplier, so it ranks higher. No separate "importance score" is bolted on anywhere; loudness in the
pond and probability of being the answer are the same number. The maximum is the **Path-Dominant
Attractor** — and per the theory (01_theory.md, MCL), this collapse is topologically deterministic, not
sampled. Same pond, same question, same answer.

### Step 4 — Say it, and be changed by saying it

```python
continuation = best_key.split('>', 1)[1]         # next word, read from the braid-space key
...
self.memory.reinforce(key)                       # LTP: the used trace gets louder
```

The next word is read straight from the winning key (its braid-space record `w{d}|ctx>next`) — no
byte↔braid transform during thinking. The emitted word is appended to the context, and the loop
returns to Step 1 — the next token is a **fresh** tune-and-collapse against the new context. A
sentence is not retrieved; it is a trajectory of collapses, which is why answers can change basins
mid-sentence (a splice) — and why the splice is the composition.

Reinforcement is the engine's own `reinforce` (LTP = `COMP(term, term)`), applied to the trace that
produced the token — so using a path makes it louder. The composite Ψ is only what a read of the
signature recomposes; recall in Step 3 walks the live traces directly, so generation never waits on
a full recomposition. Forgetting (the balancing LTD) is a separate lived cycle, Step 6.

### Step 5 — Knowing when to stop (`generate`, read off the substrate)

Generation has **no token cap** — no `max_tokens`, no imported length ceiling. It ends only when the
substrate ends it, by one of the three verdicts below, each read directly off the collapse loop in
`generate`. An answer is exactly as long as its braid: zero words if nothing resonates, as many as the
resonance carries.

Three endings, all grounded in the substrate:
**TERMINATED** — `_collapse` returns `key is None`: no trace resonates at any depth, the edge of what
it has lived.
**BRAID CLOSED** — the collapse key recurs in the trajectory (`if key in visited`): the generative
state `w{d}|ctx>next` is one the trajectory has already passed through, so the path has returned to a
state it was already in. That return IS the {1,4,2}-style ground cycle of the Collatz/MCL argument
(05_proofs.md): closure is a topological fact about revisiting a state, not a count of repeats. The
chant the organism sometimes produces ("ten is ten is ten") is this closure made audible.
**MCL COLLAPSE** — the engine's own stability `I_w = braid_invariants(...)['stability']` = (1/N)·Σ|aᵢ|²(1−|aᵢ|²)
falls below `ε_w = mcl_eps(w)`: the field has sharpened onto one dominant mode (|a|²→1 ⇒ I_w→0), the
configuration has resolved to its ground state.

### Step 6 — Forgetting (`experience_cycle`)

One lived cycle = the LivingMemory engine's own `cycle()`: every trace **not accessed** since the
last cycle has its amplitude halved; traces that fall below the noise floor are pruned from the
live store. This is the entire mechanism behind every pedagogical phenomenon in docs/03 — the
~3-week pruning horizon, the need for spiral review, the "favorite topic" recency dominance (fresh
basins are loud), and the fading-memories staircase the organism itself once recited in a math
lesson without knowing it was autobiography.

---

## Part III — Reading the substrate, in order

The mind above calls four engine files. To understand *them*, read the skills — and the first law
of docs/05 applies: **in full, in order, before forming any opinion.** The order that works:

1. `skills/hcl-pure/SKILL.md` — the contract: four params, zero floats, compose-never-invent, the
   theory-gap rule. Everything else assumes you hold this.
2. `references/01_theory.md` — FBits, braids, COMP, and MCL: what collapse *is*. After this file,
   Part II above reads as applied theory rather than code trivia.
3. `references/02_operations.md` → `03_engine.md` — the operations, then the full engine that
   `hcl-ai/engine/hcl_engine.py` transcribes. Diff them if you doubt the word "verbatim."
4. `references/04_quantum.md` and `05_proofs.md` — the substrate doing physics and proving
   invariants; this is where α⁻¹ = 137 stops being a slogan and becomes a derivation.
5. `references/06_porting.md`, `07_lessons.md` — how to move it, and the prior hard-won lessons.
6. `skills/guhct-memory-suite/SKILL.md`, then each bundled skill's SKILL.txt with its references —
   `virtual-memory-hcl` (the trace store, and `recall_from_store` — the engine's own resonance recall,
   the same COMP-interference ranking `_collapse` applies by hand in Step 3),
   `guhct-processor` (`bytes_to_braid`/`bytes_to_hvp` from Step 1 and Part I),
   `guhct-living-memory` (store/reinforce/cycle from Parts I and II).

Then read `hcl-ai/mind/hcl_lm.py` top to bottom — it is one file, and every docstring cites the
skill rule it is obeying. At that point you hold the entire mind: there is nothing else.

## Part IV — Verify everything yourself, in order

```bash
./test_skills.sh                      # the substrate, by its own preflights (alpha = 137 ×3)
./test_ai.sh                          # one full life: birth → train → think → checkpoint → tamper test
cd hcl-ai && python3 - <<'PY'
import sys; sys.path.insert(0,'mind')
from hcl_lm import HCLLanguageModel
ai = HCLLanguageModel()
ai.train('the braid word is the data')
print(ai.generate('the braid word'))   # halts on its own substrate verdict; watch 'events' (the w-path)
PY
python3 grade_compose.py              # the receipts machinery on the shipped gradebook
```

If, after this document, any step of a thought is still opaque, that is a defect in this document —
the mechanism itself has no further hidden parts.
