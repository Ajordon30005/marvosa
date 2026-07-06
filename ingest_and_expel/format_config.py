"""
format_config.py — declare format handlers as data (config) instead of callables,
and register them on a FormatRegistry. This is the command/config path that sits
on top of format_dock; the callable path (FormatRegistry.register / from_list)
remains available and unchanged. Both can be used together.

A format spec is a dict (or a list of dicts, or JSON of the same). Each spec is
compiled into a FormatHandler whose detect/open are built from the declared data
— no user-supplied code is executed. Fields:

    name        : str                    format identifier (required)
    description : str                    optional text
    fallback    : bool                   optional; true means try after normal
                                          recognizers (use for raw/default)

    detect      : how to recognize the format from the leading bytes. One of:
                    {"magic": "255044462d", "offset": 0}   hex bytes at a byte offset
                    {"any": true}                          matches any input (fallback)
                  (omit detect -> never auto-detected; select it by name)

    open        : how a request maps to a window read. A recipe evaluated against
                  the call options (opts) and these names:
                    unit    : bytes per indexed item (e.g. page/record size)
                    base    : fixed byte offset added to every read (e.g. header)
                  The read is:
                    offset = base + index * unit          (index defaults to 0)
                    size   = length                       (length defaults to unit)
                  where `index` and `length` are taken from opts if present, else
                  from the open spec's defaults, else as above. Declared as:
                    {"unit": 8192, "base": 8192,
                     "index_opt": "page", "length": 8192}
                  index_opt names which call option supplies the index (e.g.
                  open_with(mem, page=3) -> index=3). If open is omitted, the
                  handler returns the whole sequence.

Compilation is total: a spec with unknown detect/open shapes raises ValueError at
load time, so a malformed config fails immediately rather than at call time.
"""

import json
from format_dock import FormatRegistry, FormatHandler


def _build_detect(spec):
    """Return a detect(head_bytes)->bool from a detect spec dict (or None)."""
    if spec is None:
        return lambda head: False                 # not auto-detectable; select by name
    if spec.get('any') is True:
        return lambda head: True
    if 'magic' in spec:
        offset = int(spec.get('offset', 0))
        magic = bytes.fromhex(spec['magic'])
        return lambda head: head[offset:offset + len(magic)] == magic
    raise ValueError(f"unknown detect spec: {spec!r}")


def _build_open(spec):
    """Return an open(mem, **opts)->bytes from an open spec dict (or None)."""
    if spec is None:
        return lambda mem, **opts: mem.whole()
    unit = spec.get('unit')
    base = int(spec.get('base', 0))
    index_opt = spec.get('index_opt', 'index')
    default_index = int(spec.get('index', 0))
    default_length = spec.get('length', unit)

    def _open(mem, **opts):
        index = int(opts.get(index_opt, default_index))
        length = opts.get('length', default_length)
        if unit is None and length is None:
            return mem.whole()
        offset = base + index * (unit if unit is not None else 0)
        return mem.window(offset, length)
    return _open


def compile_spec(spec):
    """Compile one format spec dict into a FormatHandler. Raises ValueError on a
    malformed spec."""
    if 'name' not in spec:
        raise ValueError(f"format spec missing 'name': {spec!r}")
    return FormatHandler(
        name=spec['name'],
        detect=_build_detect(spec.get('detect')),
        open=_build_open(spec.get('open')),
        description=spec.get('description', ''),
        fallback=spec.get('fallback', False),
    )


def load_specs(specs, registry=None):
    """Compile a list of spec dicts and register them. `specs` may be a single
    dict, a list of dicts, or a JSON string of either. Returns the registry
    (a new FormatRegistry if none is given)."""
    if isinstance(specs, str):
        specs = json.loads(specs)
    if isinstance(specs, dict):
        specs = [specs]
    reg = registry if registry is not None else FormatRegistry()
    for spec in specs:
        h = compile_spec(spec)
        reg.register(h.name, h.detect, h.open, h.description)
    return reg


def load_file(path, registry=None):
    """Load format specs from a JSON file (a list of spec dicts) and register
    them. Returns the registry."""
    with open(path) as f:
        return load_specs(json.load(f), registry)


__all__ = ['compile_spec', 'load_specs', 'load_file']
