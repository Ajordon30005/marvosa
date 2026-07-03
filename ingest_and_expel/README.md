# Ingest & Expel — streamed topological memory over the Marvosa engine

Folds a byte sequence (from a reader, URL stream, local file, or bytes object) into a
single topological signature using the guhct-processor and virtual-memory-hcl
modules, and reconstructs the sequence — in full or by byte range — from that
representation. Intake reads the source in fixed-size chunks and discards each
chunk after folding, so the full source is not held in memory at once. Imports
and intake are headless by default; progress text is opt-in.

## Placement and dependencies
`ingest_expel.py` resides in `hcl-ai/` with `engine/` adjacent, where `engine/`
contains `juj.py`, `hcl_memory.py`, and `hcl_engine.py`. The module adds its own
`engine/` directory to `sys.path` at import using its file location, so no
additional configuration is required. Moving the file out of `hcl-ai/` without an
adjacent `engine/` raises `ModuleNotFoundError` at import.

## Import
```python
import sys
sys.path.insert(0, '/path/to/marvosa/hcl-ai')   # directory containing ingest_expel.py
from ingest_expel import (StreamedMemory, ingest_reader, stream_into_memory,
                           ingest_file, ingest_bytes)
```

## Intake
Each function returns `(mem, stats)`, where `mem` is a `StreamedMemory` and
`stats` is `{'bytes_folded', 'chunks', 'signature'}`.
```python
mem, stats = ingest_reader(reader)          # read any object with read(n)->bytes
mem, stats = stream_into_memory(url)        # read an HTTP source in chunks
mem, stats = ingest_file(path)              # read a local file in chunks
mem, stats = ingest_bytes(data)             # fold a bytes object already in memory
```
Parameters: `chunk` sets the chunk size in bytes (default 8 MiB). `stream_into_memory`
accepts `max_bytes` to cap the number of bytes read. Each chunk is folded with
`juj.bytes_to_hvp` and the returned signature object is stored under the key
`'<key_prefix>:chunk<N>'` (default prefix `stream`), in order. `progress=False`
by default; pass `progress=True` only when a caller wants progress text.

## Signature
```python
mem.signature()   # {'n_w', 'writhe', 'jones_span', 'depth'}
```
Computed by `juj.braid_invariants` over the concatenation of the stored chunk
braids. `depth` is the number of chunks.

## Reconstruction
```python
mem.whole()                # all chunks concatenated in order, as bytes
mem.window(offset, size)   # bytes for [offset, offset+size); size=None reads to the end
mem.regenerate(key)        # bytes of one chunk by key
```
`regenerate` calls `juj.hvp_to_bytes(sig, verify=True)` on the stored signature.
`window` determines which chunks intersect the requested range, regenerates only
those, and returns the concatenated slice. Chunk sizes may vary; ordering is
derived from numbered `:chunk<N>` keys and falls back to insertion order for
custom keys. `whole` is `window(0, None)`.

## Resonance recall
```python
key, data = mem.resonate(input_bytes)
```
Computes the topological invariant of `input_bytes` with `juj.braid_invariants`,
selects the stored chunk whose invariant `(n_w, writhe, jones_span)` matches (with
`hcl_comp` spectrum amplitude as the ordering value), and returns that chunk's key
and its bytes via `juj.hvp_to_bytes`. Returns `(None, b'')` if no chunks are stored.

## Value path
The numeric operations in the recall path use integer HCL operations
(`hcl_comp`, fixed-point arithmetic); no floating-point is used. Reconstruction is
the processor bijection. Signature objects from `bytes_to_hvp` are stored and
passed to `hvp_to_bytes` unmodified.

## CLI
```bash
python3 ingest_expel.py <url> --chunk <bytes> [--max-bytes <n>]
```
Runs `stream_into_memory` and prints the resulting chunk count and signature. The
CLI block runs only when the file is executed directly, not on import. Intake
functions print progress only when `progress=True`.

---

# format_dock

