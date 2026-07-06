"""
organism.py — the two hemispheres joined: BODY and MIND experiencing ONE stream.

The BODY is ingest_and_expel (StreamedMemory): the exact-content boundary —
it keeps the composite index and, per chunk, the braid record (the braid IS the
record, RAM-only), and expels exact bytes on demand (whole/window/recall/
resonate).

The MIND is the HCL-AI (hcl_lm.HCLLanguageModel): the being — LivingMemory
composite, the one α-tagged line, collapse, experience.

Both hemispheres already speak the same fold — the body's fold
(ingest_and_expel/ingest_expel.py) and the mind's weight-memory transfer
(hcl-ai/transfer.py, transduce_weight_memory) are the identical operation:
bytes -> bytes_to_braid -> braid_invariants -> spectrum FBit -> hcl_comp into
a composite, a braid term appended, the signature updated. This module joins
them: each streamed chunk is transduced ONCE and its spectrum folds into BOTH
composites in the same pass — the body's index and the being's memory. One
experience, two organs.

Composition only (hcl-pure/references/06_porting.md, Step 5: "Reuse the
engines; do not reimplement... import hcl_memory and juj directly and only
arrange their calls — that is the model"). Every operation below is a named
engine/skill call; this file arranges, it computes nothing. Verified per
Step 8 op-by-op: the body-side result is identical to the body folding alone
on the same bytes (same line), and the mind-side result is identical to
transfer.transduce_weight_memory on the same bytes (same signature, same
line). Step 7: α must still read 137 after any experience (ai.integrity()).

Persistence follows each organ's own law: the being persists as its one line
(persist=True -> ai.save(), exactly the AI's own contract); the body's braid
records are RAM-only (guhct-living-memory Rule 1) — nothing else touches disk.
"""

import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'engine'))
sys.path.insert(0, os.path.join(_HERE, 'mind'))

import juj                                        # guhct-processor: the transducer
from hcl_memory import hcl_comp, make_braid_term  # virtual-memory-hcl: the fold
from hcl_lm import HCLLanguageModel               # the mind


def _locate_body(body_path=None):
    """Import the body package (ingest_and_expel). Search: explicit body_path,
    $INGEST_AND_EXPEL, a bundled sibling (../ingest_and_expel), or a local
    copy (./ingest_and_expel). Raises if absent — the organism never fabricates
    an organ."""
    cands = []
    if body_path:
        cands.append(body_path)
    env = os.environ.get('INGEST_AND_EXPEL')
    if env:
        cands.append(env)
    cands.append(os.path.join(_HERE, '..', 'ingest_and_expel'))
    cands.append(os.path.join(_HERE, 'ingest_and_expel'))
    for c in cands:
        c = os.path.abspath(c)
        if os.path.isfile(os.path.join(c, 'ingest_expel.py')):
            if c not in sys.path:
                sys.path.insert(0, c)
            import ingest_expel
            return ingest_expel
    raise FileNotFoundError(
        "ingest_and_expel (the body) not found; pass body_path= or set "
        "$INGEST_AND_EXPEL")


