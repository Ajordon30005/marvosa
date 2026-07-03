"""
format_dock.py — an optional registry that maps a format to a handler and routes
a StreamedMemory's chunk windows to it. It is separate from ingest_expel and
imports nothing from it; it operates only through the StreamedMemory methods
mem.window / mem.whole / mem.regenerate / mem.resonate. The ingest core remains
format-agnostic: this module adds no parsing of its own and modifies no ingest
behavior.

A handler is a triple:
    name   : str                         identifier for the format
    detect : detect(head_bytes) -> bool  returns True if head_bytes are this format
    open   : open(mem, **opts) -> Any    reads chunk windows from mem (e.g. a byte
                                         range corresponding to one PDF page) and
                                         returns the result; the return type is the
                                         handler's own (bytes, a structure, or None)

FormatRegistry stores handlers and exposes:
    register(name, detect, open, description)   add/replace a handler by name
    from_list(handlers)                         add handlers from a list
    names()                                     registered handler names
    detect(mem, head_bytes=4096)                read mem.window(0, head_bytes) and
                                                return the first handler whose
                                                detect() returns True, else None
    open_with(mem, name=None, **opts)           run a handler: the named one, or the
                                                detected one if name is None; raises
                                                LookupError if none applies; returns
                                                the handler's return value

Fallback handlers are tried after ordinary handlers. The built-in raw handler is
therefore available as a default without preventing later PDF/image/custom
recognizers from being detected first.

Detection reads only the leading bytes via mem.window(0, head_bytes); it does not
reconstruct the full sequence. open() reads whatever windows the handler requests.
No output is produced by this module: handlers receive bytes and return values;
any text or display is performed inside a handler, not here.

Handlers may be authored as callables here, or declared as data and compiled by
format_config (the config/command path); both produce FormatHandler objects and
register on the same FormatRegistry.
"""

class FormatHandler:
    """One dockable format handler.

    fallback handlers are tried after ordinary handlers, so an always-match raw
    handler cannot hide a more specific recognizer registered later.
    """
    __slots__ = ('name', 'detect', 'open', 'description', 'fallback')

    def __init__(self, name, detect, open, description="", fallback=False):
        self.name = name
        self.detect = detect            # detect(head_bytes) -> bool
        self.open = open                # open(mem, **opts) -> anything
        self.description = description
        self.fallback = bool(fallback)


class FormatRegistry:
    """Stores format handlers and selects one to run against a StreamedMemory.
    A handler is chosen either by explicit name or by detection over the leading
    bytes. Handlers are added at runtime via register() or in bulk via from_list()."""

    def __init__(self):
        self._handlers = []

    def register(self, name, detect, open, description="", fallback=False):
        """Add a handler. If a handler with the same name exists it is replaced.

        Fallback handlers are kept at the end. This lets the built-in raw
        handler act like Windows' "open as raw bytes" option without preempting
        handlers that recognize a real format.
        """
        self._handlers = [h for h in self._handlers if h.name != name]
        handler = FormatHandler(name, detect, open, description, fallback)
        if handler.fallback:
            self._handlers.append(handler)
        else:
            for i, h in enumerate(self._handlers):
                if h.fallback:
                    self._handlers.insert(i, handler)
                    break
            else:
                self._handlers.append(handler)
        return self

    def from_list(self, handlers):
        """Add handlers from a list whose items are FormatHandler instances or
        dicts with keys name, detect, open, and optional description."""
        for h in handlers:
            if isinstance(h, FormatHandler):
                self.register(h.name, h.detect, h.open, h.description, h.fallback)
            else:
                self.register(h['name'], h['detect'], h['open'],
                              h.get('description', ''), h.get('fallback', False))
        return self

    def names(self):
        return [h.name for h in self._handlers]

    def detect(self, mem, head_bytes=4096):
        """Read mem.window(0, head_bytes) and return the name of the first handler
        whose detect() returns True, or None if no handler matches. Only the
        leading bytes are read; the full sequence is not reconstructed."""
        head = mem.window(0, head_bytes)
        for h in self._handlers:
            try:
                if h.detect(head):
                    return h.name
            except Exception:
                continue
        return None

    def open_with(self, mem, name=None, **opts):
        """Run a handler against mem. If name is given, run that handler; otherwise
        run the handler returned by detect(). Raise LookupError if name is None and
        detection fails, or if name has no registered handler. Return the handler's
        return value (type defined by the handler)."""
        if name is None:
            name = self.detect(mem)
            if name is None:
                raise LookupError(
                    "no registered handler recognizes this format; "
                    f"register one or pass name=... (have: {self.names()})")
        for h in self._handlers:
            if h.name == name:
                return h.open(mem, **opts)
        raise LookupError(f"no handler named {name!r} (have: {self.names()})")


# Module-level registry instance, available for callers that do not
# construct their own FormatRegistry.
registry = FormatRegistry()


# Built-in "raw" handler: detect() matches any input, open() returns the window
# mem.window(offset, size). It serves as the default when no format-specific
# handler matches. Additional handlers follow the same (name, detect, open) form.
def _raw_detect(head: bytes) -> bool:
    return True                                # matches any input

def _raw_open(mem, offset=0, size=None, **_):
    """Return mem.window(offset, size) of the sequence."""
    return mem.window(offset, size)

registry.register('raw', _raw_detect, _raw_open,
                  "raw bytes — returns mem.window(offset, size)",
                  fallback=True)


# safetensors handler: the checkpoint doorway. A .safetensors file declares its
# own layout — 8 bytes little-endian header length N, then N bytes of JSON
# mapping tensor name -> {dtype, shape, data_offsets [begin, end]} relative to
# byte 8+N. detect() reads that declaration from the leading bytes; open()
# turns it into window reads: no tensor argument returns the table of contents
# (name -> absolute offset/size/dtype/shape); tensor='name' returns that
# tensor's exact bytes via mem.window. Pure API over window() — the header is
# parsed at the boundary; every byte delivered comes through the expel path.
def _safetensors_detect(head: bytes) -> bool:
    if len(head) < 10:
        return False
    n = int.from_bytes(head[:8], 'little')
    return 0 < n <= 100_000_000 and head[8:9] == b'{'

def _safetensors_open(mem, tensor=None, meta=False, **_):
    """No args -> {name: {'offset','size','dtype','shape'}} (absolute offsets).
    tensor='name' -> that tensor's exact bytes. meta=True -> __metadata__."""
    import json as _json
    n = int.from_bytes(mem.window(0, 8), 'little')
    hdr = _json.loads(mem.window(8, n).decode('utf-8'))
    if meta:
        return hdr.get('__metadata__')
    base = 8 + n
    toc = {}
    for name, t in hdr.items():
        if name == '__metadata__':
            continue
        b, e = t['data_offsets']
        toc[name] = {'offset': base + b, 'size': e - b,
                     'dtype': t.get('dtype'), 'shape': t.get('shape')}
    if tensor is None:
        return toc
    t = toc[tensor]
    return mem.window(t['offset'], t['size'])

registry.register('safetensors', _safetensors_detect, _safetensors_open,
                  "safetensors checkpoint — toc, or tensor='name' for exact tensor bytes")


__all__ = ['FormatHandler', 'FormatRegistry', 'registry']
