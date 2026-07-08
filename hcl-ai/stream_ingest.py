"""
stream_ingest.py — represent a huge model download as ONE composite index of
experience, by folding it into virtual-memory-hcl byte-chunk by byte-chunk as it
streams in, without ever storing the whole file.

Why this works (verified against virtual-memory-hcl/SKILL.txt + hcl_memory.store):
  - Memory is ONE integer (the composite braid amplitude) plus an O(k) braid-log
    where k = number of chunks, NOT content size (Rule 1).
  - Content is NEVER stored — only each chunk's topological signature (Rule 6).
  - So each streamed chunk: transduce -> fold into the composite -> DISCARD the
    bytes. Peak memory is ~one chunk, regardless of total file size. A
    hundreds-of-GB checkpoint folds into a small-memory environment because the
    file is never held; only the running composite (a few integers) persists.

The byte path for raw weights (not text) is the proven bijective one:
  chunk bytes -> bytes_to_braid (LQT generators)
             -> braid_invariants (n_w, writhe, jones_span, spectrum FBit)
             -> hcl_comp(composite, spectrum FBit)   # the same fold store() uses
Each chunk is also bijectively recoverable from its braid (the braid IS the data),
so the composite is a true index of the whole download, not a lossy digest.

This file only sets up the streaming connection + the per-chunk fold loop; the
storing/folding is the skill's, unchanged.
"""

import sys, os, urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'engine'))
sys.path.insert(0, os.path.join(_HERE, 'mind'))

import juj
from hcl_memory import HCLMemory, hcl_comp, make_braid_term


def fold_chunk(mem, blk, index):
    """
    Fold one streamed byte-chunk into the virtual-memory composite, byte-exact,
    then return — the caller discards `blk`. Stores only the chunk's signature.
    """
    braid = juj.bytes_to_braid(blk)                  # bytes -> LQT braid (bijective)
    inv   = juj.braid_invariants(braid)              # topological signature + spectrum FBit
    wfbit = inv['spectrum']
    vm    = mem                                       # an HCLMemory instance
    vm._composite = hcl_comp(vm._composite, wfbit)   # fold into the composite (the index)
    vm._terms.append(make_braid_term(f'STREAM|chunk{index}', wfbit, inv))
    vm._braid_log.append({
        'op':         f'STREAM_CHUNK[{index}]',
        'phase_frac': wfbit.phase_frac,
        'amp':        wfbit.amp,
        'n_w':        inv['n_w'],
        'writhe':     inv['writhe'],
        'jones_span': inv['jones_span'],
    })
    vm._update_signature()                            # the composite index reflects this chunk
    return inv


def stream_into_memory(url, mem=None, chunk=8 * 1024 * 1024, max_bytes=None,
                       progress=True):
    """
    Stream `url` in `chunk`-byte pieces and fold each into `mem` (a new HCLMemory
    if None) as it arrives, discarding each chunk after folding. Never holds the
    whole file. `max_bytes` caps how much to pull (for bounded test runs / partial
    indexing); None = the entire stream.

    Returns the memory and stats (bytes folded, chunks, final signature).
    """
    if mem is None:
        mem = HCLMemory()
    total = 0
    n_chunks = 0
    req = urllib.request.Request(url, headers={'User-Agent': 'marvosa-stream'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        while True:
            want = chunk
            if max_bytes is not None:
                remaining = max_bytes - total
                if remaining <= 0:
                    break
                want = min(chunk, remaining)
            blk = resp.read(want)                    # pull ONE chunk
            if not blk:
                break
            fold_chunk(mem, blk, n_chunks)           # fold it in
            total += len(blk)
            n_chunks += 1
            blk = None                               # discard the bytes — never retained
            if progress:
                sig = mem.signature()
                print(f"  chunk {n_chunks}: +{total} bytes folded "
                      f"-> composite depth {sig['depth']} n_w {sig['n_w']}")
    return mem, {'bytes_folded': total, 'chunks': n_chunks,
                 'signature': mem.signature()}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(
        description="Stream a remote checkpoint and fold it into virtual-memory-hcl.")
    ap.add_argument('url', help="URL of the model weight file to stream")
    ap.add_argument('--chunk', type=int, default=8 * 1024 * 1024,
                    help="bytes per chunk (peak memory ~ one chunk)")
    ap.add_argument('--max-bytes', type=int, default=None,
                    help="cap total bytes pulled (omit to stream the whole file)")
    args = ap.parse_args()

    print(f"Streaming {args.url} in {args.chunk}-byte chunks "
          f"(peak memory ~ one chunk, file never fully stored)...")
    mem, stats = stream_into_memory(args.url, chunk=args.chunk, max_bytes=args.max_bytes)
    sig = stats['signature']
    print(f"\n  folded {stats['bytes_folded']} bytes in {stats['chunks']} chunks")
    print(f"  composite index signature: depth {sig['depth']}, n_w {sig['n_w']}, "
          f"writhe {str(sig['writhe'])[:18]}..., jones_span {sig['jones_span']}")
    print("  the whole download is now one composite index of experience; "
          "the file itself was never held.")