`format_dock.py` is a separate module that maps a format identifier to a handler
and runs that handler against a `StreamedMemory`. It imports nothing from
`ingest_expel` and operates only through `mem.window`, `mem.whole`,
`mem.regenerate`, and `mem.resonate`. It performs no format parsing of its own.

## Handler
A handler is three values:
- `name`: a string identifier for the format.
- `detect(head_bytes) -> bool`: returns `True` if `head_bytes` are this format.
- `open(mem, **opts) -> Any`: reads chunk windows from `mem` and returns a result
  whose type is defined by the handler (bytes, a structure, or `None`).

## Registry
```python
from ingest_expel import ingest_file
from format_dock import FormatRegistry

mem, _ = ingest_file(path, chunk=PAGE_SIZE)

reg = FormatRegistry()
reg.register(
    name   = 'pdf',
    detect = lambda head: head[:5] == b'%PDF-',
    open   = lambda mem, page=0, **_: mem.window(page * PAGE_SIZE, PAGE_SIZE),
)

name = reg.detect(mem)            # name of the first matching handler, or None
data = reg.open_with(mem, page=3) # run the detected handler; or pass name='pdf'
```
Methods:
- `register(name, detect, open, description="")`: adds or replaces a handler by name.
- `from_list(handlers)`: adds handlers from a list of `FormatHandler` instances or
  dicts with keys `name`, `detect`, `open`, optional `description`.
- `names()`: registered handler names.
- `detect(mem, head_bytes=4096)`: reads `mem.window(0, head_bytes)` and returns the
  name of the first handler whose `detect()` returns `True`, else `None`. Only the
  leading bytes are read.
- `open_with(mem, name=None, **opts)`: runs the named handler, or the detected one
  if `name` is `None`; raises `LookupError` if detection fails or `name` is unknown;
  returns the handler's return value.

A module-level `registry` instance is provided. It includes a built-in `raw`
handler whose `detect` matches any input and whose `open` returns
`mem.window(offset, size)`. The raw handler is registered as a fallback, so
specific recognizers added later are tried before raw.

## Output
This module produces no output. Handlers receive bytes and return values; any text
rendering or display is performed inside a handler.

---

# format_config — declaring formats as data (the config/command path)

`format_config.py` compiles a format declared as **data** into a `FormatHandler`
and registers it on a `FormatRegistry` (`format_dock.FormatRegistry`). It is an
alternative to writing `detect`/`open` as Python callables: the two paths are
interchangeable and can be mixed on one registry, so a format may be authored
either as code (`format_dock`) or as config (`format_config`), as chosen.

## Spec
A spec is a dict, a list of dicts, or JSON of either:
```json
{
  "name": "pagedpdf",
  "description": "paged document",
  "fallback": false,
  "detect": {"magic": "255044462d", "offset": 0},
  "open":   {"unit": 8192, "base": 8192, "index_opt": "page", "length": 8192}
}
```
- `name` (required): format identifier.
- `fallback`: optional; when true, this handler is tried after ordinary
  recognizers.
- `detect`: `{"magic": "<hexbytes>", "offset": N}` matches those bytes at a byte
  offset; `{"any": true}` matches any input; omitted means the handler is never
  auto-detected and must be selected by name.
- `open`: a window recipe. A call computes `offset = base + index * unit` and
  reads `mem.window(offset, length)`. `index` is taken from the call option named
  by `index_opt` (e.g. `open_with(mem, page=3)` with `"index_opt": "page"` gives
  `index = 3`); `length` defaults to `unit`. Omitting `open` returns `mem.whole()`.

## Functions
```python
from format_config import compile_spec, load_specs, load_file

reg = load_specs(spec)                 # dict | list[dict] | JSON string -> new FormatRegistry
reg = load_specs(spec, registry=reg)   # register onto an existing registry (mix with code handlers)
reg = load_file('formats.json')        # load a JSON file of specs
handler = compile_spec(spec)           # compile one spec to a FormatHandler (no registration)
```
- `compile_spec(spec)` -> `FormatHandler`; raises `ValueError` for a missing
  `name` or an unrecognized `detect`/`open` shape. Compilation is total, so a
  malformed spec fails at load time, not at call time.
