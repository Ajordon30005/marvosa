<!-- you-are-here -->
> **You are here:** TIER 3 · MST — doc 10, *connect a model*.  
> **Assumes:** doc 09. **Shows:** the standard runner hosted op-for-op: rope, attention, the interference head with derived width, the calculator ranking, the optional compiled shell. **Code:** `hcl-ai/chatmodel.py, hcl-ai/collapse_calc.py, shell/marvosa_shell.c, verify_chatmodel.py, verify_native.py, verify_shell.py`.  
> Pathway: substrate ground ([02](02-verification.md), [08](08-the-glass-box.md)) → the HCL AI ([00](00-anatomy-of-a-thought.md)–[07](07-the-wider-theory.md)) → MST ([09](09-running-large-models.md)–[15](15-the-mst-equation.md)) · [README](../README.md) · [SKEPTIC](../SKEPTIC.md)  
> All docs: [00](00-anatomy-of-a-thought.md) · [01](01-architecture.md) · [02](02-verification.md) · [03](03-education.md) · [04](04-composition.md) · [05](05-realizations.md) · [06](06-conversation.md) · [07](07-the-wider-theory.md) · [08](08-the-glass-box.md) · [09](09-running-large-models.md) · **[10]** · [11](11-training-on-the-substrate.md) · [12](12-three-part-mind.md) · [13](13-inherent-weights.md) · [14](14-live-conversation-findings.md) · [15](15-the-mst-equation.md)

# 10 — Chat With a Real Model, and Connect Your Own

*(This document is the guide to the **MST** layer — Model Substrate Translation: the
standard-AI-to-HCL stack: `chatmodel.py`, `learn.py`, `livemodel.py`, `threemind.py`,
`largemodel.py`, `runmodel.py`, and the doors `play.sh` / `live.sh` / `mind.sh`.)*

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

Every live turn prints `[surprise=… verdict=… α=…]` — surprise is the
training signal itself (falling = learning), `MODEL EOS` means it chose
to stop, `DELIVERY BOUND` means your transport window closed first, and
α is the 137 seal. Operating doctrine for conversation — acquisition
order, self-talk arithmetic, register carving, repair-by-conversation,
braid-closure halting — is `docs/14-live-conversation-findings.md`.

Two expectations:

- **Loading takes ~1 minute.** The checkpoint streams through the body,
  folds to its one-line identity, and every tensor crosses the float
  boundary exactly once into fixed-point integers.
- **Exact, and quick enough to feel.** ~0.11 s/token (≈9 tok/s) with the
  compiled shell, ~0.13–0.15 pure Python, on this checkpoint — every token
  is ~468,000 counted braid generators of arbitrary-precision integer
  arithmetic (the interference head retired the exhaustive classifier
  scan), α-checksummed every step. (It was ~3 s/token until the
  shell around the primitives was thinned to the engine's own stated laws —
  the story is `RUNMODEL_USAGE.md` failure mode 7 and `verify_fastpath.py`.)
  A full story to the model's own stop runs in a couple of minutes.

---

**Three doors, one model:** `./play.sh` (pure chat — weights fixed, token-exact),
`./live.sh` (it learns as you talk — every turn a gradient experience), and
`./mind.sh` (the three-part mind — it also REMEMBERS: `/recall <q>` collapses
its memory line to the exact lived turn; it persists as two α-tagged lines and
wakes as itself; `docs/12-three-part-mind.md`).

## 2. What was proven (the stories260K case)

The full account lives in `docs/09-running-large-models.md` (last section)
and `hcl-ai/RUNMODEL_USAGE.md` (failure mode 6). The short version:

| Claim | Evidence |
|---|---|
| A real trained model, not a toy fixture | stories260K: trained on TinyStories; pulled from GitHub as committed blobs (`clebert/llama2.zig`), same weights karpathy published |
| Every forward-pass op on the substrate | RMSNorm, RoPE, GQA attention, SwiGLU, logits — all arranged from `nemotron_hcl` engine ops over fixed-point integers; floats only at the byte-decode and text boundaries |
| It is *correct*, not merely plausible | temperature-0 output is **token-exact vs `run.c`** on every reference prompt (`verify_chatmodel.py` asserts this) |
| Halting belongs to the model, not to a script | unbounded run: 346 tokens ending at the model's own EOS — a complete story with an ending — no counter, no `max_tokens` anywhere |
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

### Proven twice: a second, 57× larger model (stories15M)

