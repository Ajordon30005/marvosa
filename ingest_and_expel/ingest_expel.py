"""
ingest_expel.py — INGEST any byte sequence into one topological memory, and
EXPEL exact bytes back out of it, using only the Marvosa repo's own processing
(guhct-processor + virtual-memory-hcl + guhct-living-memory). Two motions, one
memory: INGEST folds each streamed chunk into the composite index and keeps its
braid record; EXPEL produces bytes at delivery by running the processor
(whole/window/recall/resonate). Intake is headless by default; materializing
bytes is opt-in and bounded (a window). Expulsion is exact (verify=True inside
every delivery).

────────────────────────────────────────────────────────────────────────────
USAGE (import interface)

Requirement: this file sits beside its `engine/` directory, which holds the
repo's `juj.py`, `hcl_memory.py`, `hcl_engine.py` verbatim (it self-locates
engine/ automatically — no other setup).

    import sys
    sys.path.insert(0, '/path/to/ingest_and_expel')    # the folder with this file
    from ingest_expel import (StreamedMemory, stream_into_memory,
                              ingest_file, ingest_bytes)

    # 1) intake — pick ONE, any byte source:
    mem, stats = stream_into_memory('https://host/model.safetensors')  # streaming download
    mem, stats = ingest_file('/path/model.bin')                        # a local file
    mem, stats = ingest_bytes(raw_bytes)                               # bytes in memory

    # 2) the whole intake is now ONE composite index of experience:
    mem.signature()           # {'n_w','writhe','jones_span','depth'} — the line's head
    mem.line()                # the α-tagged memory line (HCLMemory.to_expression)

    # 3) reproduce — choose how much at a time:
    mem.whole()               # the entire sequence, exact bytes
    mem.window(offset, size)  # any byte range, exact (a bounded slice)
    mem.regenerate(key)       # one chunk by key, exact

    # 4) resonance recall — give bytes, get the chunk they resonate with:
    key, data = mem.resonate(some_bytes)   # topological-invariant match, exact bytes

Intake reads the source in fixed-size chunks and folds each one, then discards
it, so the full source is never held in memory at once. Reconstruction is the
processor bijection juj.hvp_to_bytes. The value path uses integer HCL operations
(no floating point).
────────────────────────────────────────────────────────────────────────────

This module provides the network/file/byte intake loop and the chunk-window
reconstruction. All transduction is performed by the guhct-processor functions,
called with the signature object kept intact and passed back whole. window()
reconstructs only the chunks intersecting the requested [offset, offset+size)
range; it follows the same access pattern as the windowed log view in star.py,
which retains the full sequence but materializes only the requested slice.
"""

import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'engine'))

import juj                                  # the guhct-processor skill (exact-content layer)
from hcl_memory import HCLMemory, hcl_comp, make_braid_term   # virtual-memory-hcl (index/address layer)