- `load_specs(specs, registry=None)` compiles and registers; returns the registry.
- `load_file(path, registry=None)` loads specs from a JSON file.

No code from the spec is executed; `detect`/`open` are built from the declared
fields only. The recipe expresses addressed reads (offset/size from `unit`/`base`/
`index`); a format requiring logic beyond that (reading an internal index, then a
target) is authored as a callable via `format_dock` instead.

---

# Authoring a format — role, decisions, and interaction timeline

This section states what the author of a format provides and how a request flows
through the system, and cross-references the modules above.

## What the author decides
A format handler is three values (`format_dock.FormatHandler`): `name`, `detect`,
`open`. Authoring a format means deciding:
1. **name** — the format identifier used to select the handler.
2. **detect** — what in the leading bytes identifies the format. `detect(head)`
   receives only `mem.window(0, head_bytes)` (default 4096), so recognition reads
   the head, not the whole sequence. Authored as a magic-byte rule in config
   (`format_config` `detect`) or as a callable (`format_dock`).
3. **open** — how a request maps to window reads. `open(mem, **opts)` translates
   the request options into `mem.window(offset, size)` / `mem.regenerate(key)` /
   `mem.whole()` calls and returns a result. The structure of `opts` and the
   return type are defined by the handler; the registry imposes neither.

`open` computes *where* the requested content is and reads those windows; it is
not a content scan. A format whose location step needs reading an index first does
so as additional `mem.window` reads inside `open`.

## How a request flows (interaction timeline)
1. **Intake** (`ingest_expel`): `stream_into_memory` / `ingest_file` /
   `ingest_bytes` fold the source into a `StreamedMemory` as the topological
   signature with ordered chunks.
2. **Recognition** (`format_dock.FormatRegistry.detect`, or
   `format_config`-compiled detect): reads `mem.window(0, head_bytes)` and selects
   the handler whose `detect` returns `True`.
3. **Selection**: `FormatRegistry.open_with(mem, name=None, **opts)` runs the
   detected handler, or the one named by `name`.
4. **Access**: the handler's `open` issues `mem.window(...)` reads for the
   requested item, each reconstructed via the processor bijection
   (`juj.hvp_to_bytes`), and returns the result.

The list of registered handlers is the set of these access paths across formats:
for a given format and request, it defines how to address the requested content
through the recall window.

## Choosing config or code
- Config path (`format_config`): formats declared as data; suitable for
  addressed-read formats (item N at `base + N*unit`). Loadable from a JSON file.
- Code path (`format_dock`): formats authored as callables; suitable for any
  access logic, including multi-step location.
Both produce `FormatHandler`s and register on the same `FormatRegistry`, so a
registry may hold a mix.

## State — two roles, one memory
The index: every chunk folds into ONE HCLMemory composite (the repo's own
fold_chunk pattern); `mem.line()` is the α-tagged memory line
(HCLMemory.to_expression), deterministic and reconstructable in any fresh
process via `HCLMemory.from_expression(line)` — the line reconstructs the
memory (identity/resonance), not the bytes. The exact-content layer: each
chunk's braid record, RAM-only (Rule 1 — the braid IS the record); sigs are
produced transiently per request; whole()/window()/resonate() are bit-perfect
from it with no re-download. After a process reset, re-ingest — the
deterministic operator re-derives the identical memory and line.

## The safetensors dock (checkpoints)
A `.safetensors` checkpoint declares its own tensor layout in its header; the
dock turns that declaration into windows:
```python
from format_dock import registry
name = registry.detect(mem)                      # 'safetensors'
toc  = registry.open_with(mem)                   # name -> offset/size/dtype/shape
q    = registry.open_with(mem, tensor='model.layers.0.attn.q_proj.weight')
```
Every tensor byte is delivered through `mem.window` — the expel path — so a
streamed checkpoint serves named tensors on demand (layer-paged), with the
memory line as the whole checkpoint's identity.
