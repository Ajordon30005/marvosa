# Reconstruction in this package — read this, it answers "how do I get the bytes back"

Everything below is verifiable in the files in THIS folder (engine/juj.py,
engine/hcl_memory.py, ingest_expel.py). You do not need any other repo. Do not
reason from prior knowledge of how compressors/codecs "usually" work — this is a
bijective transducer, not a dictionary or a model. Read juj.py and confirm.

## The one fact that resolves the common mix-up
There is NO dictionary and NO "expand a short line into the data" step. Asking
"which function turns the memory line into the braid?" has no answer because the
premise is wrong. Here is what the code actually does.

## The signature has two parts (engine/juj.py, bytes_to_hvp)
    bytes_to_hvp(raw) -> { 'params': {...}, 'braid': [...], 'n_bytes': N }
- params  : the holographic ADDRESS (a handful of derived integers). Fixed size.
- braid   : the DATA-CARRYING term. bytes_to_braid(raw) == list(raw), i.e. the
            braid IS the byte values as generator indices. It scales with data.
The docstring states it plainly: "The params alone are the address; the braid
carries the data. Both together are the complete, bijective representation."

## Bytes come back FROM THE BRAID (engine/juj.py, hvp_to_bytes)
    hvp_to_bytes(signature, verify=True):
        data = braid_to_bytes(signature['braid'])   # <-- bytes rebuilt from the braid
        if verify: re-derive params from the braid and assert they match
        return data[:signature['n_bytes']]
braid_to_bytes is bytes(bytearray(braid)) — the exact inverse of bytes_to_braid.
The params are used ONLY to verify the braid; they are not turned back into data.
So hvp_to_bytes REQUIRES the braid. A signature without its braid cannot rebuild
the bytes — by design, not by omission.

## The "memory line" is the ADDRESS ONLY (engine/hcl_memory.py)
HCLMemory.to_expression() emits the 7-field colon line:
    phase_frac:amp:n_w:writhe:jones_span:depth:ALPHA_INV
That line is the COMPOSITE address (params side). It contains NO braid.
from_expression(line) restores that composite address into an HCLMemory object;
HCLMemory has no whole()/regenerate and no braid, so it cannot and is not meant
to emit original file bytes. The line is for resonance/addressing, not byte
recovery. (If you give the line to hvp_to_bytes it will fail: there is no
'braid' key. That is expected — the line is not a full signature.)

## How you ACTUALLY reconstruct bytes in this package
You need the FULL signature (params + braid). Two equivalent ways, both in
ingest_expel.py / juj.py:

Direct (engine/juj.py):
    import juj
    sig  = juj.bytes_to_hvp(data)             # bytes -> full signature (params + braid)
    out  = juj.hvp_to_bytes(sig, verify=True) # full signature -> exact bytes
    assert out == data

Streamed (ingest_expel.py): fold keeps each chunk's braid record (the
data-carrying term — the braid IS the record) and folds its spectrum into the
composite Ψ; whole()/window()/regenerate() produce each chunk's sig transiently
and expand it via hvp_to_bytes(verify=True), and resonate() matches by
topological invariant then returns exact bytes:
    from ingest_expel import ingest_file
    mem, stats = ingest_file('enwik8')        # each chunk folded: braid record + composite fold
    data = mem.whole()                        # exact bytes: sig produced per chunk, verified inverse
    part = mem.window(offset, size)           # any exact byte range
    key, back = mem.resonate(query_bytes)     # topological match -> exact bytes
Reconstruction produces the sig by processing at delivery (bytes_to_hvp over the
braid record) and expands it through the verified inverse (hvp_to_bytes,
verify=True) — the AI's speak() shape. No signature object is held between
requests; nothing reads the colon line for bytes. That is correct, not a
missing feature.

## State model — two roles, one memory (composition.md)
INDEX / ADDRESS ROLE: every chunk is folded into ONE HCLMemory composite
exactly as the repo's own hcl-ai/stream_ingest.py fold_chunk does. The memory
line is the skill's own α-tagged expression — `mem.line()` (=
HCLMemory.to_expression, ~160 chars regardless of size, deterministic: same
content -> same line). In ANY fresh process, `HCLMemory.from_expression(line)`
RECONSTRUCTS the memory from the line — α-verified (foreign/tampered lines are
refused), signature identical, resonance functional — with no download. The
line reconstructs THE MEMORY (identity/resonance/verification). It does not
replay the bytes: the repo's own ingest discards them by design ("the file
itself was never held"), and the processor's rule is that the braid — not the
parameters — carries the data.

EXACT-CONTENT ROLE: each chunk's braid record lives in RAM only (Rule 1: zero
disk I/O for state — the braid IS the record). Sigs are produced transiently
per request (bytes_to_hvp) and expanded by the verified inverse
(hvp_to_bytes, verify=True) — whole()/window()/recall()/resonate() are
bit-perfect from this layer, with no re-download.

A process reset clears the exact-recall layer by design (RAM-only). The line
survives as the download's identity; to replay bytes after a reset, re-ingest
the source — the operator is deterministic and scale-invariant, so re-folding
re-derives the identical memory (identical line) rather than inventing one.

## Rules for using this package correctly
- Read engine/juj.py before concluding anything about reconstruction.
- Use the functions exactly as written; pass the whole signature object to
  hvp_to_bytes — never hand-build or strip it.
- Do not expect the colon line alone to rebuild bytes (it is address-only).
- Test by running ingest -> whole -> assert byte equality, not by assuming.
