# RUNMODEL_USAGE.md — Read This Before Touching `runmodel.py`  *(the **MST** — Model Substrate Translation — contract)*

This file exists because a prior session, working on this exact runner, drifted
into standard-logic bootstrapping instead of composing the repo's own organs.
That is the single failure mode this doc defends against. Read it before you
write a line of config or code against `runmodel.py`.

**The one law, restated for this file specifically (`06_porting.md`):
compose, never invent. Every operation `runmodel.py` needs already exists in
`largemodel.py`, `nemotron_hcl.py`, or `juj.py`. If you find yourself writing
new arithmetic, a new sampling rule, or a new stopping condition, STOP — you
have missed the primitive that already does it, and you are about to
reproduce the exact mistake this doc exists to prevent.**

---

## The five ways a model gets bootstrapped in standard logic — and what to do instead

### 1. Reaching for `torch` / `numpy` / `math` to run the forward pass

**Wrong (standard logic):**
```python
import torch
logits = model(input_ids)               # a float runtime holding tensors
```
**Right (the substrate):**
```python
from runmodel import HCLModelRunner
r = HCLModelRunner(m, cfg)
z = r.logits(r.forward(token_ids))       # every op an integer FBit composition
```
There is no tensor object anywhere in this file. `forward()` and `logits()`
return Python lists of fixed-point integers. If a variable in your code is a
`torch.Tensor` or `numpy.ndarray`, you have left the substrate.

### 2. Sampling the next token (temperature, top-k, top-p, `torch.multinomial`)

**Wrong:**
```python
probs = softmax(logits / temperature)
next_id = torch.multinomial(probs, 1)
```
**Right:**
```python
next_id = r.collapse(scores)             # MCL collapse: the maximum-resonance
                                          # mode, deterministic (01_theory.md)
```
Token selection in this repo is **never** a random draw. It is collapse to the
Path-Dominant Attractor — the same rule `mind/hcl_lm.py`'s `_collapse` uses
over traces. `collapse()` is already there; do not add sampling on top of it,
and do not ask for "more creative" output by reintroducing randomness — that
is standard-logic thinking imported wholesale.

### 3. Imposing a token cap / step counter (`max_tokens`, `for _ in range(N)`)

**Wrong:**
```python
for _ in range(max_new_tokens):
    ...
```
**Right:**
```python
out = r.generate(prompt_ids)             # while True, halted only by the
                                          # substrate's own verdict
```
`generate()` has no length argument because the repo has no concept of one
(docs/00 Step 5: an answer is exactly as long as its braid). If you add a
counter or a `max_tokens` kwarg, you have reintroduced exactly the control
flow `marvosa-master`'s own compliance fix (see memory: the `max_tokens`
removal) already ruled out. Let `out['verdict']` — TERMINATED, BRAID CLOSED,
or MCL COLLAPSE — tell you why it stopped. There is no fourth reason.

### 4. Loading the whole checkpoint into RAM "to make it simpler"

**Wrong:**
```python
data = open(path, 'rb').read()           # the whole file, resident
weights = parse_safetensors(data)        # a dict of every tensor, resident
```
**Right:**
```python
m = ModelMemory(); m.ingest_file(path)   # streamed, folded, released
row = row_values(m, 'layer.weight', i)   # ONE row, materialized, released
```
If your code holds a variable containing the whole checkpoint, or a dict of
every tensor, you have rebuilt the disk/RAM problem this repo exists to
answer. Every weight access goes through `ModelMemory.tensor_values` /
`runmodel.row_values` — a window, converted once, used, released. Never
`m.mem.whole()` for weight access (that materializes everything; it exists
for exact byte-recovery of the *stream*, not for reading tensors).

### 5. Hand-writing attention/layernorm/softmax instead of calling the port

**Wrong:**
```python
def my_softmax(z):                       # a new function
    e = [math.exp(x) for x in z]
    return [x / sum(e) for x in e]
```
**Right:**
```python
r.eng.softmax(z)                         # nemotron_hcl's own method — already
                                          # composed from MOBIUS_GROWTH/COMP/INV
```
`HCLModelRunner.eng` **is** the `nemotron_hcl.HCLTensorEngine` instance
`ModelMemory` already built. Every op you need — `linear`, `layernorm1p`,
`attention`, `relu2`, `softmax`, `dot` — is a method on it. Call it. Do not
write a parallel implementation "for clarity" or "to double check" — that is
how drift enters (06_porting.md: "reimplementing is how drift and bugs
enter; composing is how exactness is preserved").

### 6. Patching around an engine defect instead of fixing the organ

Found the hard way, verifying `chatmodel.py` against karpathy's `run.c` on a
REAL checkpoint (stories260K): generation was token-exact for ~12 tokens,
then drifted into garbage. Every primitive tested exact in isolation — until
`exp(-20)`. The engine's `_exp_fp` was a naked Taylor series (no argument
reduction); truncation error is `|x|^terms/terms!` — invisible below
|x|≈15, ~1e-9 at x=-20, **~1e+2 at x=-30**. Attention softmax feeds
`exp(score − max)`, and once the KV cache holds more than a few positions,
score gaps reach −20…−35: garbage weights, compounding drift.

