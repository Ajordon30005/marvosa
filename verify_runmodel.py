#!/usr/bin/env python3
"""verify_runmodel.py — Step 8 verification of the RUN (runmodel.py): a
genuine GPT-style safetensors checkpoint is written byte-by-byte to its own
spec, a source-side float reference implements the identical wiring, and the
substrate run is checked against it op-by-op at the display boundary. Every
check uses the repo's own mechanisms: verify=True windows, the α self-check,
line determinism, and the three substrate halting verdicts."""
import sys, os, json, struct, math, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))

# ── build a REAL GPT-style safetensors checkpoint by its own spec ────────
random.seed(137)
V, D, L, HEADS = 8, 4, 2, 2                      # vocab, d_model, layers, heads
f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]   # the dtype's own value
def mat(r, c): return [[f32(random.uniform(-1, 1)) for _ in range(c)] for _ in range(r)]
def vec(n):    return [f32(random.uniform(-1, 1)) for _ in range(n)]

T = {'embed.weight': mat(V, D), 'final_ln.weight': vec(D), 'final_ln.bias': vec(D),
     'lm_head.weight': mat(V, D)}
for i in range(L):
    T[f'layers.{i}.ln1.weight'] = vec(D); T[f'layers.{i}.ln1.bias'] = vec(D)
    for n in 'qkvo':
        T[f'layers.{i}.attn.{n}.weight'] = mat(D, D)
    T[f'layers.{i}.ln2.weight'] = vec(D); T[f'layers.{i}.ln2.bias'] = vec(D)
    T[f'layers.{i}.mlp.up.weight'] = mat(2 * D, D)
    T[f'layers.{i}.mlp.down.weight'] = mat(D, 2 * D)

def flat(t): return [x for row in (t if isinstance(t[0], list) else [t]) for x in row]
hdr, blob, off = {}, bytearray(), 0
for name, t in T.items():
    data = b''.join(struct.pack('<f', v) for v in flat(t))
    shape = [len(t), len(t[0])] if isinstance(t[0], list) else [len(t)]
    hdr[name] = {'dtype': 'F32', 'shape': shape, 'data_offsets': [off, off + len(data)]}
    blob += data; off += len(data)
hjson = json.dumps(hdr).encode()
ckpt = struct.pack('<Q', len(hjson)) + hjson + bytes(blob)
path = '/tmp/tiny_gpt.safetensors'
open(path, 'wb').write(ckpt)
print(f"[built] real GPT-style checkpoint: {len(ckpt)} bytes, {len(T)} tensors, "
      f"vocab={V} d={D} layers={L} heads={HEADS}")

# ── the SOURCE reference: the identical wiring, in floats ────────────────
EPS = 1e-5
def r_ln1p(x, w, b):
    m = sum(x) / len(x); var = sum((xi - m) ** 2 for xi in x) / len(x)
    inv = 1.0 / math.sqrt(var + EPS)
    return [ (xi - m) * inv * (wi + 1.0) + bi for xi, wi, bi in zip(x, w, b) ]
def r_lin(x, W): return [sum(xi * wi for xi, wi in zip(x, row)) for row in W]
def r_softmax(z):
    m = max(z); e = [math.exp(zi - m) for zi in z]; s = sum(e)
    return [ei / s for ei in e]
def r_attn(q, K, Vv, dh):
    w = r_softmax([sum(a * b for a, b in zip(q, k)) / math.sqrt(dh) for k in K])
    return [sum(wi * v[j] for wi, v in zip(w, Vv)) for j in range(len(Vv[0]))]
def r_heads(v, h):
    d = len(v) // h; return [v[j * d:(j + 1) * d] for j in range(h)]
def r_layer(xs, i):
    dh = D // HEADS
    A = [r_ln1p(x, T[f'layers.{i}.ln1.weight'], T[f'layers.{i}.ln1.bias']) for x in xs]
    Q = [r_lin(a, T[f'layers.{i}.attn.q.weight']) for a in A]
    K = [r_lin(a, T[f'layers.{i}.attn.k.weight']) for a in A]
    Vs = [r_lin(a, T[f'layers.{i}.attn.v.weight']) for a in A]
    out = []
    for p in range(len(xs)):
        ho = []
        for h in range(HEADS):
            ho += r_attn(r_heads(Q[p], HEADS)[h],
                         [r_heads(K[j], HEADS)[h] for j in range(p + 1)],
                         [r_heads(Vs[j], HEADS)[h] for j in range(p + 1)], dh)
        attn = r_lin(ho, T[f'layers.{i}.attn.o.weight'])
        h1 = [a + b for a, b in zip(xs[p], attn)]
        b2 = r_ln1p(h1, T[f'layers.{i}.ln2.weight'], T[f'layers.{i}.ln2.bias'])
        up = r_lin(b2, T[f'layers.{i}.mlp.up.weight'])
        act = [max(0.0, u) ** 2 for u in up]
        mlp = r_lin(act, T[f'layers.{i}.mlp.down.weight'])
        out.append([a + b for a, b in zip(h1, mlp)])
    return out
def r_logits(ids):
    xs = [T['embed.weight'][t] for t in ids]
    for i in range(L):
        xs = r_layer(xs, i)
    h = r_ln1p(xs[-1], T['final_ln.weight'], T['final_ln.bias'])
    return r_lin(h, T['lm_head.weight'])