class StreamedMemory:
    """A streamed sequence carried as the repo carries it — composition.md's
    "two skills, two roles, one memory":

    INDEX / ADDRESS ROLE (virtual-memory-hcl, self.vm): every chunk is folded
    into the ONE composite exactly as the repo's own hcl-ai/stream_ingest.py
    fold_chunk does — bytes_to_braid -> braid_invariants -> hcl_comp into the
    composite, a braid term appended, signature updated. The whole download
    becomes one composite index of experience; the memory line is the skill's
    own α-tagged expression (self.vm.to_expression(), ~160 chars regardless of
    size), reconstructable in any fresh process by HCLMemory.from_expression —
    α-verified, deterministic (same content -> same line), no download needed.
    The line reconstructs THE MEMORY (identity/resonance); it does not replay
    the bytes — the repo's own ingest discards them by design ("the file itself
    was never held").

    EXACT-CONTENT ROLE (guhct-processor + guhct-living-memory, self._recs):
    each chunk's braid record — the data-carrying term, the braid IS the record
    — lives in RAM only (Rule 1: zero disk I/O for state). At delivery the sig
    is produced by processing (juj.bytes_to_hvp), expanded by the verified
    inverse (juj.hvp_to_bytes, verify=True), and released — the AI's speak()
    shape. whole()/window()/recall()/resonate() run on this layer, bit-perfect,
    with no re-download. RAM is populated only during processing, finite per
    request; nothing is persisted between requests as a signature list.
    """

    def __init__(self):
        self.vm = HCLMemory()      # the index: ONE composite; its to_expression() is the memory line
        self._recs = {}            # key -> braid record (exact-recall layer; RAM-only, Rule 1)

    def line(self):
        """The memory line — the skill's own α-tagged expression of the whole
        composite index (HCLMemory.to_expression, verbatim). Reconstructable by
        HCLMemory.from_expression in any fresh process."""
        return self.vm.to_expression()

    def _ordered_keys(self):
        """Return stored keys in stream order.

        Keys produced by this module end in ':chunk<N>'. Direct callers may use
        other keys, so non-stream keys keep insertion order after numbered chunks.
        """
        keys = list(self._recs.keys())
        order = {k: i for i, k in enumerate(keys)}

        def rank(k):
            head, sep, tail = k.rpartition(':chunk')
            if sep:
                try:
                    return (0, int(tail), order[k])
                except ValueError:
                    pass
            return (1, order[k], k)

        return sorted(keys, key=rank)

    def fold(self, key, chunk_bytes, keep_record=True):
        """Experience one chunk — the repo's own fold (hcl-ai/stream_ingest.py
        fold_chunk), composed verbatim: transduce to the braid, take its
        invariants ONCE, fold the spectrum into the composite index, append the
        braid term, update the signature. The braid record is additionally kept
        in RAM as the exact-recall layer (living-memory role); no signature
        object is retained — the sig is produced again, by processing, at
        delivery. With keep_record=False the braid is released after the fold —
        the repo's own index-only motion (hcl-ai/stream_ingest.py: fold and
        discard, peak memory ~ one chunk): the line/resonance stand, the expel
        layer holds nothing."""
        braid = juj.bytes_to_braid(chunk_bytes)              # bytes -> braid (bijective)
        inv = juj.braid_invariants(braid)                    # one invariants pass per chunk
        wfbit = inv['spectrum']
        self.vm._composite = hcl_comp(self.vm._composite, wfbit)   # fold into the index
        self.vm._terms.append(make_braid_term(key, wfbit, inv))
        self.vm._braid_log.append({
            'op':         f'STREAM_CHUNK[{key}]',
            'phase_frac': wfbit.phase_frac,
            'amp':        wfbit.amp,
            'n_w':        inv['n_w'],
            'writhe':     inv['writhe'],
            'jones_span': inv['jones_span'],
        })
        self.vm._update_signature()                          # the index reflects this chunk
        if keep_record:
            self._recs[key] = braid                          # exact-recall record (RAM, Rule 1)
        return self.vm.signature()

    def recall(self, key):
        """Produce one chunk's exact bytes by running the processor now — the
        AI's speak() shape verbatim: the sig is produced by processing
        (juj.bytes_to_hvp) as a local, transient object, expanded by the
        processor's verified inverse (juj.hvp_to_bytes, verify=True), and
        released. Nothing was held cold; nothing survives the request."""
        sig = juj.bytes_to_hvp(juj.braid_to_bytes(self._recs[key]))
        return juj.hvp_to_bytes(sig, verify=True)

    def regenerate(self, key):
        """Exact bytes of one recalled chunk (see recall())."""
        return self.recall(key)

    def resonate(self, input_bytes):
        """Recall by RESONANCE: the input's topology (juj.braid_invariants) is
        matched by the processor's own COMP (juj.comp — one scale); collapse
        selects the Path-Dominant Attractor, whose bytes are then produced by
        the processor. Returns (key, bytes), or (None, b'') if empty. The
        per-chunk topology is produced from its record at match time, not held
        as a sig."""
        if not self._recs:
            return None, b''
        qi = juj.braid_invariants(juj.bytes_to_braid(input_bytes))
        q_sig  = (qi['n_w'], qi['writhe'], qi['jones_span'])
        q_fbit = qi['spectrum']
        best_key, best = None, None
        for key in self._recs:
            mi = juj.braid_invariants(self._recs[key])         # produced from the record now
            m_sig = (mi['n_w'], mi['writhe'], mi['jones_span'])
            exact = (m_sig == q_sig)
            align = juj.comp(q_fbit, mi['spectrum']).amp       # resonance, processor scale
            rank  = (1 if exact else 0, align)
            if best is None or rank > best:                    # collapse to dominant attractor
                best_key, best = key, rank
        return best_key, self.recall(best_key)

    def window(self, offset=0, size=None, key_prefix=None):
        """Materialize a bounded WINDOW of the sequence (star.py HolographicLog
        pattern: keep the whole, materialize only the requested slice). Only the
        chunks the window touches are produced through the processor; the rest
        are never materialized. RAM is finite per this request."""
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if size is not None and size < 0:
            raise ValueError("size must be >= 0")
        keys = self._ordered_keys()
        if not keys:
            return b''
        total = sum(len(self._recs[k]) for k in keys)       # braid length == byte length
        if offset >= total or size == 0:
            return b''
        if size is None:
            size = total - offset
        end = min(total, offset + size)
        out = bytearray()
        cursor = 0
        for key in keys:
            n = len(self._recs[key])
            nxt = cursor + n
            if nxt <= offset:
                cursor = nxt
                continue
            if cursor >= end:
                break
            blk = self.recall(key)                           # produce this chunk now
            lo = max(0, offset - cursor)
            hi = min(n, end - cursor)
            out += blk[lo:hi]
            cursor = nxt
        return bytes(out)

    def whole(self, key_prefix=None):
        """Materialize the ENTIRE sequence in order (window over all of it)."""
        return self.window(0, None, key_prefix)

    def signature(self):
        """The whole memory's topological signature — the index's own
        (HCLMemory.signature: n_w, writhe, jones_span, depth). These integers
        head the memory line; they are the identity/address of the stream, not
        the byte-reconstruction path (the processor is)."""
        return self.vm.signature()