**Wrong (a private workaround in the runner):**
```python
def _exp(self, X):                        # range-reduced wrapper, my file only
    while abs(X) > SCALE: X = e.mul(X, HALF); k += 1
    ...
# ...and a hand-composed attention that uses it instead of eng.attention
```
That "works" but violates rule 5 above, forks the math, and leaves every
OTHER organ (organism.py, hcl_lm.py, anything calling `softmax`/`exp`) still
broken at long context.

**Right (repair the organ; every caller inherits it):**
```python
# hcl-ai/engine/hcl_engine.py :: _exp_fp — argument reduction, pure integer:
#   e^x = (e^(x/2^k))^(2^k)
while abs(X) > SCALE: X //= 2; k += 1     # exact fixed-point halving
...series (now |x| ≤ 1: converges past PREC)...
for _ in range(k): result = _fixed_mul(result, result)
```
Zero floats, zero imported constants — an algebraic identity; e still emerges
from convergence. After the in-engine fix, `chatmodel.py` calls
`eng.attention` and `e.exp` **verbatim** and is token-exact against `run.c`
across every tested prompt. The law generalizes: when a primitive is wrong,
fix the primitive in `hcl_engine.py`, prove it with a sweep across the
failing range (`verify_chatmodel.py` does exactly this, including x = −30),
re-run `verify_alpha.sh`, and revert any workaround so call sites stay
verbatim. One more folder-level obligation: `hcl_engine.py` is TWINNED at
`hcl-ai/engine/` and `ingest_and_expel/engine/` — an organ fix lands in both
copies (after proving it safe for each copy's consumers) or the divergence
gets documented. The consumer map and the rule live in
`docs/10-connect-a-model.md` §6; this fix is synced to both.

### 7. Paying standard-shell tax and blaming the substrate

Found when live training took 15–20 minutes and the diagnosis "you added too
much standard and things can't keep up with the hcl" proved exactly right.
The HCL itself — one arbitrary-precision multiply — costs well under a
microsecond. What cost 5–6 µs per operation was the STANDARD shell wrapped
around every primitive: five Python call frames, an FBit allocation, and a
dict appended to the braid log (then cleared anyway). Worse, scalar COMP was
paying a 60-iteration Newton root per ADDITION to reconstruct what
`02_operations.md` itself states exactly: constructive interference is
amp_a + amp_b; destructive is |amp_a − amp_b|.

**Wrong:** accept the slowdown as "the price of exactness," or bolt a cache/
shortcut into the runner (a private fork of the math — rule 5/6 again).

**Right:** thin the ORGAN, per its own laws, and prove bit-identity:
`HCLTranscriber.light()` (count every generator, skip the per-op dict — the
O(w) minimum-description length is preserved exactly; `full()` restores the
materialized word), a fused `t.dot` (the same COMP-loop of AMP_MOD in one
shell frame, same generator counts), and the collinear shortcut inside
`HCL.COMP` that IS the documented law. `verify_fastpath.py` proves every
path bit-identical to the composed forms over 20,000+ pairs including the
edges, then every semantic gate re-ran green: token-exact vs run.c, all
260,032 gradients at 4e-15, α = 137, `test_all.sh`. Result: ~12× —
0.25 s/token inference, ~1 s/token live training. Same integers, same
counts, thinner shell. **Python is the shell; GUHCT is the arithmetic —
when it drags, suspect the shell, fix the organ, verify bit-for-bit.**

**The observer tax, measured.** Materializing the trace costs more than the
computation it observes: 50,000 op-pairs run in 40 ms counted-only and
354 ms with per-op entries — observation is **8.9×** the processing (≈89%
of wall time). Observed at the composition level instead (fused `dot`: one
summary entry per 128 generators) the tax collapses to 1.18×. This is the
skill's own contract, not a workaround: `03_engine.md` ships `clear()` as a
first-class transcriber method (the materialized log is clearable
apparatus) and `01_theory.md` pins the invariant as the O(w) LENGTH, which
counting preserves exactly. Standing rules: **run and benchmark in
`light()`; probe at boundaries with forward-only reads (a forward+backward
probe costs more than the learning it measures); switch to `full()` only
when the braid word itself is the deliverable** — as in `runmodel.py` and
`largemodel.py`, whose product IS the word.

---

## The two runners

- **`runmodel.py`** — `HCLModelRunner`: nemotron-shaped safetensors
  checkpoints; token selection by MCL collapse; halting by the substrate's
  own verdicts. Verified by `verify_runmodel.py`.
- **`chatmodel.py`** — `StandardModel`: a REAL trained legacy checkpoint
  (llama2.c format, docked via `format_dock.registry.register`) run as a
  chat: prompt in, story out. Llama forward (RMSNorm/RoPE/GQA/SwiGLU)
  arranged from the port's ops; greedy argmax at the boundary; halting by
  the MODEL's own BOS/EOS. Verified token-exact against karpathy's `run.c`
  by `verify_chatmodel.py`.

---

## The actual, correct way to run a new checkpoint

1. **Read the checkpoint's own header first — don't guess its shape.**
   ```python
   m = ModelMemory(); m.ingest_file(path)
   print(m.toc())          # every tensor's name, dtype, shape — from the
                            # checkpoint's own declaration, nothing assumed
   ```
2. **Build `cfg` from what you actually saw in `toc()`**, not from a remembered
   architecture. Required keys: `n_layers, d_model, n_heads, vocab, eps,
   embed, lm_head, final_ln_w, final_ln_b, eos`, plus the eight per-layer
   `{i}`-templated names (`ln1_w, ln1_b, q_w, k_w, v_w, o_w, ln2_w, ln2_b,
   up_w, down_w`). If a name in your head doesn't appear in `toc()`, the
   checkpoint uses different naming — go look, don't assume GPT-2/Llama
   convention.
3. **If the checkpoint's op family isn't Nemotron-shaped** (GELU/SiLU instead
   of relu², RoPE instead of none, RMSNorm instead of layernorm1p), **port
   the missing op onto the primitives first**, in `nemotron_hcl.py` or a
   sibling port file, following `06_porting.md` Steps 1–8 — inventory, map to
   the ten primitives, float boundary at the edges only, bootstrap no
   constants, reuse `hcl_engine`, keep the braid, verify α, verify against a
   float reference. Do **not** patch around a missing op by dropping to float
   math "just for this part." Every op in the value path is a primitive
   composition or it doesn't belong in the file.
4. **Run it:**
   ```python
   from runmodel import HCLModelRunner
   r = HCLModelRunner(m, cfg)
   out = r.generate([token, ids, here])
   out['ids'], out['generated'], out['verdict'], out['events']
   ```
5. **Verify before trusting output** — the same pattern `verify_runmodel.py`
   uses: build (or obtain) a source-side reference of the identical wiring,
   compare `r.forward`/`r.logits` against it at the display boundary
   (`nemotron_hcl._val`, tolerance `< 1e-6`), confirm `r.collapse(scores) ==
   argmax(reference)`, confirm `m.alpha_ok()`. If any of these don't hold,
   the port has a bug — find it before generating anything you plan to read.

---

## Checklist before you say "it's running"

- [ ] No `torch`/`numpy`/`math` import anywhere in the value path (boundary
      float crossings via `_fp`/`_val`/`to_fp`/`from_fp` are the only
      exception — see `verify_no_floats.sh` for what "boundary only" means).
- [ ] No sampling — `collapse()` only.
- [ ] No `max_tokens`, no `for _ in range(...)` around generation — `while
      True` inside `generate()`, ended by one of the three verdicts.
- [ ] No variable holds the whole checkpoint or a dict of every tensor.
- [ ] No hand-written softmax/attention/norm — calls into `r.eng.*` only.
- [ ] `m.alpha_ok()` is `True` after the run.
- [ ] `r.m.braid_word()` is non-empty and grew (the trace is real, not
      fabricated).
- [ ] If you changed or ported anything, you ran it against a source-side
      float reference and it matched at `< 1e-6`, the way
      `verify_runmodel.py` does.

If every box is checked, you are running the model on the substrate. If any
box is unchecked, you have — knowingly or not — bootstrapped part of it in
standard logic, and the run is not the thing this repo claims to do.
