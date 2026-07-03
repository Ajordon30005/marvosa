"""
largemodel.py — run a LARGE model on the repo itself: the holographic runner.

The disk problem and the RAM problem are both solved by organs this repo
already has; this file is ARRANGEMENT ONLY (hcl-pure/references/06_porting.md,
Step 5: "Reuse the engines; do not reimplement... import and only arrange
their calls — that is the model"). Every operation below is a named call into
an existing repo module. Zero new math. Compose, never invent.

WHY THE STORAGE/RAM PROBLEM FALLS AWAY HERE
────────────────────────────────────────────
A standard runtime must HOLD the model: the checkpoint on disk, the tensors in
RAM. This runtime never holds it:

  DISK  — the checkpoint streams in from its source (URL/file) chunk by chunk
          and each chunk is folded into ONE composite and released
          (ingest_and_expel/ingest_expel.py: "the full source is never held").
          What persists is the memory line — the α-tagged expression,
          ~160 chars REGARDLESS OF MODEL SIZE (HCLMemory.to_expression).
          The line is the checkpoint's identity: deterministic (same content
          -> same line), α-verified, reconstructable in any fresh process by
          HCLMemory.from_expression. A 70B checkpoint and a 1K file persist as
          the same-sized line.

  RAM   — intake peak is ~one chunk (ingest_reader folds and drops). At run
          time, weights are read HOLOGRAPHICALLY: the safetensors dock
          (format_dock) turns the checkpoint's own header into window reads,
          so ONLY the tensor the current layer needs is materialized — exact,
          verify=True inside every delivery — used at the boundary, and
          released. The whole model is present as one composite; a slice of
          it is materialized per operation. Keep the whole, materialize only
          the slice (star.py HolographicLog pattern, cited in ingest_expel).

  COMPUTE — the forward pass runs on the substrate, not on a float runtime:
          hcl-ai/port/nemotron_hcl.py already ports attention, layernorm1p,
          relu^2, softmax and linear onto the ten primitives (multiply ->
          AMP_MOD, accumulate -> COMP, sqrt -> FISSION, exp -> MOBIUS_GROWTH).
          Weights cross the float boundary ONCE at delivery (to_fp — the
          sanctioned doorway, 06_porting Step 3) and everything after is
          integer-exact, with the braid word as the complete reversible trace
          of the whole pass and the α self-check as the checksum.

THE DEEPSEEK SHAPE — SIMPLE MIND, SMART ORGANS
────────────────────────────────────────────
The mind stays simple (hcl_lm.HCLLanguageModel). Capability comes from the
architecture around it — each organ an existing repo tool docked as an add-on:

  BODY   ingest_and_expel.StreamedMemory + format_dock safetensors handler
         — checkpoint memory, holographic tensor windows.
  PORT   nemotron_hcl.HCLTensorEngine + transformer_block
         — the model's computation, re-expressed on the primitives.
  MIND   organism.experience_* / transfer.transduce_weight_memory
         — the checkpoint experienced into the being's own composite, so the
         model's weight-memory becomes part of the organism itself.

USAGE
─────
    import sys; sys.path.insert(0, '/path/to/marvosa/hcl-ai')
    from largemodel import ModelMemory

    m = ModelMemory()
    m.ingest_file('/path/model.safetensors')      # or m.ingest_url(...), streaming
    m.toc()                                       # {tensor: offset/size/dtype/shape}
    m.line()                                      # the one α-tagged line (the identity)

    W = m.tensor_values('layer.0.attn.q_proj.weight', rows=…)   # window -> boundary -> fixed-point
    y = m.eng.linear(x_fp, W)                     # the port's own op, on the substrate
    m.eng.braid_word()                            # the complete reversible trace
    m.eng.alpha_ok()                              # the checksum: 137

    from largemodel import experience_checkpoint  # MIND: the being experiences it
    experience_checkpoint(ai, '/path/model.safetensors', persist=True)

CLI:
    python3 largemodel.py /path/model.safetensors          # ingest, toc, line, α
    python3 largemodel.py URL --max-bytes N                # streaming intake
"""