def ingest_reader(reader, mem=None, chunk=8 * 1024 * 1024, max_bytes=None,
                  key_prefix='stream', progress=False, keep_records=True):
    """
    Intake any object with read(n)->bytes in `chunk`-byte pieces; hand each
    chunk's bytes to the processor (mem.fold) as it arrives, then drop the
    chunk. This is the headless core intake hook for files, downloads, pipes,
    custom fetchers, or any other byte source. `max_bytes` caps the pull.

    Returns (mem, stats). Get any chunk back with mem.regenerate(key); query with
    mem.resonate(input_bytes) -> (key, bytes) by topological match.
    """
    if mem is None:
        mem = StreamedMemory()
    total = n = 0
    while True:
        want = chunk if max_bytes is None else min(chunk, max_bytes - total)
        if want <= 0:
            break
        blk = reader.read(want)
        if not blk:
            break
        mem.fold(f'{key_prefix}:chunk{n}', blk, keep_record=keep_records)
        total += len(blk); n += 1
        blk = None                                 # drop the chunk
        if progress:
            print(f"  chunk {n}: +{total} bytes folded")
    return mem, {'bytes_folded': total, 'chunks': n, 'signature': mem.signature()}


def stream_into_memory(url, mem=None, chunk=8 * 1024 * 1024, max_bytes=None,
                       key_prefix='stream', progress=False, keep_records=True):
    """
    Stream `url` in `chunk`-byte pieces. Network access is boundary I/O only;
    transduction still happens exclusively through mem.fold -> juj.bytes_to_hvp.
    """
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'marvosa-stream'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return ingest_reader(resp, mem=mem, chunk=chunk, max_bytes=max_bytes,
                             key_prefix=key_prefix, progress=progress,
                             keep_records=keep_records)


def ingest_bytes(data, mem=None, chunk=8 * 1024 * 1024, key_prefix='stream',
                 keep_records=True):
    """Intake a raw byte sequence already in memory (any bytes — weights, a file's
    contents, anything). Folds it chunk-by-chunk through the processor, same as
    streaming. Returns (mem, stats). Use mem.whole()/mem.window()/mem.resonate()."""
    if mem is None:
        mem = StreamedMemory()
    total = n = 0
    for off in range(0, len(data), chunk):
        blk = data[off:off + chunk]
        mem.fold(f'{key_prefix}:chunk{n}', blk, keep_record=keep_records)
        total += len(blk); n += 1
    return mem, {'bytes_folded': total, 'chunks': n, 'signature': mem.signature()}


def ingest_file(path, mem=None, chunk=8 * 1024 * 1024, key_prefix='stream',
                progress=False, keep_records=True):
    """Intake a local file (e.g. a model checkpoint on disk) by reading it
    chunk-by-chunk and folding each through the processor — never loads the whole
    file into RAM at once. Returns (mem, stats)."""
    with open(path, 'rb') as f:
        return ingest_reader(f, mem=mem, chunk=chunk, key_prefix=key_prefix,
                             progress=progress, keep_records=keep_records)


# Public API — what another program imports and uses.
__all__ = [
    'StreamedMemory',      # the memory: .fold | .whole .window .recall .regenerate .resonate | .line .signature
    'ingest_reader',       # intake from any object exposing read(n)->bytes
    'stream_into_memory',  # intake from a URL  (streaming download)
    'ingest_file',         # intake from a local file path
    'ingest_bytes',        # intake from raw bytes already in memory
]


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(
        description="INGEST a byte stream into one topological memory; EXPEL exact bytes back out.")
    ap.add_argument('url', help="URL of the weight file to stream")
    ap.add_argument('--chunk', type=int, default=8 * 1024 * 1024)
    ap.add_argument('--max-bytes', type=int, default=None)
    ap.add_argument('--progress', action='store_true',
                    help="print per-chunk progress; default is headless")
    ap.add_argument('--index-only', action='store_true',
                    help="fold and discard (the repo's own motion): keep only the composite index — peak memory ~ one chunk; no expel layer")
    args = ap.parse_args()

    print(f"Streaming {args.url} (chunk {args.chunk}B, file never fully stored)...")
    mem, stats = stream_into_memory(args.url, chunk=args.chunk,
                                    max_bytes=args.max_bytes,
                                    progress=args.progress,
                                    keep_records=not args.index_only)
    s = stats['signature']
    print(f"\n  folded {stats['bytes_folded']} bytes in {stats['chunks']} chunks")
    print(f"  memory signature: depth {s['depth']}, n_w {s['n_w']}, "
          f"writhe {str(s['writhe'])[:18]}..., jones_span {s['jones_span']}")
    print(f"  memory line: {mem.line()}")
    if not args.index_only:
        print("  expel any chunk: mem.recall(key) | whole: mem.whole() | range: mem.window(off, size)")
        print("  query by resonance: mem.resonate(input_bytes) -> (key, bytes)")