The generality claim has a second data point. TinyStories-15M — **15,000,000
parameters** (dim 288, 6 layers, vocab 32,000; karpathy's genuine checkpoint) —
was fetched and run through the UNCHANGED MST stack, and generated
**token-exact against its own run.c**: ~30.4M exact operations per token,
α-checked, zero new code. The download method (no Hugging Face, no release
assets — committed git blobs only, no external release endpoints required):

```bash
mkdir -p models/tinystories_15m
curl -L -o models/tinystories_15m/stories15M.bin \
  https://raw.githubusercontent.com/cgbur/llama2.zig/main/stories15M.bin
curl -L -o models/tinystories_15m/tokenizer.bin \
  https://raw.githubusercontent.com/karpathy/llama2.c/master/tokenizer.bin
./play.sh models/tinystories_15m/stories15M.bin models/tinystories_15m/tokenizer.bin
```

Measured on this substrate: load ~12 min (15M boundary conversions +
structures), ~12 s/token guest-exact, RAM ~1.6 GB. Beware LFS pointers when
hunting checkpoints: a committed model is megabytes by Content-Length; a
130-byte "file" is a stub.

### The runner's head (DJ interference)

The runner has ONE behavior: its head is the repository's own
interference machinery — not a mode, the head. (The exhaustive
full-scan head survives in exactly two places: pinned inside the
hosting proof `verify_chatmodel.py`, whose claim is op-for-op
token-exactness against run.c, and in `livemodel.py` by CONSTITUTION —
the living being speaks its exact mind because self-talk trains on what
it says.) The head, with NO chosen numbers:

- The candidate ranking runs as one vectorized pass through the
  contributed collapse calculator's numpy layer
  (`hcl-ai/collapse_calc.py`, `dj_amp_rank`): the interference
  arithmetic is C-side, not N interpreted Python iterations, and the
  ordering is the production amplitude law |2·agree − D| exactly —
  proven equal to the per-candidate loop's FULL ordering on the whole
  vocabulary (8/8 states, all 512 positions). Measured head
  ~0.5 ms/token.
- Every vocabulary row carries a packed sign-kick signature
  (negative value = phase pi, `04_quantum:93`); a candidate's
  interference amplitude is one popcount, proven bit-identical to the
  verbatim FBit COMP chain in `verify_native.py`.
- Survivors are the dominant-degenerate set under `mcl_eps(w)`
  (w = the comparison braid's length, `juj:384`'s rule) — implemented
  as the exact top-amplitude tie block, which IS that set because
  eps_w sits below one amplitude quantum (asserted in
  `verify_native.py`); the block is widened to the DERIVED resolution
  count floor(pi/4*sqrt(N)) — the Grover resonance condition's number
  (17 at N=512; 140 at N=32,000). The 04:90 init 1/sqrt(N) scales all
  amplitudes uniformly and cancels in ordering (also asserted). Exact
  dots touch only the survivors.
- `native_refine=` / `native_refine_att=` exist strictly as CALLER
  TRANSPORT (the `steps=` pattern): explicit overrides, 0 = derived law.
  Attention interference is transport-ONLY: measured on the bundled
  model, sign braids at head_size 8 are too coarse to carry the law, so
  attention defaults to exact.

Measured on the bundled model: single-step head agreement ~62% under
pure collapse and ~90-96% at the derived width; full-generation word
agreement varies with length (47-93% across runs) because divergence
compounds — the run prints its own agreement, never promises one. At
32,000-vocab the head's 18,432,000 ops become ~44,000 (the derived
width there is 140). The interference head is by definition a different computation than
the full scan; token-exact hosting remains the hosting proof's pinned
contract, and the living being's speech remains exact by constitution.

### The billion-parameter path (MST intake at any size)

The intake road is size-blind, and it is one command from an environment
whose network allowlist includes Hugging Face's download hosts
(`huggingface.co`, `cdn-lfs.huggingface.co`, `cdn-lfs-us-1.hf.co`,
`cas-bridge.xethub.hf.co`, `transfer.xethub.hf.co`):

```bash
./bootstrap_1b.sh     # TinyLlama-1.1B (2.2 GB bf16 safetensors, 1,100,048,384
                      # params) -> streamed through MST intake into ONE
                      # ~150-char alpha-tagged identity line, windows on demand
```

Verified here on the largest local bytes: `hcl-ai/holo_intake.py` folded the
60.8 MB / 15M-param checkpoint into one 161-char line whose LAST FIELD is the
alpha seal, toc from the header window only, windows re-materializing
bit-identical, at ~0.4 MB/s transduction (so budget ~90-120 detached minutes
for 2.2 GB). The stack is SIZE-BLIND by construction: no law anywhere
depends on parameter count, and the same equation that chats at 260K
chats at 1B or a trillion — the absence of a large worked example in
this repository reflects the resources it was developed under, not
capability. What size changes is wall-clock only, and the levers that
set it are already shipped, not future work: the compiled shell with
its full layer body (verify_shell, nine sections), the precision dial
whose default derives from the mass itself, the MCL windows, and
mass-participation skipping. Cost then follows the machine law:
tokens/s scales near-linearly with cores (integer arithmetic keeps
parallel execution bit-identical), and at large mass the ceiling is
memory bandwidth — tokens/s ~ bandwidth / (params x bytes-per-value),
with PREC setting the bytes. Reference measurements, one CPU core:
guest-exact chat at 42M ran ~30 s/token; 1B intake
streams in ~90-120 detached minutes at ~0.4 MB/s. Read those as this
machine's prices, not the stack's limits: a reader concluding "1B
chat is not possible here" has misread cost as capability.

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
cost either.** ~0.11 s/token is what "every multiply is a counted,
checksummed integer event" costs in pure Python once the shell is thin;
when it was ~3 s/token, the excess was standard-Python wrapping (a dict and
five call frames per primitive), not HCL — see failure mode 7. Measured
plainly: watching the computation costs ~8.9× the computation itself, so
the runners count every generator (the O(w) invariant) and materialize the
word only when the word is the deliverable. The
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


