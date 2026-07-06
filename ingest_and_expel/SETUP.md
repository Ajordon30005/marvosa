# ingest — setup and folder structure

These scripts fold a byte sequence into one topological memory and reconstruct it
in full or by range, with an optional registry for format handlers. Intake is
headless by default; progress/output is opt-in. They depend on three engine
modules from the Marvosa repo, which are included here.

## Required folder structure
The three top-level scripts must sit together, with an `engine/` directory beside
them containing the three engine modules:

    ingest_and_expel/
    ├── ingest_expel.py        # intake + chunk-window reconstruction + resonance recall
    ├── format_dock.py          # FormatRegistry: map a format to a handler (code path)
    ├── format_config.py        # declare formats as data and compile them (config path)
    ├── SETUP.md                # this file
    ├── README.md               # full technical reference for all three modules
    └── engine/
        ├── juj.py              # guhct-processor: bytes <-> braid/HVP (bijective)
        ├── hcl_memory.py       # virtual-memory-hcl: hcl_comp, FBit, invariants
        └── hcl_engine.py       # HCL substrate constants/operations

`ingest_expel.py` adds its own adjacent `engine/` directory to `sys.path` at
import (using its own file location), so the only requirement is that `engine/`
stays directly beside `ingest_expel.py`. Renaming or moving `engine/` away from
it raises `ModuleNotFoundError` for `juj` / `hcl_memory`.

`juj.py` and `hcl_memory.py` have no external imports and do not import each other
or `hcl_engine.py` at module load; all three are included so the package is
self-contained. `format_dock.py` uses only the standard library. `format_config.py`
imports `format_dock`.

## Importing from your own code
Point `sys.path` at the directory that contains the scripts (the `ingest_and_expel/`
directory above), then import the public names:

    import sys
    sys.path.insert(0, '/path/to/ingest_and_expel')      # directory holding ingest_expel.py
    from ingest_expel import StreamedMemory, ingest_reader, stream_into_memory, ingest_file, ingest_bytes
    from format_dock   import FormatRegistry, FormatHandler, registry
    from format_config import compile_spec, load_specs, load_file

You do not add `engine/` to `sys.path` yourself; `ingest_expel.py` does that.

## Quick check
From inside the `ingest_and_expel/` directory:

    python3 -c "import ingest_expel as si; \
m,_ = si.ingest_bytes(bytes(range(256))*80, chunk=8192); \
print('ok:', m.whole() == m.window(0, None))"

Should print `ok: True`.

## Running as a script (CLI)
    python3 ingest_expel.py <url> --chunk <bytes> [--max-bytes <n>]

Streams a URL into a `StreamedMemory` and prints the final chunk count and
signature. Per-chunk progress is disabled unless `--progress` is passed. The CLI
runs only when the file is executed directly, not on import.

## Where the full API is documented
`README.md` — intake functions, `StreamedMemory` methods
(`signature`, `whole`, `window`, `regenerate`, `resonate`), the format registry
(code and config paths), and the format-authoring guide with the request-flow
timeline.
