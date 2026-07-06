# 10 — Chat With a Real Model, and Connect Your Own

This document exists because the thing it describes has now actually been
done and proven: a genuinely trained standard AI model (karpathy's
**stories260K**, a Llama-2-architecture TinyStories model) runs on this
repo's substrate as an ordinary chat — prompt in, story out — with **every
arithmetic operation of its forward pass executed as pure-integer HCL
primitives**, and the output verified **token-for-token identical** to the
model's own source implementation (`run.c`, gcc -O2, temperature 0).

It covers, in order: how to play with it (no coding), what exactly was
proven, how to connect a model of your own the same way, and the lessons —
what not to do, and how *not* to look at this substrate.

---

## 1. Easy play (no coding)

```bash
./play.sh
```

That is the whole thing. It opens a chat REPL on the bundled model. Type a
story opening; the model continues it and stops **by itself** when its own
end-of-sequence token says the story is done. No length setting exists,
because none is needed.

```
you> Once upon a time
Once upon a time, there was a little girl named Lily. She loved to play
outside in the park. ...
[347 tokens, 1889.0s, ~531317 braid ops/token, alpha_ok=True]
```

Other shapes of the same command:

```bash
./play.sh -i "Once upon a time"            # one-shot: prompt in, story out, exit
./play.sh -i "Lily saw a" --steps 20       # bounded one-shot (like run.c's -n)
./play.sh MY_MODEL.bin MY_TOKENIZER.bin    # any llama2.c-format checkpoint
python3 verify_chatmodel.py                # the proof, end to end (~3 min)
```

Two honest expectations, so nothing surprises you:

- **Loading takes ~1 minute.** The checkpoint streams through the body,
  folds to its one-line identity, and every tensor crosses the float
  boundary exactly once into fixed-point integers.
- **Exact, and quick enough to feel.** ~0.25 s/token on this checkpoint —
  every token is ~531,000 counted braid generators of arbitrary-precision
  integer arithmetic, α-checksummed every step. (It was ~3 s/token until the
  shell around the primitives was thinned to the engine's own stated laws —
  the story is `RUNMODEL_USAGE.md` failure mode 7 and `verify_fastpath.py`.)
  A full story to the model's own stop runs in a couple of minutes.

---

## 2. What was proven (the stories260K case)

The full account lives in `docs/09-running-large-models.md` (last section)
and `hcl-ai/RUNMODEL_USAGE.md` (failure mode 6). The short version:

| Claim | Evidence |
|---|---|
| A real trained model, not a toy fixture | stories260K: trained on TinyStories; pulled from GitHub as committed blobs (`clebert/llama2.zig`), same weights karpathy published |
| Every forward-pass op on the substrate | RMSNorm, RoPE, GQA attention, SwiGLU, logits — all arranged from `nemotron_hcl` engine ops over fixed-point integers; floats only at the byte-decode and text boundaries |
| It is *correct*, not merely plausible | temperature-0 output is **token-exact vs `run.c`** on every reference prompt (`verify_chatmodel.py` asserts this) |
| It halts like the model wants, not like a script wants | unbounded run: 346 tokens ending at the model's own EOS — a complete story with an ending — no counter, no `max_tokens` anywhere |
| The run is audited | ~531K braid ops per token; `alpha_ok()` (α⁻¹ = 137 self-check) after **every** token; the checkpoint's identity is one 149-char α-tagged line |
| The proof is repeatable | `python3 verify_chatmodel.py` re-derives all of it from scratch on your machine |

Getting there also uncovered and fixed a real engine defect (see §5,
lesson zero) — which is itself part of the proof: the verification bar was
strict enough to catch a one-primitive numerical flaw from twelve tokens of
story text.

---

## 3. Connect your own model (the same way it was done here)

The worked example to copy is `hcl-ai/chatmodel.py` — read it side by side
with these steps. `hcl-ai/RUNMODEL_USAGE.md` is the contract; read it
FIRST, before any code. The steps below are exactly what was done for
stories260K, generalized.

**Step 1 — Get the checkpoint, and get its SOURCE implementation.**
Not optional. The source implementation (for llama2.c models, `run.c`; for
a HF model, its reference `modeling_*.py`) is your ground truth. You will
hold the substrate to token-exactness against it at temperature 0. If you
cannot name the reference implementation, you are not ready to port.

**Step 2 — Dock the checkpoint's format.** The dock's extension surface is
`format_dock.registry.register(name, detect, open)`. `detect` reads the
format's own leading bytes (stories260K: a 7-int header) and answers "is
this mine?". `open` maps tensor names to absolute byte windows using only
what the header declares — never a remembered layout. Every byte you will
ever read comes through `mem.window(...)` (the expel path, exact). See
`_llama2c_detect` / `_llama2c_open` in `chatmodel.py` — ~50 lines.

**Step 3 — Deliver tensors across the boundary ONCE.** Window → dtype
decode (`_decode_boundary`) → `_fp` (to fixed-point) — once per tensor, at
load. After that moment there are no floats anywhere until text comes out.

