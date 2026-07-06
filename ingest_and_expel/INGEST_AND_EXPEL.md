# INGEST & EXPEL — the complete technical account

Package: `ingest_and_expel/` — `ingest_expel.py` over `engine/{juj.py,
hcl_memory.py, hcl_engine.py}`, with `format_dock.py`/`format_config.py` as the
format surface. The engine files are the Marvosa repo's own skill scripts,
verbatim: `juj.py` = guhct-processor/scripts/juj.py, `hcl_memory.py` =
virtual-memory-hcl/scripts/hcl_memory.py, `hcl_engine.py` = the hcl-pure engine
transcribed from hcl-pure/references/03_engine.md. `ingest_expel.py` contains
no mathematics of its own: every operation below is a named repo function, and
the repo file is cited at the point of use. Where a mechanism is stated here
and in the repo, the repo's wording governs.

One tool, two motions, one memory:

- **INGEST** — a byte stream arrives chunk by chunk; each chunk is folded into
  the memory and released.
- **EXPEL** — bytes are produced back out of the memory at delivery
  (whole / window / recall / resonate), exactly.

Throughout this document, blocks marked ⊘ name the standard-architecture
reading that a mechanism superficially resembles, and state why that reading is
wrong here. These are not style notes; every one of them is a conflation that
has actually derailed readers of this system.

⊘ TRAP 0 — "this is a compressor / archiver / codec / database / RAG store."
It is none of these. A codec's object is a smaller encoding of a payload; a
database's object is a container of payloads. This tool's object is a MEMORY:
the stream is experienced (folded) into one composite index, and bytes are
produced back by running the processor — not fetched from a container. Nothing
below is an encoding-for-size, nothing is a stored payload awaiting retrieval,
and the verification of the whole system is bijection and topological
integrity, not a compression ratio.


## 1. The substrate — what every value is

Everything runs on the HCL pure-integer substrate (hcl-pure skill;
`engine/hcl_engine.py`, transcribed verbatim from
`marvosa/skills/hcl-pure/references/03_engine.md`):

    PREC  = 40               # 40 significant decimal digits
    SCALE = 10 ** PREC       # all values: integer X where x = X/SCALE

Every quantity in the value path is an arbitrary-precision integer read as
X/SCALE. There are zero floats, zero imported constants, zero classical math
libraries in the value path. The four parameters (η, λ, γ, β) bootstrap the
engine; the fine-structure self-check α⁻¹ = 137.000000 is derived from them and
is the integrity signal of a correctly running engine at its scale.

The package spans two scale levels, each self-consistent at its own PREC:

- `engine/juj.py` (guhct-processor): PREC = 40. The exact-content transducer.
- `engine/hcl_memory.py` (virtual-memory-hcl): PREC = 30. The composite memory.

Both derive α⁻¹ = 137.000000 at their own scale.

⊘ TRAP — "PREC=30 vs PREC=40 is an inconsistency to normalize away."
It is running structure between scale levels, not a contradiction
(hcl-pure/references/07_lessons.md: values that differ across scale levels are
"running structure, not contradictions"). Each level's arithmetic is closed at
its own SCALE. The one hand-off between levels — a processor-scale spectrum
FBit folded into the memory-scale composite by `hcl_comp` — is the repo's own
committed fold (`marvosa/hcl-ai/stream_ingest.py`, fold_chunk), not an accident
of this package. Do not "fix" it to one scale; doing so changes the memory line
the repo itself produces.

