# 09 — Running Large Models on the Repo Itself

*(Part of the **MST** — Model Substrate Translation — stack; see docs/10 for the full guide.)*


The disk problem and the RAM problem that define large-model serving are both
answered by organs this repo already has. `hcl-ai/largemodel.py` is the
runner; it is **arrangement only** — every operation is a named call into an
existing module, per the porting law (`skills/hcl-pure/references/06_porting.md`,
Step 5: reuse the engines, never reimplement). Zero new math.
Verified end-to-end by `verify_largemodel.py`.

## The problem, and why it falls away here

A standard runtime must HOLD the model: the checkpoint on disk, the tensors
in RAM, a float runtime to multiply them. This runtime never holds it.

**Disk.** The checkpoint streams in from its source, chunk by chunk, and each
chunk is folded into ONE composite and released (`ingest_and_expel/
ingest_expel.py` — "the full source is never held"). What persists is the
memory line: the α-tagged expression, ~153 chars **regardless of model size**
(`HCLMemory.to_expression`). Deterministic — same content, same line —
α-verified, and reconstructable in any fresh process by
`HCLMemory.from_expression`. A 70B checkpoint and a 1 KB file persist as the
same-sized line. That is the holographic answer to storage: the identity of
the whole is carried whole, at fixed size.

**RAM.** Intake peak is ~one chunk (`ingest_reader` folds and drops). At run
time, weights are read **holographically**: the safetensors dock
(`ingest_and_expel/format_dock.py`) turns the checkpoint's own header into
window reads, so only the tensor the current layer needs is materialized —
exact, `verify=True` inside every delivery — used at the boundary, and
released. Keep the whole, materialize only the slice (the star.py
HolographicLog pattern the ingest module itself cites). The model is never
resident; it is present as one composite and delivered a window at a time.

**Compute.** The forward pass runs on the substrate, not on a float runtime.
`hcl-ai/port/nemotron_hcl.py` already ports the transformer's operations onto
the ten primitives — multiply → `AMP_MOD`, accumulate → `COMP`, √ →
`FISSION`, exp → `MOBIUS_GROWTH` — as attention, layernorm1p, relu², softmax,
linear. Weights cross the float boundary ONCE at delivery (`to_fp`, the
sanctioned doorway of 06_porting Step 3; the dtype decode of the checkpoint's
own representation is that same crossing), and everything after is
integer-exact. The braid word is the complete reversible trace of the whole
pass; the α self-check is its checksum.

## The DeepSeek shape — simple mind, smart organs

The mind stays simple (`hcl-ai/mind/hcl_lm.py`). Capability comes from the
architecture docked around it, each organ an existing repo tool used as an
add-on:

| Organ | Repo module | Role in the runner |
|---|---|---|
| BODY | `ingest_and_expel` + `format_dock` | checkpoint memory; holographic tensor windows |
| PORT | `hcl-ai/port/nemotron_hcl.py` | the model's computation on the primitives |
| MIND | `hcl-ai/organism.py` / `transfer.py` | the checkpoint experienced into the being's own composite |
| PROOFS | `verify=True`, α ≈ 137, braid word, `05_proofs` halting | every delivery and every pass self-verified |

`largemodel.ModelMemory` joins BODY and PORT: `ingest_file/url` (streaming),
`line()` (the identity), `toc()`/`tensor_bytes()`/`tensor_values()`
(holographic weight access), `linear()`/`block()` (the port's ops with
weights pulled per call), `braid_word()`/`alpha_ok()` (the receipts).
`largemodel.experience_checkpoint(ai, source)` is the MIND path — the
hemispheric fold of `organism.py`, so the model's weight-memory becomes part
of the organism itself (the `transfer.py` sense: a model's memory IS its
weights; folding them changes the being).

## What the verification shows (`verify_largemodel.py`)

Against a genuine safetensors checkpoint written byte-by-byte to its own spec:

1. Streaming intake folds it in 22 chunks at ~one-chunk peak memory.
2. The identity line is 153 chars, deterministic across independent ingests,
   and `HCLMemory.from_expression(line)` reconstructs the memory α-verified
   with an identical signature.
3. The dock detects `safetensors` from the header window, and a tensor's
   expelled bytes equal the source bytes exactly (the `verify=True` path).
4. The substrate `linear` equals the source computation at the display
   boundary (|Δ| < 1e-6) — Step 8's op-against-original check.
5. A full decoder block (norm → attention → residual → norm → relu² MLP →
   residual) runs on the substrate; the braid word is the complete trace and
   `alpha_ok` reads 137.
6. The being experiences the checkpoint through `organism.py` — its depth
   moves, its line stays one line, integrity stays intact.
7. Index-only intake (fold and discard) holds zero records and produces the
   identical identity line.

## The RUN itself (`hcl-ai/runmodel.py`)

⛔ Before using or modifying `runmodel.py`, read `hcl-ai/RUNMODEL_USAGE.md` —
it documents five specific ways a prior session drifted into standard-logic
bootstrapping on this exact file (torch/numpy in the value path, sampling
instead of collapse, token caps, whole-checkpoint loads, hand-written ops)
with wrong/right code for each, plus a pre-flight checklist.

