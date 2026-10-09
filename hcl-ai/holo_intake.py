"""
holo_intake.py — MST: holographic intake of ANY checkpoint (any size) into
ONE alpha-tagged identity line, with on-demand tensor windows. The call
path is size-blind: a 1MB toy and a multi-GB billion-parameter body take
the same road (streaming chunks; RAM bounded; the line stays ~150 chars).

    python3 hcl-ai/holo_intake.py <checkpoint> [--chunk BYTES] [--window TENSOR]

Formats: safetensors natively; llama2c once chatmodel (its dock registrar)
is imported — which this script does. See docs/09, docs/10, docs/12.
"""
import sys, os, time, argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, 'engine'), os.path.join(_HERE, 'port')):
    sys.path.insert(0, _p)

import chatmodel                      # registers the llama2c dock handler
from largemodel import ModelMemory


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('checkpoint')
    ap.add_argument('--chunk', type=int, default=1024 * 1024)
    ap.add_argument('--window', default=None,
                    help='tensor name to materialize as a demo window')
    a = ap.parse_args()
    size = os.path.getsize(a.checkpoint)
    print(f"[intake] {a.checkpoint}  ({size/1e6:.1f} MB) — streaming, "
          f"RAM-bounded, chunk={a.chunk}")
    t0 = time.time()
    mm = ModelMemory(chunk=a.chunk)
    mm.ingest_file(a.checkpoint)
    dt = time.time() - t0
    line = mm.line()
    print(f"[identity] ONE line, {len(line)} chars, alpha_ok={mm.alpha_ok()} "
          f"({dt:.0f}s, {size/1e6/max(dt,1e-9):.2f} MB/s)")
    print(f"[line] {line}")
    toc = mm.toc()
    print(f"[toc] {len(toc)} tensors read from the header window only")
    name = a.window or toc[min(2, len(toc) - 1)]['name']
    t1 = time.time()
    v = mm.tensor_values(name)
    n = sum(len(r) if isinstance(r, list) else 1 for r in v) \
        if isinstance(v, list) else len(v)
    v2 = mm.tensor_values(name)
    print(f"[window] {name!r}: {n} values in {time.time()-t1:.1f}s; "
          f"re-materialized bit-identical: {v == v2}")
    print("[[DONE — the same road carries a billion]]")


if __name__ == '__main__':
    main()