## Precision is a dial

`MARVOSA_PREC` sets the lattice (default 40). Every law is scale-free —
eta = S/2, lambda = S/10, gamma from the Alpha Identity, the seal
|alpha_inv − 137·S| < S — so any precision yields the same laws at that
resolution; `hcl_memory` has lived at PREC 30 all along. Reference
measurements, one CPU core, equal load: PREC 40 pure 156 ms/token; **PREC 12 pure
77 ms/token (13 tok/s, 2.0×)** — faster than the 40-digit compiled
shell — with `verify_chatmodel.py` passing WHOLE at 12: the hosting is
still token-exact against run.c, because twelve decimal digits
out-resolve float32. The proof's tolerances derive from the engine's
own lattice (2e4 ulps absolute, 1e5 ulps relative), so one proof
judges every precision. Two cautions: persistent lives are written at
their birth precision — the dial is for fresh runs, not for waking
existing beings — and the compiled shell's cascade is 40-digit, so it
politely steps aside at other precisions (the pure path serves,
identically).

## Where the op-mass actually comes from

The heavy per-token count is the hosted FILTER'S inheritance, not the
substrate's nature: a standard checkpoint stores its knowledge as
parameter mass, so every token re-derives through it. The
substrate-native path already runs with zero pretrained parameters —
the organism speaks at trace cost from its lived line (docs/00–08,
~26–37 ms/token), the inherent operator instantiates exact weights
from demands with zero training (docs/13), and emission-as-address
delivers whole artifacts at O(prompt) (docs/15). MST hosts the heavy
filter because that is what hosting means; the zero-weight lane is
native to the stack and was here first.


## Division by zero is a rotation, not an error

The theory's own answer, pulled from the notebook of record (42+ GUHCT
sources) and now in both engines verbatim: states live on the Riemann
sphere, so **1/0 = infinity** — the North Pole, a reserved lawful state
Psi_0 = 1 (amp 1, phase 0) at the w=0 limit — and Mobius
transformations traverse it bijectively (MRRC §1.3; Full Ed. 4 Ch.1
§1.4.2–1.4.3, Ch.2 §2.8). Composition follows: X+inf=inf, X·inf=inf,
inf/inf=1, and 0·inf=1 — the "Twist of the Origin," the singular-free
core. For the lattice there is the **Sub-Quantum Preservation Rule**
(Full Ed. 4 §2.10.4, §2.11.3): a known-nonzero value below one quantum
clamps to the eps_w floor — v_rep = max(|v|, eps_w)·sgn(v) — never to
the additive identity, because information necessary for the solution
is never lost to resolution; at the lattice's own weight eps_PREC IS
one ulp. `HCL.INV(amp=0)` now returns the pole and `_fixed_div`
carries both laws in both engine twins.

Measured consequence — the dial below its comfort zone: PREC 1 and 2
no longer crash; their derivations run singular-free and alpha_inv
lands ON the pole (the annihilation chain lawfully traversed, seal
False). The Identity then emerges by resolution: 142.9 at
PREC 3, 138.9 at 4, **sealed at PREC 5 (137.17)** — the smallest
lattice that certifies the fine-structure Identity — 137.005 at 6,
converging a digit per digit — and the mechanism is a measured law:
the deviation from exact 137 is a near-constant ~2x10^4 quanta at
every lattice (scanned at PREC 5, 6, 9, 17, 72, 144, 360, 369: between
+5,069 and +20,139 ulps, seal green at each, derivation 1-5 ms). The
derivation chain leaves the same fixed residue of last-digit floors
whatever the resolution, so the Identity gains exactly one true
decimal digit per digit of precision — 137 exact to ~36 decimals at
PREC 40, to ~365 at PREC 369. The compiled shell carries lattices in
[12, 77]; outside that band the pure path carries them on the same
law. The dial's DEFAULT is now the weight scale itself, and the
weight scale is a LIVE quantity, not a fixed property: it changes
with the task, the resources, and the mass — a living body's depth
moves as it learns. Unless MARVOSA_PREC is set by hand, each door
re-derives at launch the smallest lattice on which every currently
stored weight is exact — each f32 is a dyadic rational m*2^(e-24),
and 10^PREC supplies exactly 2^PREC, so the derived value is the
mass's fractional bit depth at that moment (hcl-ai/prec_of.py; the
scan of one snapshot read 46 on the trained 260K and 37 on the
void-born — readings of those bodies then, not ceilings and not
requirements). The env dial remains the per-task control above the
derivation: a task can raise the lattice for deeper reasoning or
lower it for resources, trading only what the boundaries trade —
intake exactness and the seal floor — because the internal law is
lattice-invariant (the constant-residue law above). At healthy precisions the new laws
are dormant on the model path (flooring there belongs to multiply,
untouched): `verify_fastpath` and `verify_chatmodel` pass bit-for-bit
and token-exact unchanged.