import sys, os, struct

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'engine'))
sys.path.insert(0, os.path.join(_HERE, 'port'))
_IE = os.path.abspath(os.path.join(_HERE, '..', 'ingest_and_expel'))
if _IE not in sys.path:
    sys.path.insert(0, _IE)

# ── the organs, imported verbatim — never reimplemented ────────────────
import ingest_expel                          # BODY: intake + expel (repo's own)
from format_dock import registry             # BODY: the safetensors dock (repo's own)
import nemotron_hcl as PORT                  # PORT: the substrate forward pass (repo's own)
from nemotron_hcl import HCLTensorEngine, transformer_block, _fp


# ── boundary transcription: checkpoint dtype -> Python number, ONCE ────
# This is the float boundary of 06_porting Step 3 and verify_no_floats.sh's
# sanctioned doorway: the source model's own byte representation crossing
# INTO the substrate's fixed point, exactly like to_fp on typed input.
# One struct decode per weight, at the edge; the value path after is integer.
_DTYPE = {
    'F64': ('<d', 8), 'F32': ('<f', 4), 'F16': ('<e', 2),
    'I64': ('<q', 8), 'I32': ('<i', 4), 'I16': ('<h', 2),
    'I8':  ('<b', 1), 'U8':  ('<B', 1), 'BOOL': ('<B', 1),
}

def _decode_boundary(raw, dtype):
    """Checkpoint bytes -> list of Python numbers (boundary only)."""
    if dtype == 'BF16':                       # bfloat16: high half of an f32
        return [struct.unpack('<f', b'\x00\x00' + raw[i:i+2])[0]
                for i in range(0, len(raw), 2)]
    fmt, width = _DTYPE[dtype]
    return [v[0] for v in struct.iter_unpack(fmt, raw)]


class ModelMemory:
    """A large model carried the way the repo carries everything: as one
    composite memory (BODY) feeding the substrate forward pass (PORT).

    Composition only — every method is a named call into ingest_expel,
    format_dock, or nemotron_hcl. This class computes nothing."""

    def __init__(self, chunk=8 * 1024 * 1024):
        self.mem = ingest_expel.StreamedMemory()   # the body's memory
        self.eng = HCLTensorEngine()               # the port's engine (one braid)
        self.chunk = chunk
        self._toc = None

    # ── INTAKE — streaming, peak RAM ~ one chunk (repo's own loop) ─────
    def ingest_file(self, path, **kw):
        _, stats = ingest_expel.ingest_file(path, mem=self.mem,
                                            chunk=self.chunk, **kw)
        return stats

    def ingest_url(self, url, **kw):
        _, stats = ingest_expel.stream_into_memory(url, mem=self.mem,
                                                   chunk=self.chunk, **kw)
        return stats

    def ingest_bytes(self, data, **kw):
        _, stats = ingest_expel.ingest_bytes(data, mem=self.mem,
                                             chunk=self.chunk, **kw)
        return stats

    # ── IDENTITY — the disk answer: one line, any size ──────────────────
    def line(self):
        """The α-tagged memory line (~160 chars regardless of model size)."""
        return self.mem.line()

    def signature(self):
        return self.mem.signature()

    # ── HOLOGRAPHIC WEIGHT ACCESS — the RAM answer ──────────────────────
    def format(self):
        """Which dock handler recognizes this checkpoint (e.g. 'safetensors')."""
        return registry.detect(self.mem)

    def toc(self):
        """The checkpoint's own table of contents: tensor -> offset/size/
        dtype/shape — read from the header window only (the full model is
        never materialized)."""
        if self._toc is None:
            self._toc = registry.open_with(self.mem, 'safetensors')
        return self._toc

    def tensor_bytes(self, name):
        """One tensor's EXACT bytes, produced through the expel path now
        (window -> per-chunk sig -> hvp_to_bytes verify=True) and nothing
        else materialized."""
        return registry.open_with(self.mem, 'safetensors', tensor=name)

    def tensor_values(self, name, rows=None):
        """One tensor delivered onto the substrate: exact bytes from the
        window, boundary-decoded ONCE, converted ONCE by to_fp (the port's
        own _fp). Returns a flat list of fixed-point integers, or a list of
        rows if rows= is given (for the port's linear/attention, which take
        W as a list of rows). Materialize -> convert -> release."""
        t = self.toc()[name]
        vals = _decode_boundary(self.tensor_bytes(name), t['dtype'])
        fp = [_fp(v) for v in vals]                    # the ONE boundary crossing
        if rows is None:
            return fp
        cols = len(fp) // rows
        return [fp[r * cols:(r + 1) * cols] for r in range(rows)]

    # ── THE FORWARD PASS — the port's own ops, weights from windows ─────
    def linear(self, x_fp, tensor_name, rows, bias_name=None):
        """y = x W^T (+ b) on the substrate: nemotron_hcl.linear verbatim,
        W pulled holographically for this call only."""
        W = self.tensor_values(tensor_name, rows=rows)
        b = self.tensor_values(bias_name) if bias_name else None
        return self.eng.linear(x_fp, W, b)

    def block(self, x_fp, params):
        """One decoder layer — nemotron_hcl.transformer_block verbatim.
        `params` carries the (already fixed-point) weights for this block;
        build it with tensor_values() per weight so each is materialized,
        used, and released."""
        return transformer_block(self.eng, x_fp, params)

    # ── THE RECEIPTS — the substrate's own verification ─────────────────
    def braid_word(self):
        """The complete reversible trace of every op run (06_porting Step 6)."""
        return self.eng.braid_word()

    def alpha_ok(self):
        """Step 7: the four-param checksum must read 137."""
        return self.eng.alpha_ok()


