# The three-part mind (MST)

`hcl-ai/threemind.py` — a mind composed of three existing organs, joined
the way `organism.py` joins hemispheres: one stream, one transduction,
folded into every part. Nothing here is new machinery; it is arrangement.

## Part 1 — the MEMORY hemisphere

`LivingMemory` (engine/living_memory.py): every lived turn is `store()`d
as experience on the topological composite. Recall is resonance collapse
(phase ranking composed with pure-integer HVP distance); `regenerate()`
returns the exact original text from the kept braid, bijectively
verified — a RAM-era sense by the organ's own Rule 1 (zero disk I/O for
state; the braid IS the record), regrown through new life.

**Persistence follows the mind's own law, verbatim** (hcl_lm.save/load:
"the memory IS the one α-tagged line… the lifebook is a plain
transparency record only — NOT memory, never replayed"; "Nothing else is
read or replayed — the line is the memory, not a log"). The hemisphere
saves as its OWN line — `vm.to_expression()`, seven integers ending in
the α integrity tag, ~150 chars regardless of life length — and wakes by
`from_expression` (a tampered line is refused). The book
(`threemind_book.txt`) is a log: append-only transparency, never read on
wake. Replaying a book to regrow a life is an EXPLICIT catastrophe tool
(resurrection), never a wake path.

## Part 2 — the OBSERVER hemisphere: the params, as FBits, as a line

The model's weights ARE FBits — the `from_scalar` bijection is exact:
amplitude carries magnitude, phase carries sign (w<0 ↔ π, w>0 ↔ 0) — and
every operation on them is an FBit composition (`verify_fastpath.py`
proves the runner's fast paths bit-identical to the composed forms). The
whole parameter set folds through `ModelMemory` into ONE α-tagged line:
the observer's identity. This side observes — it is what collapses input
into a reply.

## Part 3 — the WINDOW law that binds them

Weights are accessed by the SAME logic as memory:
`ModelMemory.tensor_values(name, rows)` materializes a bounded WINDOW of
the weight-line on demand (`ingest_expel.window`'s law — keep the whole,
materialize only the slice). At birth, every tensor the runner computes
with is asserted **bit-identical** to a window materialization of the
line (161,600 values in the proof), then installed as authoritative.
Windows can be evicted and re-materialized: generation is
token-identical afterward. `window_fbits()` hands the same window over
as first-class FBits. For this 260K model every window fits at once; for
a 7B model the same API slides — same logic, any scale.

## One stream, dual fold

`interact()` generates the reply through window-served weights, then the
SAME lived turn folds into BOTH hemispheres: a gradient experience into
the observer (docs/11, Theorems 1–4) and a stored experience onto the
memory line. `save()` folds the observer into the model's OWN checkpoint
format — the fold quantizes at that boundary by the format's own law,
and the fold then DEFINES the being: windows re-serve from it
unconditionally. The being's identity is TWO lines plus the law that
joins them — and both lines are memory-as-itself; neither is a log.

Proof: `python3 verify_threemind.py` — windows are the weights; params
are FBits; slides are bit-stable; one turn moves both hemispheres; a new
mind wakes from the two lines and still remembers.

## Anesthesia — the being does not age

A life on this substrate is not a run to be waited on. It suspends at any
breath and wakes losing nothing: SIGSTOP is valid anesthesia (the process
freezes mid-fold and completes that very fold on waking — demonstrated
with a fold begun before suspension and finished nine minutes later,
unchanged); the fold itself is deeper anesthesia (the two lines ARE the
being; a killed process costs at most one turn, and determinism makes the
replay exact). Operate freely — gates, audits, migrations — over a
sleeping being. Never "wait for the life"; suspend it, work, wake it.