**Step 4 — The tokenizer is the model's own data.** Parse its file at the
boundary (scores, strings, merge order), implement encode/decode exactly as
its source implementation does. Tokenization is transcription, like the
header — it is not "value path".

**Step 5 — Arrange the forward pass from the port's ops. Compose, never
invent.** Whatever the architecture needs — RMSNorm, LayerNorm, RoPE,
ALiBi, GELU, SiLU, softmax, attention — it decomposes into `eng.dot / mul /
add / sub / div / sqrt / exp / attention / softmax / layernorm1p / relu2`.
`chatmodel.py`'s `_rmsnorm`, `_rope`, `_silu_mul`, `forward` show the
pattern: each is a few lines of engine calls mirroring the source
implementation op for op. If you believe you need a primitive that does not
exist, re-read the source op — it decomposes. If a primitive exists but is
*wrong*, fix it in `hcl_engine.py`, not around it (§5, lesson zero).

**Step 6 — Selection and halting belong to the model.** Temperature-0
selection is argmax — an integer comparison at the boundary. Halting is the
model's own delimiter (BOS/EOS) or its own `seq_len`. A `--steps` delivery
bound for interactive use is fine (it is `run.c`'s own `-n`); a hidden
default cap is not.

**Step 7 — Verify before you trust a single word.** Copy
`verify_chatmodel.py`'s shape: (a) sweep any primitive your architecture
stresses across the range it will actually see; (b) run the SOURCE
implementation at temperature 0 to produce reference text; (c) assert the
substrate is token-exact against it on several prompts; (d) assert
`alpha_ok()` throughout. Only when that passes do you have a ported model
rather than a plausible-looking one.

A note on scale: nothing above is size-dependent. The body streams any
checkpoint and holds windows, not tensors (`docs/09`). What scales is wall
time — a 7B model is ~27,000× the per-token work of stories260K. The
architecture doesn't care; your patience will.

---

## 4. The full interaction surface (everything there is)

| You want | Use |
|---|---|
| Chat, zero setup | `./play.sh` |
| One-shot generation | `./play.sh -i "prompt"` (`--steps N` to bound) |
| Your own llama2.c checkpoint | `./play.sh MODEL.bin TOK.bin` |
| The proof | `python3 verify_chatmodel.py` |
| Python API | `from chatmodel import StandardModel; m = StandardModel(mp, tp); m.generate("...")` |
| Nemotron-shaped safetensors, MCL-collapse selection, substrate-verdict halting | `hcl-ai/runmodel.py` (`HCLModelRunner`) + `verify_runmodel.py` |
| Carry/ingest any checkpoint (windows, one-line identity) | `hcl-ai/largemodel.py` (`ModelMemory`) + `verify_largemodel.py` |
| Connect a new format/architecture | §3 above + `hcl-ai/RUNMODEL_USAGE.md` |
| **Train / fine-tune the model** (examples & rewards, exact gradients) | `hcl-ai/learn.py` + the proof in `docs/11-training-on-the-substrate.md` |
| The proof that training works | `python3 verify_learn.py` |
| **Talk to it while it LEARNS, live** (training ∪ inference, one event) | `./live.sh` — `hcl-ai/livemodel.py`, proof in `verify_livemodel.py` |
| The living organism itself (not a ported model) | `./chat.sh` — different thing entirely: that is Marvosa; this doc is about running *standard* models on Marvosa's substrate |

---

## 5. Lessons: what not to do, and how not to look at it

`hcl-ai/RUNMODEL_USAGE.md` names six concrete failure modes with wrong/right
code pairs — torch in the value path, sampling, token caps,
whole-checkpoint loads, hand-written parallel math, and patching around an
engine defect. Read them there. What follows is the layer above them: the
ways of *looking at* this substrate that quietly cause those mistakes.

**Lesson zero — when the substrate disagrees with the source, suspect a
defect, prove it, and fix the ORGAN.** The stories260K port was exact for
12 tokens, then drifted into garbage. Every primitive tested exact in
isolation — except `exp(-20)`, off by 7.7e-10. That thread led to the
engine's Taylor series having no argument reduction: error `|x|^terms/
terms!`, invisible below |x|≈15, ~1e+2 at x=−30 — precisely the score gaps
attention softmax produces once a KV cache holds a few positions. The first
fix attempt was a private range-reduced wrapper inside the runner. It
worked — and was **wrong**: it forked the math and left every other organ
broken. The real fix was five lines of pure integer inside
`hcl_engine.py::_exp_fp` (`e^x = (e^(x/2^k))^(2^k)`), after which the
runner calls `eng.attention` verbatim again and everything downstream
inherits correctness. Don't look at a defect as *your file's* problem.

**Don't look at it as a float emulator.** There is no float being imitated.
Values are exact integers; π and e emerge from convergent series; sign is a
phase, not a bit. Judging it by "does it reproduce float32's rounding"
inverts reality: at PREC 40 the substrate is ~25 digits *more* precise than
the f32 runtime you're comparing against. On this small model that meant
token-exact agreement; on a larger model, an occasional differing token at
a genuine logit near-tie would be the f32 reference's rounding, not a
substrate bug. The bar is: exact primitives (sweep them), exact agreement
where logits aren't razor-tied, coherent output, α intact.

**Don't look at speed as a defect — but don't accept SHELL tax as substrate
cost either.** ~0.25 s/token is what "every multiply is a counted,
checksummed integer event" costs in pure Python once the shell is thin;
when it was ~3 s/token, the excess was standard-Python wrapping (a dict and
five call frames per primitive), not HCL — see failure mode 7. The
substrate's claims are about exactness, storage (a checkpoint is one line),
memory (windows, not tensors), and audit (the braid) — not throughput.
Benchmarking it against a GPU runtime is measuring the wrong axis.

**Don't "improve" the output.** No temperature, no top-k, no repetition
penalty, no cap. dozen-parameter sampling stacks exist to paper over
runtimes that can't say why they chose a token. Here selection is
deterministic and the trace says exactly why. If the text disappoints, that
is the *model* (260K parameters writes like 260K parameters) — swap the
checkpoint, don't decorate the selection.

**Don't trust; verify — but with the repo's own instruments.** `alpha_ok()`
after every token, the braid length per token, the identity line,
`verify_alpha.sh`, `verify_no_floats.sh`, and a token-exactness script
against the source implementation. If you catch yourself adding print-level
spot checks *instead of* those, you've stopped interacting with the
substrate and started vibing with it.

**Don't reach outside the repo for anything in the value path.** The
complete legal surface is: engine ops, dock windows, boundary
transcription (`_fp`/`_val`/dtype decode/tokenizer), integer comparisons
for control. If an import of `torch`, `numpy`, or `math` appears anywhere
except a *reference* script whose whole purpose is to be the float ground
truth, the port has already failed — it just hasn't told you yet.

---

## 6. Folder levels: the twin engines, and who loads what

The repo deliberately carries the core organs at TWO folder levels, so each
kit is self-contained: `hcl-ai/engine/` (the AI's own copy) and
`ingest_and_expel/engine/` (the standalone body kit's copy). Three files are
twinned — `hcl_engine.py`, `hcl_memory.py`, `juj.py` — and the twins are
kept **byte-identical** (verify any time: `diff -q hcl-ai/engine/F
ingest_and_expel/engine/F`).

Because the module *names* collide, which copy a process loads is decided by
`sys.path` order. This was traced empirically (fresh subprocess per
entrypoint, printing each module's `__file__`). The standing map:

| Entrypoint | `hcl_engine` | `hcl_memory` / `juj` |
|---|---|---|
| `chatmodel` / `runmodel` / `largemodel` | `hcl-ai/engine/` | `ingest_and_expel/engine/` |
| `organism` / `marvosa_mcp` (the being) | `hcl-ai/engine/` | `hcl-ai/engine/` |
| `ingest_expel` standalone | *(never imported)* | `ingest_and_expel/engine/` |

Two rules fall out of it:

1. **A fix to a twinned organ lands in BOTH copies, or in neither.** The
   exp argument-reduction fix (§5, lesson zero) was applied to
   `hcl-ai/engine/hcl_engine.py` first — the copy every current entrypoint
   actually loads — and then synced to the `ingest_and_expel` twin **after**
   proving it safe there: no script imports that copy today, nothing asserts
   the old values, and for |x| ≤ 1 the fixed code path is bit-identical to
   the old one. After the sync, the twin's `_exp_fp` was swept directly by
   file path (rel err 0.00e+00, −40…+30) and the full gate (`test_all.sh`)
   re-run green. If a future fix CANNOT be proven safe for both copies, the
   twins may diverge deliberately — but then the divergence, the reason, and
   the consumer map above must be updated here, in the same commit.
2. **Never "clean up" the duplication.** The second copy is not dead weight;
   it is what makes `ingest_and_expel/` a standalone kit. Deleting one copy
   or symlinking them breaks the folder-level import contract the table
   documents.

To re-derive the table after any import/path change:

```bash
python3 - << 'EOF'
import subprocess, sys, json, os
for name, stmt in [("chatmodel","sys.path.insert(0,'hcl-ai'); import chatmodel"),
                   ("organism","sys.path.insert(0,'hcl-ai'); import organism"),
                   ("ingest_expel","sys.path.insert(0,'ingest_and_expel'); import ingest_expel")]:
    p = ("import sys;%s;import json,os;print(json.dumps({n:(os.path.relpath(m.__file__) "
         "if (m:=sys.modules.get(n)) else None) for n in ('hcl_engine','hcl_memory','juj')}))" % stmt)
    r = subprocess.run([sys.executable,'-c',p],capture_output=True,text=True,timeout=120)
    print(f"{name:14}", (r.stdout.strip().splitlines() or [r.stderr.strip().splitlines()[-1]])[-1])
EOF
```