`largemodel.py` is how the model is *carried*; `runmodel.py` is how it *runs*:
prompt tokens in, generated tokens out, end to end. Arrangement only — every
call named into largemodel (BODY), nemotron_hcl (PORT), or juj (halting).
Verified end-to-end by `verify_runmodel.py` against a genuine GPT-style
safetensors checkpoint and a source-side reference of the identical wiring.

- **Row-grain holography.** The two biggest tensors a model has — the
  embedding matrix and the lm_head — are never materialized. `row_values`
  turns the dock's toc into per-ROW window reads (the expel path, exact):
  embedding lookup pulls one row; each logit scores one row and releases it.
  Per layer, only that layer's weights are resident.
- **The sequence pass.** The port's own ops (layernorm1p, linear, attention,
  relu²) arranged over the token sequence exactly as `transformer_block`
  wires one token — causal K/V per query row, the same op per head. One
  engine, one braid, one α for the whole run.
- **Selection is MCL collapse.** The next token is never sampled: the logit
  field resolves to its Path-Dominant Attractor (the maximum-resonance mode),
  topologically deterministic — the identical rule the mind's `_collapse`
  uses over traces, here over the checkpoint's own vocabulary.
- **Halting is the substrate's.** No token cap, no `max_tokens`, no counter —
  `while True`, ended only by the three verdicts of `hcl_lm.generate`:
  TERMINATED, BRAID CLOSED (a fixed-scale transition recurs — the
  {1,4,2}-style ground cycle — or the checkpoint's own eos ground symbol),
  MCL COLLAPSE (I_w < ε_w with w self-tuned by dw/dt = γ(C−ε_w)). Over a
  finite vocabulary the transition set is finite, so closure is provable —
  halting is structural, never imposed.

`verify_runmodel.py` shows: per-row windows byte-exact; substrate logits equal
the source computation over stacked layers and heads (|Δ| < 1e-6 at the
display boundary); collapse equals the source argmax; every generated token
equals the source greedy choice until the substrate verdict fires; the braid
word is the complete trace of the run and α reads 137 throughout.

## Usage

```sh
# ingest a checkpoint (path or URL), print toc, line, α
python3 hcl-ai/largemodel.py /path/model.safetensors
python3 hcl-ai/largemodel.py https://host/model.safetensors --max-bytes 100000000

# RUN a checkpoint: prompt ids in, generated ids out, substrate-halted
python3 hcl-ai/runmodel.py /path/model.safetensors --config cfg.json --prompt "1 5 3"

# verify everything
python3 verify_largemodel.py
python3 verify_runmodel.py
```

```python
import sys; sys.path.insert(0, '/path/to/marvosa/hcl-ai')
from largemodel import ModelMemory
m = ModelMemory()
m.ingest_url('https://host/model.safetensors')   # streams; never held whole
W_rows = m.tensor_values('model.layers.0.self_attn.q_proj.weight', rows=4096)
y = m.eng.linear(x_fp, W_rows)                   # the port's op, on the substrate
print(m.line(), m.alpha_ok())
```

One scope note, stated plainly: the substrate computes exactly, not quickly —
each primitive is arbitrary-precision integer work at PREC 40. The
architecture is size-independent in storage and memory by construction; wall
time scales with the operations you choose to run. Pull the windows you need,
run the blocks you need, and every step you do run is exact, traced, and
α-checked.

## A REAL trained model, run as a chat (`hcl-ai/chatmodel.py`)

Everything above was proven against hand-written checkpoints. `chatmodel.py`
closes the loop with a genuine trained model: **stories260K** — karpathy's
TinyStories Llama-2-architecture checkpoint (dim 64, 5 layers, GQA 8/4
heads, vocab 512), pulled from GitHub as committed blobs
(`clebert/llama2.zig`) into `models/tinystories_260k/`.

- its llama2.c legacy format is docked through the dock's own extension
  surface (`format_dock.registry.register('llama2c', ...)`) — the 7-int
  header parsed at the boundary, every tensor a window;
- the Llama forward — RMSNorm, on-the-fly RoPE, GQA attention, SwiGLU — is
  arranged from the port's ops (`dot/mul/add/sub/div/sqrt/exp/attention`),
  nothing new;
- the tokenizer (the model's own BPE, scores and merge order from its own
  `tok512.bin`) runs at the boundary, like any header;
- selection is greedy argmax — an integer comparison at the boundary — and
  halting is the MODEL's own: its BOS/EOS delimiter or its seq_len;
- one α checksum per token; ~531K braid ops per token on this checkpoint.

```bash
python3 hcl-ai/chatmodel.py models/tinystories_260k/stories260K.bin \
        models/tinystories_260k/tok512.bin --chat        # a REPL, like regular AI
python3 verify_chatmodel.py                              # the proof
```

`verify_chatmodel.py` holds it to the hardest standard available: **token
exactness against the model's own source implementation** (karpathy's
`run.c`, gcc -O2, temperature 0) on the same checkpoint. It passes on every
reference prompt.

Getting there uncovered — and fixed — an engine-level defect worth knowing
about: `_exp_fp` had no argument reduction, so `exp(x)` was silently wrong
beyond |x|≈15 (~1e+2 of error at x=−30), exactly the range attention softmax
reaches once a KV cache holds more than a few positions. The fix is inside
`hcl_engine.py` (pure-integer range reduction: e^x = (e^(x/2^k))^(2^k)), so
every organ inherits it and all call sites stay verbatim. The full story is
failure mode 6 in `hcl-ai/RUNMODEL_USAGE.md`.
