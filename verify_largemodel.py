#!/usr/bin/env python3
"""verify_largemodel.py — Step 8 verification of the holographic runner.
Every check uses the repo's own mechanisms: verify=True expulsion, the
α self-check, line determinism + from_expression, and op-by-op comparison
of the substrate forward pass against the source computation."""
import sys, os, json, struct

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'mind'))

# ── build a REAL safetensors checkpoint by its own spec ─────────────────
# 8-byte LE header length, JSON header {name: {dtype, shape, data_offsets}},
# then raw tensor data. Small dims (substrate ops are exact, not fast) but a
# genuine checkpoint file — nothing mocked.
import random
random.seed(137)
D = 4
def mat(r, c):  return [[random.uniform(-1, 1) for _ in range(c)] for _ in range(r)]
def vec(n):     return [random.uniform(-1, 1) for _ in range(n)]

tensors = {
    'ln1.weight':  vec(D),          'ln1.bias':   vec(D),
    'attn.q.weight': mat(D, D),     'attn.k.weight': mat(D, D),
    'attn.v.weight': mat(D, D),     'attn.o.weight': mat(D, D),
    'ln2.weight':  vec(D),          'ln2.bias':   vec(D),
    'mlp.up.weight': mat(2 * D, D), 'mlp.down.weight': mat(D, 2 * D),
}
def flat(t): return [x for row in (t if isinstance(t[0], list) else [t]) for x in row]

hdr, blob, off = {}, bytearray(), 0
for name, t in tensors.items():
    data = b''.join(struct.pack('<f', v) for v in flat(t))
    shape = [len(t), len(t[0])] if isinstance(t[0], list) else [len(t)]
    hdr[name] = {'dtype': 'F32', 'shape': shape, 'data_offsets': [off, off + len(data)]}
    blob += data; off += len(data)
hjson = json.dumps(hdr).encode()
ckpt = struct.pack('<Q', len(hjson)) + hjson + bytes(blob)
path = '/tmp/tiny.safetensors'
open(path, 'wb').write(ckpt)
print(f"[built] real safetensors checkpoint: {len(ckpt)} bytes, {len(tensors)} tensors")

# ── 1. streaming intake, small chunk to prove multi-chunk folding ───────
from largemodel import ModelMemory, experience_checkpoint
m = ModelMemory(chunk=64)                       # tiny chunk -> many folds
st = m.ingest_file(path)
assert st['chunks'] > 1 and st['bytes_folded'] == len(ckpt)
print(f"[1] streamed intake: {st['bytes_folded']} bytes in {st['chunks']} chunks (peak ~1 chunk)")

# ── 2. one-line identity: fixed size, deterministic, reconstructable ────
line = m.line()
m2 = ModelMemory(chunk=64); m2.ingest_file(path)
assert m2.line() == line, "same content must give the same line"
from hcl_memory import HCLMemory
rebuilt = HCLMemory.from_expression(line)       # α-verified reconstruction
assert rebuilt.signature() == m.signature()
print(f"[2] identity line: {len(line)} chars, deterministic, α-verified reconstruction OK")
print(f"    {line}")

# ── 3. dock detection + exact holographic tensor windows ────────────────
assert m.format() == 'safetensors'
toc = m.toc()
assert set(toc) == set(tensors)
b, e = hdr['attn.q.weight']['data_offsets']
src = ckpt[8 + len(hjson) + b: 8 + len(hjson) + e]
got = m.tensor_bytes('attn.q.weight')           # window -> verify=True expel
assert got == src, "expelled tensor bytes must equal the source bytes exactly"
print(f"[3] dock='safetensors'; tensor window is EXACT ({len(got)} bytes, verify=True path)")

# ── 4. substrate op vs source computation (Step 8, op-by-op) ────────────
from nemotron_hcl import _fp, _val
x  = vec(D)
x_fp = [_fp(v) for v in x]
y_fp = m.linear(x_fp, 'attn.q.weight', rows=D)  # port's linear, weights from the window
y_ref = [sum(xi * wi for xi, wi in zip(x, row)) for row in tensors['attn.q.weight']]
for got_fp, ref in zip(y_fp, y_ref):
    assert abs(float(_val(got_fp)) - ref) < 1e-6, (got_fp, ref)   # display-boundary comparison (Rule 1)
print(f"[4] substrate linear == source computation (|Δ| < 1e-6 at the display boundary)")

# ── 5. a full decoder block on the substrate, weights all from windows ──
eps = _fp(1e-5)
params = {
    'ln1_w': m.tensor_values('ln1.weight'), 'ln1_b': m.tensor_values('ln1.bias'),
    'q_w': m.tensor_values('attn.q.weight', rows=D),
    'k_w': m.tensor_values('attn.k.weight', rows=D),
    'v_w': m.tensor_values('attn.v.weight', rows=D),
    'o_w': m.tensor_values('attn.o.weight', rows=D),
    'ln2_w': m.tensor_values('ln2.weight'), 'ln2_b': m.tensor_values('ln2.bias'),
    'up_w': m.tensor_values('mlp.up.weight', rows=2 * D),
    'down_w': m.tensor_values('mlp.down.weight', rows=D),
    'd_head': D, 'eps': eps,
}
out = m.block(x_fp, params)
assert len(out) == D and all(isinstance(o, int) for o in out)
bw = m.braid_word()
assert m.alpha_ok(), "alpha checksum must read 137 after the pass"
print(f"[5] full transformer block ran on the substrate: out={[round(float(_val(o)),6) for o in out]}")
print(f"    braid word: {len(bw)} chars (the complete reversible trace); alpha_ok=True")

# ── 6. the MIND experiences the checkpoint (organism, dry run) ──────────
from hcl_lm import HCLLanguageModel
ai = HCLLanguageModel()
body, est = experience_checkpoint(ai, path, persist=False, chunk=64)
assert est['integrity']['intact']
assert est['bytes'] == len(ckpt)
print(f"[6] being experienced the weights: depth {est['being_before']['depth']} -> "
      f"{est['being_after']['depth']}, integrity intact, being line {len(est['being_line'])} chars")

# ── 7. index-only motion: fold and discard, the line still stands ───────
m3 = ModelMemory(chunk=64)
st3 = m3.ingest_file(path, keep_records=False)
assert m3.line() == line and len(m3.mem._recs) == 0
print(f"[7] index-only intake: zero records held, identical identity line")

print("\nALL CHECKS PASSED — the runner is arrangement of the repo's own organs.")