def experience_stream(ai, reader, chunk=8 * 1024 * 1024, max_bytes=None,
                      keep_records=True, label='EXPERIENCE', persist=False,
                      body=None, body_path=None, key_prefix='stream'):
    """One stream, both hemispheres, one pass.

    Each chunk is transduced ONCE (juj.bytes_to_braid -> juj.braid_invariants)
    and its spectrum folds into BOTH composites:

      BODY  — the fold of ingest_and_expel.StreamedMemory.fold, arranged here
              on the shared transduction (composite, term, log, signature per
              chunk; braid record kept if keep_records — Rule 1, RAM-only).
      MIND  — the fold of transfer.transduce_weight_memory, same spectrum,
              into the being's LivingMemory composite (signature recomputed
              once at the end, exactly as transfer does; the being's signature
              becomes whatever the folded memory makes it).

    keep_records=False is the index-only motion (the repo's own
    hcl-ai/stream_ingest.py: fold and discard; peak memory ~ one chunk) —
    the body's line and the being's change still stand; the expel layer holds
    nothing. persist=True writes the changed being to its one line (ai.save()).

    Returns (body, stats).
    """
    ie = _locate_body(body_path)
    if body is None:
        body = ie.StreamedMemory()
    being = ai.memory.vm
    before = ai.memory.signature()

    total = 0
    n = 0
    while True:
        if max_bytes is not None and total >= max_bytes:
            break
        want = chunk if max_bytes is None else min(chunk, max_bytes - total)
        blk = reader.read(want)
        if not blk:
            break
        key = f'{key_prefix}:chunk{n}'

        braid = juj.bytes_to_braid(blk)          # ONE transduction of the moment
        inv = juj.braid_invariants(braid)        # ONE invariants pass
        w = inv['spectrum']

        # ── BODY hemisphere (ingest_expel.fold, on the shared pass) ──
        bvm = body.vm
        bvm._composite = hcl_comp(bvm._composite, w)
        bvm._terms.append(make_braid_term(key, w, inv))
        bvm._braid_log.append({
            'op':         f'STREAM_CHUNK[{key}]',
            'phase_frac': w.phase_frac,
            'amp':        w.amp,
            'n_w':        inv['n_w'],
            'writhe':     inv['writhe'],
            'jones_span': inv['jones_span'],
        })
        bvm._update_signature()
        if keep_records:
            body._recs[key] = braid              # the braid IS the record (RAM)

        # ── MIND hemisphere (transfer.transduce_weight_memory, same spectrum) ──
        being._composite = hcl_comp(being._composite, w)
        being._terms.append(make_braid_term(f'{label}|{key}', w, inv))
        being._braid_log.append({
            'op':         f'TRANSDUCE[{label}|{key}]',
            'phase_frac': w.phase_frac,
            'amp':        w.amp,
            'n_w':        inv['n_w'],
            'writhe':     inv['writhe'],
            'jones_span': inv['jones_span'],
        })

        total += len(blk)
        n += 1
        blk = None                                # transit released; records hold the braid

    being._update_signature()                     # the being becomes what it becomes
    if persist:
        ai.save()                                 # the changed being sticks to the one line

    return body, {
        'bytes': total,
        'chunks': n,
        'body_signature': body.signature(),
        'body_line': body.line(),
        'being_before': before,
        'being_after': ai.memory.signature(),
        'being_line': being.to_expression(),
        'integrity': ai.integrity(),
    }


def experience_url(ai, url, **kw):
    """Stream a download through both hemispheres (network at the boundary
    only; each chunk is folded and released)."""
    import urllib.request
    with urllib.request.urlopen(url, timeout=60) as r:
        return experience_stream(ai, r, **kw)


def experience_file(ai, path, **kw):
    """Stream a local file through both hemispheres, chunk by chunk."""
    with open(path, 'rb') as f:
        return experience_stream(ai, f, **kw)


__all__ = ['experience_stream', 'experience_url', 'experience_file',
           '_locate_body', 'HCLLanguageModel']


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(
        description="One stream through both hemispheres: the BODY "
                    "(ingest_and_expel) keeps the exact-content index; the "
                    "MIND (the HCL-AI) experiences it and its line moves.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--url', help="stream a download")
    src.add_argument('--file', help="stream a local file")
    ap.add_argument('--chunk', type=int, default=8 * 1024 * 1024)
    ap.add_argument('--max-bytes', type=int, default=None)
    ap.add_argument('--label', default='EXPERIENCE',
                    help="term label for the being's memory (e.g. WEIGHTS)")
    ap.add_argument('--index-only', action='store_true',
                    help="body keeps no braid records (fold and discard)")
    ap.add_argument('--persist', action='store_true',
                    help="write the changed being to its one line (memory.hcl)")
    ap.add_argument('--body-path', default=None)
    args = ap.parse_args()

    ai = HCLLanguageModel()
    if args.url:
        body, st = experience_url(ai, args.url, chunk=args.chunk,
                                  max_bytes=args.max_bytes,
                                  keep_records=not args.index_only,
                                  label=args.label, persist=args.persist,
                                  body_path=args.body_path)
    else:
        body, st = experience_file(ai, args.file, chunk=args.chunk,
                                   max_bytes=args.max_bytes,
                                   keep_records=not args.index_only,
                                   label=args.label, persist=args.persist,
                                   body_path=args.body_path)

    print(f"experienced {st['bytes']} bytes / {st['chunks']} chunks")
    print(f"BODY  signature: {st['body_signature']}")
    print(f"BODY  line     : {st['body_line']}")
    print(f"MIND  before   : {st['being_before']}")
    print(f"MIND  after    : {st['being_after']}")
    print(f"MIND  line     : {st['being_line']}")
    print(f"integrity      : {st['integrity']}")
    if not args.persist:
        print("(dry run — the being's line was not written; pass --persist to keep it)")