⊘ TRAP — "these files contain Python, so 'no standard coding' is already
violated." The language in these files is HCL Python, not ordinary Python.
Python is the shell and GUHCT is the arithmetic ("Python is the shell. GUHCT
is the arithmetic." — `engine/hcl_engine.py`, header): every statement in the
value path is an HCL operation — integer FBits, COMP, the four params, the
derived α — written in Python syntax the way HCL would be written on any
carrier. The syntax being Python does not make the code standard, any more
than writing HCL on paper would make it English. Standard coding means
substituting foreign LOGIC for the substrate's operations — float trig,
distance metrics, imported constants, external buffers — and none exists
here. `ingest_expel.py` adds zero operations of its own; its only non-HCL
text is the API shell (sequencing calls, carrying arguments), which stands in
for no logic.


## 2. INGEST — the fold, line by line

`StreamedMemory.fold(key, chunk_bytes, keep_record=True)` is the repo's own
fold (`marvosa/hcl-ai/stream_ingest.py`, fold_chunk), composed verbatim, plus
one assignment for the exact-recall record. Per chunk:

### 2.1  bytes → braid word

    braid = juj.bytes_to_braid(chunk_bytes)

`engine/juj.py`: "Forward data term: bytes -> braid word (list of generator
indices). Exactly reversible. No information is discarded; the word is the
data." Each byte value k selects the braid generator σ_k. A generator is a
topological object with its own phase address (`_generator_phase(k)`),
position-dependent amplitude (`_generator_amp`), and FBit
(`_generator_fbit`) — all pure-integer functions in `engine/juj.py`. The braid
word is the sequence of those generators: the chunk expressed in the
substrate's own topological language. The transduction is bijective — an
identity at the sequence level (guhct-processor/references/pipeline.md §6) —
and its inverse is `braid_to_bytes` ("Inverse data term: braid word -> exact
original bytes").

⊘ TRAP — "the braid is just the bytes / a renamed copy of the file."
The byte value is the INDEX that selects a generator; the generator is the
object. The braid word has winding number, writhe, and a Jones-polynomial span
— properties a byte array does not have — and those invariants are what the
memory folds on and what resonance matches on. Saying "the braid is the bytes"
is the electrical-signals-are-the-voice error: the two sides are connected by
an exact transduction, and neither is the other.

### 2.2  the chunk's topology — one invariants pass

    inv = juj.braid_invariants(braid)

One pass computes the chunk's exact topological invariants: `n_w` (winding),
`writhe`, `jones_span`, `spectrum` (the COMP-accumulated FBit of the whole
generator sequence), `stability`. virtual-memory-hcl/references/theory.md:
"The topological invariants are NOT lossy projections. They are exact
structural properties."

⊘ TRAP — "the invariants are a hash / checksum."
A checksum is external bookkeeping attached to data stored elsewhere. The
invariants are the braid's own shape, computed by the substrate's integer
trigonometry and COMP, and they are re-derived from the braid at every single
expulsion (`verify=True`, §4) — the object certifies itself in flight. Nothing
here is bookkeeping about a payload; there is no payload stored elsewhere.

### 2.3  fold into the ONE composite (the index role)

    self.vm._composite = hcl_comp(self.vm._composite, inv['spectrum'])
    self.vm._terms.append(make_braid_term(key, inv['spectrum'], inv))
    self.vm._braid_log.append({... n_w, writhe, jones_span ...})
    self.vm._update_signature()

This is `marvosa/hcl-ai/stream_ingest.py` fold_chunk, verbatim in shape and in
functions (`hcl_comp`, `make_braid_term`, `_update_signature` are all
`engine/hcl_memory.py` — the virtual-memory-hcl skill's own script). The
memory's law (`engine/hcl_memory.py`):

    Ψ_system = COMP(COMP(... COMP(FBit₁, FBit₂) ..., FBitₙ₋₁), FBitₙ)

Every chunk's spectrum is COMP-folded into the one composite. COMP is the
substrate's superposition operator (virtual-memory-hcl/references/encoding.md:
"COMP is quantum superposition"; `engine/hcl_memory.py`, hcl_comp():
"COMP — quantum superposition / addition."). What the index holds is the composite plus one
BraidTerm per chunk — a few integers each ("~200 bytes regardless of content
size", `engine/hcl_memory.py`). The chunk's content is not among them:
"Content itself is NOT stored in this object." (`engine/hcl_memory.py`,
store()).

⊘ TRAP — "the composite is a running hash / Merkle root / digest of the file."
A digest fingerprints data that lives elsewhere. Here nothing lives elsewhere:
the composite IS the memory — a live FBit that recall and resonance operate on
directly, that `to_expression` writes out as the memory line, and that
`from_expression` revives into a functioning memory. It is the state, not a
fingerprint of state.

### 2.4  the exact-recall record (the living role)

    if keep_record:
        self._recs[key] = braid

The braid word — the data-carrying term — is kept as live state in RAM. This is
the guhct-living-memory pattern verbatim
(`marvosa/skills/guhct-memory-suite/bundled/guhct-living-memory/living_memory.py`):

    Rule 1: zero disk I/O for state (RAM-only; the braid IS the record)
    Rule 6: content travels in the braid word (so regeneration is exact)

and its own state line: `self.sigs = {}  # key -> full HVP signature (for
exact recall)`. composition.md (same skill): the address/resonance layer is the
memory skill; the exact-content layer is the processor skill — two skills, two
roles, one memory. §2.3 is the first role; this record is the second.

⊘ TRAP — "`_recs` is a chunk cache / a dictionary holding the file."
In standard architecture a chunk dict is a buffer of payload awaiting use, and
"the memory" would be metadata about it. Here the relation is inverted: the
composite (§2.3) is the memory; the record is the data term already transduced
into the substrate's own language, held as live state because Rule 6 says
content travels in the braid word. Three properties a cache does not have:
(1) it is RAM-only by law (Rule 1) — persisting it to disk is a violation, not
a feature-gap; (2) what expulsion consumes is NOT this record but a signature
PRODUCED from it at delivery (§4) — nothing stored is ever returned as-is;
(3) it is optional: with `keep_record=False` the braid is released after the
fold and the memory (index) stands complete without it.

⊘ TRAP — "a per-chunk braid list means RAM ≈ file size, so the huge-download
purpose fails." Two roles. The index role alone — `keep_records=False` on any
intake function, or the `--index-only` CLI flag — is the repo's own motion
(`marvosa/hcl-ai/stream_ingest.py`: "represent a huge model download as ONE
composite index of experience"; "the file is never held; only the running
composite (a few integers) persists"; peak memory ~ one chunk). That is the
hundreds-of-GB-into-a-small-environment path. The record layer is what you
additionally keep, RAM-permitting, when the session needs byte-exact expulsion
(whole/window/resonate). Enabling one role does not counterfeit the other.

### 2.5  what exists after a fold

Held: the composite index (`self.vm`: one FBit + O(chunks) small terms) and,
if kept, the braid records (`self._recs`). Not held: the chunk's bytes (the
intake releases each chunk — `blk = None`), any HVP signature (never held at
all; see §4), anything on disk (Rule 1).


## 3. The memory line — identity of the whole intake

    mem.line()        →  HCLMemory.to_expression()
    mem.signature()   →  HCLMemory.signature()   # the line's topological head

The line is the virtual-memory-hcl skill's own expression of the composite —
seven α-tagged colon-separated fields:

    phase_frac : amp : n_w : writhe : jones_span : depth : ALPHA_INV

`engine/hcl_memory.py`, to_expression(): "Total length: ~130-250 chars
regardless of number of memories"; "RAM-only. The disk expression encodes the
COMPOSITE state only." It is always the whole state, always overwritten, never
appended.

Three properties, each demonstrated by running the package (§7):

1. **Deterministic.** The fold operator is deterministic, so the same content
   produces the identical line, every time, in any process. The line is a pure
   function of the experienced stream — the download's identity.
2. **Reconstructs the memory.** In any fresh process,
   `HCLMemory.from_expression(line)` rebuilds a functioning memory from the
   line alone: the α tail is checked against the engine's own derived ALPHA_INV
   and a foreign or tampered line is refused (ValueError: expression integrity
   check); the signature is identical; recall/resonance run against the revived
   composite. This is the same mechanism the repo's AI itself lives by —
   `marvosa/hcl-ai/mind/hcl_lm.py`: "The memory IS the one α-tagged line" —
   save() writes only that line; load() revives the being from it.
3. **Addresses; does not carry.** The line is the params side of the system.
   The data term is the braid. guhct-processor/SKILL.txt: "The braid word is
   the data. Never drop it and expect the parameters to rebuild the bytes";
   pipeline.md §6: the parameters "never need to *carry* the data; they
   *address and check* it" — and the earlier version that tried to make the
   parameters alone reconstruct the data is named there as the removed bug.

⊘ TRAP — "the line is the compressed file; feeding it back should replay the
bytes." That expectation is, verbatim, the removed bug (pipeline.md §6). The
line reconstructs THE MEMORY — identity, resonance, verification — not the
payload. `from_expression` restores the composite only ("Individual BraidTerms
are not stored in the expression", `engine/hcl_memory.py`); there is no braid
in the line, and no function anywhere in the repo produces a braid from
invariants — that inverse is the open search problem
(hcl-pure/references/05_proofs.md), not an unshipped feature.

⊘ TRAP — the opposite conflation: "then the line is just metadata."
Metadata describes data stored elsewhere. There is no elsewhere: the line is
the persistent form of the memory itself — the same one line that revives the
repo's AI — α-verified, deterministic, and sufficient to reconstruct a memory
that resonates. A ~150-character identity that a fresh process can wake into a
functioning memory is not a label on a payload; it is the payload's experience,
folded.


## 4. EXPEL — producing bytes at delivery

    def recall(self, key):
        sig = juj.bytes_to_hvp(juj.braid_to_bytes(self._recs[key]))
        return juj.hvp_to_bytes(sig, verify=True)

The signature is PRODUCED at the moment of delivery — a local, transient
object — and released when the call returns. `engine/juj.py`, bytes_to_hvp():
"The params alone are the address; the braid carries the data. Both together
[are the complete, bijective representation]." hvp_to_bytes(): "Consumes ONLY
the signature (params + braid). Rebuilds the exact bytes from [the braid
word]" — and with `verify=True` it re-derives the parameters from the braid
(forensic_reconstruct_boundary) and asserts they address it, on every single
expulsion. A signature whose parts do not belong together is refused with a
mismatch error, not returned.

This is the shape of the repo's AI emitting output —
`marvosa/hcl-ai/mind/hcl_lm.py`, speak(): make the signature, "expand it back
losslessly — the verified bijective round trip" — and, on the thinking side,
the AI's generation walks braid space with no per-step transduction ("signals
(no byte↔braid transform per step)"): the bijection runs once, at delivery.
Expulsion here obeys the same law: RAM is populated only during the request,
finite per request, and nothing survives it.

⊘ TRAP — "recall is a dictionary lookup returning a stored value."
A lookup returns the stored thing. Here nothing stored is returned: the record
is run THROUGH the processor; the signature exists only inside the call; the
address is re-derived and checked against the data term every time; and the
bytes are the transduction's output. Hand the path a signature whose params
and braid disagree and it raises — a lookup has no notion of refusing.

⊘ TRAP — "`verify=True` is a unit test / checksum comparison."
It is the processor certifying its own inverse per call — the same self-check
`engine/juj.py`'s own `__main__` runs (its six-case family, "ALL BIT-PERFECT").
It is part of the operation, not scaffolding around it.

### 4.1  whole() and window(offset, size)

The whole sequence is addressable; only the requested slice is materialized.
`window` walks a byte cursor across the ordered records (a record's braid
length equals its chunk's byte count — the transduction is one generator per
byte), expels only the chunks the window touches, and joins the exact slice.
`whole()` is `window(0, None)`. Bounds are honored (`offset ≥ total` or
`size == 0` → empty; negatives raise). This is the access pattern of
HolographicLog in the repo author's star.py: keep the whole abstract sequence,
materialize only `[view_offset : view_offset + render_size]`.

⊘ TRAP — "chunk boundaries are a framing/file format."
Chunking is transit granularity only. Addressing is continuous across chunk
boundaries: a window may start mid-chunk, span several, and end mid-chunk; the
cursor walks real per-record lengths. The memory line is of the WHOLE intake;
order is carried by the keys/terms, not by any framing bytes (none exist).

### 4.2  resonate(input_bytes)

    qi = juj.braid_invariants(juj.bytes_to_braid(input_bytes))
    # exact topology (n_w, writhe, jones_span) is the dominant attractor;
    # juj.comp(q_spectrum, m_spectrum).amp ranks resonance;
    # collapse selects; the selected memory is expelled.

The query is transduced, its topology computed, and each candidate's topology
is produced from its record at match time. An exact topological identity —
the full (n_w, writhe, jones_span) tuple — dominates the ranking; the COMP
amplitude of the two spectra is the resonance value. The selection is the MCL
collapse of the substrate: "Collapse is NOT random. It is topologically
deterministic. The system collapses to the Path-Dominant Attractor"
(hcl-pure/references/01_theory.md) — the same recall law as
`recall_from_store` (`engine/hcl_memory.py`) and `_collapse`
(`marvosa/hcl-ai/mind/hcl_lm.py`).

⊘ TRAP — "resonance is embedding similarity / nearest-neighbor search."
There are no vectors, no distance metric, no cosine, no floats. The dominant
criterion is exact structural identity — a closed topological match, not
proximity in a space — and the resonance value is the substrate's own COMP
amplitude in integers. Two byte sequences do not "score similar"; their braids
either share a topology or they interfere to a given amplitude.


## 5. The intake surface (the API shell)

    ingest_reader(reader, ...)        # any object with read(n) -> bytes
    stream_into_memory(url, ...)      # streaming download (boundary I/O only)
    ingest_file(path, ...)            # local file, chunk-by-chunk
    ingest_bytes(data, ...)           # bytes already in memory

All delegate to one loop: pull a chunk, `mem.fold(key, blk)`, release the
chunk (`blk = None`), repeat. Peak transit is one chunk regardless of source
size. Every function threads `keep_records=` (default True) to `fold`'s
`keep_record=` — set False for the index-only motion (§2.4). The CLI
(`python3 ingest_expel.py URL [--index-only]`) is the same loop with printing.

`format_dock.py` is an optional registry — `name / detect(head) /
open(mem, **opts) → windows` with a built-in `'raw'` fallback — and
`format_config.py` declares formats as data (magic/offset detection; a
unit/base/index/length window recipe) compiled onto the same registry. Both
are pure API over `window()`: they choose WHERE to window; they compute
nothing.

⊘ TRAP — "the API layer is where the logic is."
The shell stands in for no logic (the build rule of this package): every
transformation of a value is a named skill function; the shell only sequences
calls and carries arguments. If a behavior cannot be pointed at a repo
function, it does not exist in this package.


## 6. What survives what

Within a live process: everything. Expulsion is bit-perfect with zero network
and zero disk — the memory produced by one ingestion is the complete source
for every whole/window/recall/resonate that follows.

Across a process reset: the exact-recall records clear — by law, not by
accident (Rule 1: state is RAM-only; the braid IS the record). The line
survives wherever the caller put it (it is ~150 characters; the repo's AI
keeps its own as `memory.hcl`). From the line, a fresh process reconstructs
the memory — identity, resonance, α-verified — with no download. To replay
bytes after a reset, re-ingest the source: the operator is deterministic and
scale-invariant, so re-folding re-derives the identical memory and the
identical line. Re-derivation, not re-invention.

⊘ TRAP — "no content save/load = an unfinished design."
The absence is the architecture. The living-memory skill states Rule 1 as law;
the repo's own ingest ends its run announcing the file was never fully stored;
the repo's AI persists as one line and nothing else. A JSON of braids on disk
is not a missing feature that was left out — it is a violation that was taken
out.


## 7. Verification — the substrate's own, in this package

Every check below is the repo's own mechanism; none is an external harness.

- **Per-expulsion:** `verify=True` inside every delivery — parameters
  re-derived from the braid and asserted to address it.
- **Engine integrity:** α⁻¹ = 137.000000 at each scale level with its own
  constants (juj at 10⁴⁰; hcl_memory at 10³⁰), never mixed.
- **The processor's own case family** (`engine/juj.py` `__main__`: empty /
  1 byte / 13 bytes / all-256 / 4096 entropy / 13500 structured) run through
  this tool's fold→whole: all exact.
- **Operator scale-invariance** (the proof method of
  hcl-pure/references/05_proofs.md: the operator's logic does not change with
  n, so finite verification covers all potential inputs): boundary sizes
  0, 1, 2, 255/256/257, 1023/1024/1025, 8191/8192/8193, 100000 — single-chunk
  and chunked — all exact.
- **The line:** deterministic (same content → identical line, independent
  runs); `from_expression(line)` in a fresh process → memory reconstructed,
  α-verified, signature identical, line round-trips byte-identical; a tampered
  line is refused.
- **Cross-implementation identity:** the same content folded by this package
  and by the repo's own `marvosa/hcl-ai/stream_ingest.py` produces the
  IDENTICAL memory line — the fold is the repo's fold.
- **Refusals:** a signature assembled from mismatched parts is refused by
  `hvp_to_bytes(verify=True)`; a line with a foreign α tail is refused by
  `from_expression`.

⊘ TRAP — "where are the real (external) tests?"
External probing misleads on this system — escape-hatch asserts, timing loops,
and N×N discrimination probes measure the harness, not the substrate, and have
done so. The verification above is the system exercising its own integrity
checks, the way `juj.py`'s own `__main__` does.


## 8. File map — mechanism → source

| Package file        | Role                                   | Repo source (verbatim origin)                                            |
|---------------------|----------------------------------------|--------------------------------------------------------------------------|
| `ingest_expel.py`   | the two motions; API shell only        | fold = `marvosa/hcl-ai/stream_ingest.py` (fold_chunk); expel = the speak() shape, `marvosa/hcl-ai/mind/hcl_lm.py`; record = living_memory.py Rule 1/6 |
| `engine/juj.py`     | bytes↔braid↔HVP transducer, invariants, COMP (PREC 40) | `marvosa/skills/guhct-memory-suite/bundled/guhct-processor/scripts/juj.py` |
| `engine/hcl_memory.py` | ONE-composite memory, hcl_comp, braid terms, the line (PREC 30) | `marvosa/skills/guhct-memory-suite/bundled/virtual-memory-hcl/scripts/hcl_memory.py` |
| `engine/hcl_engine.py` | the pure arithmetic substrate        | transcribed from `marvosa/skills/hcl-pure/references/03_engine.md`        |
| `format_dock.py` / `format_config.py` | format→window registry (API only) | this package; every operation defers to `window()`            |
| `RECONSTRUCTION.md` | the line vs. bytes, stated for a fresh reader | grounded in pipeline.md §5–6, SKILL.txt Rule 3                   |
| `SETUP.md` / `README.md` | install & use                     | —                                                                        |

Method surface of `StreamedMemory`: `fold` (ingest) · `whole` `window`
`recall` `regenerate` `resonate` (expel) · `line` `signature` (identity).

Read order for a new reader: `SETUP.md` → this file → `RECONSTRUCTION.md` →
the repo skills it cites (each SKILL.txt in
`marvosa/skills/guhct-memory-suite/bundled/`, then
`marvosa/skills/hcl-pure/`). The repo is the account; this document is its
map.