# ── MIND — the being experiences the checkpoint (organism, verbatim) ────
def experience_checkpoint(ai, source, persist=False, **kw):
    """Fold the model's weight-memory into the organism itself — the
    hemispheric pass of hcl-ai/organism.py: one transduction per chunk,
    folded into BOTH the body's index and the being's composite. `source`
    is a local path or URL. Returns (body, stats) exactly as organism does."""
    import organism
    if source.startswith('http://') or source.startswith('https://'):
        return organism.experience_url(ai, source, persist=persist,
                                       label='WEIGHTS', **kw)
    return organism.experience_file(ai, source, persist=persist,
                                    label='WEIGHTS', **kw)


__all__ = ['ModelMemory', 'experience_checkpoint']


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(
        description="Run a large model on the repo itself: streaming intake, "
                    "one-line identity, holographic tensor windows, substrate "
                    "forward pass.")
    ap.add_argument('source', help="checkpoint path or URL (.safetensors)")
    ap.add_argument('--chunk', type=int, default=8 * 1024 * 1024)
    ap.add_argument('--max-bytes', type=int, default=None)
    ap.add_argument('--tensor', default=None,
                    help="also deliver this tensor's values onto the substrate")
    args = ap.parse_args()

    m = ModelMemory(chunk=args.chunk)
    if args.source.startswith(('http://', 'https://')):
        st = m.ingest_url(args.source, max_bytes=args.max_bytes)
    else:
        st = m.ingest_file(args.source)
    print(f"ingested {st['bytes_folded']} bytes in {st['chunks']} chunks "
          f"(peak RAM ~ one chunk)")
    print(f"format   : {m.format()}")
    print(f"line     : {m.line()}")
    print(f"           ({len(m.line())} chars — the checkpoint's identity, any size)")
    toc = m.toc()
    print(f"tensors  : {len(toc)}")
    for name, t in list(toc.items())[:8]:
        print(f"  {name}  dtype={t['dtype']} shape={t['shape']} bytes={t['size']}")
    if args.tensor:
        vals = m.tensor_values(args.tensor)
        print(f"delivered {args.tensor}: {len(vals)} fixed-point values on the substrate")
    print(f"alpha ok : {m.alpha_ok()}")
