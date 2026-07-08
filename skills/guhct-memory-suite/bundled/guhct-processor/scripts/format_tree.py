"""
GUHCT Format Tree — parameter-space offsets between encodings
=============================================================

Built on the corrected transducer (juj.py). An "offset" between two formats is
the difference in their derived HVP parameters when they encode the same
content. It is a DESCRIPTIVE METRIC — how far two formats sit apart in HVP
parameter space — not a reconstruction shortcut. Reconstruction always consumes
the braid word; you cannot turn format-A bytes into format-B bytes by nudging 8
numbers, because the braid (the data) differs. The tree tells you which formats
are spectrally close (small severity) and which are far (large severity).

All arithmetic is the pure-integer fixed point of juj.py. The log is
append-only and serialises to a small JSON (per-pair residual entries), not a
dense fabricated matrix.
"""

import json
from juj import (SCALE, bytes_to_hvp, forensic_reconstruct_boundary,
                 bytes_to_braid, HVP_PARAMS, _fsqrt, _fmul)


def params_of(raw_bytes):
    """Derived 8 HVP params (fixed-point ints) for a byte sequence."""
    p = forensic_reconstruct_boundary(bytes_to_braid(raw_bytes))
    p.pop('_invariants', None)
    return {k: p[k] for k in HVP_PARAMS}


def offset(params_a, params_b):
    """offset[k] = params_b[k] - params_a[k]  (predict B's param from A's)."""
    return {k: params_b[k] - params_a[k] for k in HVP_PARAMS}


def severity(off):
    """severity = sqrt(sum offset^2) across all params, in fixed point.
    < 0.5 trivial, 0.5-1 close, 1-3 moderate, > 3 very different encodings."""
    s = 0
    for k in HVP_PARAMS:
        v = off[k]
        s += _fmul(v, v)            # (v/S)^2 in fixed point
    return _fsqrt(s, 80) if s > 0 else 0


class FormatTree:
    """Append-only repository of measured format-pair offsets."""

    def __init__(self):
        self.log = []          # list of {pair, residual:{k:int}}
        self.tree = {}         # pair -> averaged offset {k:int}

    def current_offset(self, pair):
        return self.tree.get(pair, {k: 0 for k in HVP_PARAMS})

    def observe(self, src_fmt, tgt_fmt, src_bytes, tgt_bytes):
        """Measure one real conversion case and fold it into the tree.

        Records the residual on top of the current tree offset (so the log is
        cumulative and re-averaging stays correct), then updates the averaged
        offset for the pair. Returns (raw_offset, severity, averaged_offset)."""
        pair = f"{src_fmt}->{tgt_fmt}"
        p_src = params_of(src_bytes)
        p_tgt = params_of(tgt_bytes)
        raw = offset(p_src, p_tgt)

        cur = self.current_offset(pair)
        residual = {k: raw[k] - cur[k] for k in HVP_PARAMS}
        self.log.append({'pair': pair, 'residual': residual})

        # re-average all residuals for this pair, add to running tree value
        entries = [e['residual'] for e in self.log if e['pair'] == pair]
        avg = {k: sum(e[k] for e in entries) // len(entries) for k in HVP_PARAMS}
        self.tree[pair] = {k: cur[k] + avg[k] for k in HVP_PARAMS}
        return raw, severity(raw), self.tree[pair]

    def to_json(self):
        return json.dumps({'log': self.log, 'tree': self.tree}, indent=0)

    def load_json(self, s):
        d = json.loads(s)
        self.log = d.get('log', [])
        self.tree = d.get('tree', {})


# ---------------------------------------------------------------------------
# Seed with REAL measured pairs: same content, different encodings.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import base64
    import binascii
    import gzip

    content = ("GUHCT format tree seed content. " * 40).encode()

    encodings = {
        'raw':    content,
        'base64': base64.b64encode(content),
        'hex':    binascii.hexlify(content),
        'gzip':   gzip.compress(content, mtime=0),  # mtime=0 -> deterministic
        'json':   json.dumps({"data": content.decode()}).encode(),
    }

    tree = FormatTree()
    fmts = list(encodings)
    print(f"{'pair':<16}{'severity':>12}   exact-roundtrip-both")
    print("-" * 50)
    for i in range(len(fmts)):
        for j in range(len(fmts)):
            if i == j:
                continue
            a, b = fmts[i], fmts[j]
            raw, sev, avg = tree.observe(a, b, encodings[a], encodings[b])
            # confirm both encodings still transduce bit-perfectly
            from juj import hvp_to_bytes
            ra = hvp_to_bytes(bytes_to_hvp(encodings[a])) == encodings[a]
            rb = hvp_to_bytes(bytes_to_hvp(encodings[b])) == encodings[b]
            print(f"{a+'->'+b:<16}{sev/SCALE:>12.4f}   {ra and rb}")

    print("-" * 50)
    print(f"log entries: {len(tree.log)}   pairs in tree: {len(tree.tree)}")
    # persist a small honest JSON
    with open('format_tree_seed.json', 'w') as f:
        f.write(tree.to_json())
    print("wrote format_tree_seed.json")