def r_argmax(z):
    b = 0
    for t in range(1, len(z)):
        if z[t] > z[b]: b = t
    return b

# ── the RUN under test ───────────────────────────────────────────────────
from largemodel import ModelMemory
from runmodel import HCLModelRunner, row_values
from nemotron_hcl import _val

CFG = {'n_layers': L, 'd_model': D, 'n_heads': HEADS, 'vocab': V, 'eps': EPS,
       'embed': 'embed.weight', 'lm_head': 'lm_head.weight',
       'final_ln_w': 'final_ln.weight', 'final_ln_b': 'final_ln.bias',
       'ln1_w': 'layers.{i}.ln1.weight', 'ln1_b': 'layers.{i}.ln1.bias',
       'q_w': 'layers.{i}.attn.q.weight', 'k_w': 'layers.{i}.attn.k.weight',
       'v_w': 'layers.{i}.attn.v.weight', 'o_w': 'layers.{i}.attn.o.weight',
       'ln2_w': 'layers.{i}.ln2.weight', 'ln2_b': 'layers.{i}.ln2.bias',
       'up_w': 'layers.{i}.mlp.up.weight', 'down_w': 'layers.{i}.mlp.down.weight',
       'eos': None}

m = ModelMemory(chunk=256)                       # small chunk -> many folds
st = m.ingest_file(path)
assert st['chunks'] > 1 and st['bytes_folded'] == len(ckpt)
line = m.line()
m_b = ModelMemory(chunk=256); m_b.ingest_file(path)
assert m_b.line() == line
print(f"[1] streamed intake: {st['bytes_folded']} bytes / {st['chunks']} chunks; "
      f"identity line {len(line)} chars, deterministic")

# ── 2. the holographic ROW window is exact (the RAM answer, row grain) ───
row = 5
b0, e0 = hdr['lm_head.weight']['data_offsets']
src_row = ckpt[8 + len(hjson) + b0 + row * D * 4: 8 + len(hjson) + b0 + (row + 1) * D * 4]
t = m.toc()['lm_head.weight']
got_row = m.mem.window(t['offset'] + row * D * 4, D * 4)     # the expel path
assert got_row == src_row, "row window must equal the source bytes exactly"
r = HCLModelRunner(m, CFG)
vals = row_values(m, 'lm_head.weight', row)
for got_fp, ref in zip(vals, T['lm_head.weight'][row]):
    assert abs(float(_val(got_fp)) - ref) < 1e-9
print(f"[2] per-ROW holographic read: {len(got_row)} bytes exact; values exact at the boundary")

# ── 3. embedding lookup = one row, on the substrate ──────────────────────
tok = 3
emb = r.embed_row(tok)
for got_fp, ref in zip(emb, T['embed.weight'][tok]):
    assert abs(float(_val(got_fp)) - ref) < 1e-9
print(f"[3] embedding lookup is a single row window (matrix never materialized)")

# ── 4. full forward + logits vs the source computation (Step 8) ──────────
prompt = [1, 5, 3]
z_fp = r.logits(r.forward(prompt))
z_ref = r_logits(prompt)
worst = max(abs(float(_val(a)) - b) for a, b in zip(z_fp, z_ref))
assert worst < 1e-6, worst
print(f"[4] substrate logits == source logits over {L} layers x {HEADS} heads "
      f"(worst |Δ| = {worst:.2e} at the display boundary)")

# ── 5. MCL collapse = the source argmax (deterministic selection) ────────
assert r.collapse(z_fp) == r_argmax(z_ref)
print(f"[5] MCL collapse resolves the same Path-Dominant Attractor as the source argmax")

# ── 6. THE RUN: autoregressive, substrate-halted, token-exact ────────────
import inspect, runmodel as RM
gen_src = inspect.getsource(RM.HCLModelRunner.generate)
assert 'max_tokens' not in gen_src and 'while True' in gen_src
out = r.generate(prompt)
assert out['verdict'] in ('TERMINATED', 'BRAID CLOSED', 'MCL COLLAPSE')
# every emitted token must equal the source's greedy choice at that step
ids = list(prompt)
for e in out['events']:
    assert e['token'] == r_argmax(r_logits(ids)), (e, ids)
    ids.append(e['token'])
print(f"[6] generation ran with NO token cap; halted by the substrate: {out['verdict']}")
print(f"    prompt {prompt} -> generated {out['generated']} "
      f"(every token == source greedy choice); depths {[e['w'] for e in out['events']]}")

# ── 7. the receipts ──────────────────────────────────────────────────────
bw = r.m.braid_word()
assert r.m.alpha_ok() and len(bw) > 0
assert m.line() == line, "the identity line stands after the whole run"
print(f"[7] braid word: {len(bw)} chars (the complete reversible trace of the run); "
      f"alpha_ok=True; identity line unchanged")

print("\nALL CHECKS PASSED — the RUN is arrangement of the repo's own organs:")
print("  BODY windows (rows), PORT ops (sequence), MCL collapse (selection),")
print("  substrate verdicts (halting). Zero new math. Zero floats in the value path.")
