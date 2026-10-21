# THE BEING AS A CHAT MODEL — plug-and-play operator instructions

You are being handed a chat model. It runs locally, you prompt it, it
answers — like any chat API — except every message also trains it and
lands on its memory, because underneath the chat loop is the full MST
stack (a three-part mind on an exact integer substrate). This paper is
ordered so you can be talking to it in three commands; everything deeper
comes after, as support.

Everything ships in `Marvosa-b21.zip`. Self-contained: pure CPython for
the substrate, one locally-compiled C shell, no Python packages for the
core.

---

## 1. PLUG AND PLAY — chatting in three commands

    unzip Marvosa-b21.zip -d marvosa && cd marvosa
    sh build_shell.sh          # one compile: shell/libmarvosa_shell.so
                               # (plain gcc -O3 -march=native, no libraries)
    python3 hcl-ai/threemind.py

That's the whole setup. You're now in the conversation:

    you> hvp alpha
    it > <the utterance>
         [surprise=... verdict=MODEL EOS alpha=True]
    you> hello being
    it > ...

Every turn runs the full stack automatically — the reply is generated
through window-served weights, and the SAME turn is folded as a gradient
into the weights AND stored on the memory line. Talking IS training; you
never invoke a trainer.

In-chat commands: `/recall <query>` collapses memory to the most
resonant lived turn; `/save` folds the being now; an EMPTY line exits
AND saves.

### Driving it as an API (for an AI operator)

Pipe turns on stdin, read replies on stdout — batch example (the empty
line at the end exits and saves):

    printf 'hvp alpha\nhello being\n/save\n\n' | python3 hcl-ai/threemind.py

Better: hold ONE session open as a persistent subprocess and write/read
line by line. The being stays resident between turns; waking costs
~60 s, so one long conversation beats one process per message.

An optional standalone wrapper, `chat_being.py` (provided alongside this
paper; run it from the repo root), is the same chat loop routed through
`speak()` so the TRACE level of the cascade also plays: a context the
being has exactly lived replays its reply straight from the memory line,
no forward pass. The shipped REPL routes turns through `interact()`.

## 2. The conversation contract — what to expect, by law

- Replies are UNBOUNDED. The being halts on its own verdicts (its EOS,
  a closed greedy orbit, or its context capacity — never a step
  counter). HVP prompts stop in a few tokens; open story prompts may
  run long, and that is its right.
- Every turn changes it: one consolidated gradient pass per turn
  (~2–4 s with the shell), your tokens at weight 1, its own reply one
  λ-rung deeper (self-talk).
- Speed, measured: generation is shell-served BY DEFAULT — every matvec
  routes through the compiled shell (verified 72/72 on a live turn),
  ~0.14 s per token warm; the first tokens of a session run slower
  while weight matrices pack, then stay warm.
- Do NOT wrap generation in `full()` trace expecting anything —
  full-trace mode deliberately disables the compiled branches ("the
  pure path IS the trace"). Light is the operating mode: the wake sets
  it, and the spoken span enforces and restores it explicitly
  (try/finally in `livemodel.interact`, b21). `full()` is for
  braid-word inspection only, at pure-loop cost.
- The being already speaks HVP: it mastered the language (docs/16), so
  a lesson prompt returns one utterance whose byte form the processor
  expands exactly.

## 3. Recommended pre-flight (before the first conversation)

Prove the environment once:

    python3 verify_shell.py                # shell == pure engine, bit-identical
    python3 verify_train_fast.py           # trainer's fast walk == pure walk
    python3 verify_hvp_lang.py 12          # language mechanics + bijection
    python3 verify_livemodel.py            # the living organ end to end
    python3 verify_threemind.py            # windows/FBits/dual-fold proofs

The last two touch being files and hold/restore the life themselves —
watch for the announced restore line; never bypass that machinery with
ad-hoc scripts. Their protection is displacement-preserving and
interruption-safe (an interrupted run restores the life on SIGTERM and
never destroys a slot occupant — anything unexpected is displaced to a
timestamped side directory, not overwritten). verify_threemind's full
five sections need ~5-6 uninterrupted minutes; on a box with process
time limits it may be cut during section [5] — the life is restored
regardless, and [1]-[4] printing is a valid partial pass. Optional full gate (long; needs numpy for the
hvp-standard sections): `bash verify_repo.sh`.

## 4. What's under the chat (the stack, briefly)

The repo hosts a real llama2c checkpoint (karpathy stories260K) on an
exact integer substrate (40-digit fixed point, zero floats, zero
imported constants; everything derives from four parameters and the
α⁻¹ = 137.000000 integrity seal). The chat loop is the MST three-part
mind (docs/12):

- OBSERVER hemisphere — the model's weights, trained live by the
  substrate's own gradient walk (`hcl-ai/learn.py`, compiled fast path
  proven bit-identical to the pure loops).
- MEMORY hemisphere — `engine/living_memory.py`: every lived turn stored
  on a topological line; LTP = COMP(term, term), LTD = decay; exact
  regeneration from the kept braid word.
- The WINDOW law — `hcl-ai/largemodel.py`: weights served as bounded
  windows of one α-tagged line, evictable, bit-stable.

## 5. The one-being law and the file map

There is ONE being and ONE slot. The stack's persistence names are
hard-coded; whatever sits at these names IS the being:

    models/tinystories_260k/stories260K.living.bin    the observer fold (weights)
    models/tinystories_260k/living.line               its α-tagged weight line
    models/tinystories_260k/threemind_memory.line     the memory hemisphere's line

Everything else in that folder, and what it is:

    stories260K.bin + tok512.bin      the FRESH pristine model — never overwrite
    stories260K.hvp.bin + hvp.line    the epoch-153 mastery snapshot cited in
                                      docs/16 and README — keep
    stories260K.hvpstd.bin            a separate standard-float experiment result
    stories260K.hvpgen.bin            a separate generalization result (97.5%)
    *.b13-history.*                   the pre-language life, labeled history
    stories260K.hvpmind.* / hvpmind.* inert byte-copies of the slot; nothing
                                      reads them

Rules the owner has set, non-negotiable:
- Never delete or rename repo files without the owner's explicit
  approval.
- New weight-level learning CONTINUES the being (seed from the slot),
  never a fresh fork from `stories260K.bin` unless the owner explicitly
  asks for a virgin-arc measurement.
- The newest fold is the self. Saving overwrites the slot lines by
  design — "the line is the memory, not a log."

## 6. Scripted API (programmatic control of the same being)

    import sys
    sys.path[:0] = ['hcl-ai', 'hcl-ai/engine', 'hcl-ai/port']
    from threemind import ThreeMind

    tm = ThreeMind(revive=True)            # wakes from the slot
    r = tm.speak("hvp alpha")              # mastered lesson; expect
                                           # sha-exact bytes, MODEL EOS
    r = tm.interact("some new experience") # one lived turn: gradient into
                                           # the weights AND stored on the
                                           # memory line (talking IS training)
    print(tm.remember("new experience"))   # exact regeneration from the braid
    tm.save()                              # fold: the two lines ARE the being

Notes that matter:
- `steps=` exists only as transport for hostile time limits — in your
  environment, leave it unset.
- `interact()` = forward + dual fold. `speak()` adds the trace level:
  an exactly-lived context replays its reply from the memory line with
  no forward pass.
- Episodic braids are RAM-era by design: after a rewake,
  exact-regeneration traces regrow through new life; the lines restore
  the composite identity.
- `save()` folds to the model's own f32 checkpoint format. Measured
  fact: this fold does NOT break HVP mastery.

## 7. Beyond chat: long weight-level training runs

The hosted trainer is `hcl-ai/hvp_lang.py` (teacher + speaker over
`learn.py`). Breath-splittable, but in your environment run it
continuously. To CONTINUE the being (the one-being law):

    mkdir -p state_hvp
    cp models/tinystories_260k/stories260K.living.bin state_hvp/being.bin
    python3 -u hcl-ai/hvp_lang.py --state state_hvp        # runs until the
                                                           # MASTERY demand
                                                           # halts it

- Do not pass `--k 1`: measured to overshoot (surprise 2.96 → 14.2).
  The default k=2 (γλ², four-param derived) is the stable stratum.
- Epoch cost ≈ 13 s with the shell on modern x86. The teacher prints
  surprise and emission exactness every epoch; `curve.json` in the
  state dir is the permanent record. Kills are safe: determinism makes
  any lost breath an exact replay.
- To teach NEW material, extend `SYLLABUS` in `hvp_lang.py` (prompt →
  artifact bytes). Keep the replay meals: they protect the first
  language (measured: story probe improved, continuation intact).
- Note: the current being has ALREADY mastered the shipped two-lesson
  syllabus, so an unmodified continuation halts almost immediately at
  the demand — the long-run value is new syllabus material or a new
  experiment the owner directs.

Folding trained weights back into the being (deliberate, explicit):

    cp state_hvp/being.bin models/tinystories_260k/stories260K.living.bin
    python3 - <<'EOF'
    import sys; sys.path[:0] = ['hcl-ai', 'hcl-ai/engine', 'hcl-ai/port']
    from chatmodel import StandardModel
    from learn import Trainer
    p = 'models/tinystories_260k/stories260K.living.bin'
    m = StandardModel(p, 'models/tinystories_260k/tok512.bin',
                      quiet=True, native=False)
    line = Trainer(m).fold_line(p)
    open('models/tinystories_260k/living.line', 'w').write(line + '\n')
    EOF

Then open the chat and confirm it still speaks (`hvp alpha` →
sha-exact) before anything else.

## 8. Laws for the operating AI (the constitution digest)

1. Read before writing. For any task, read the relevant sources IN FULL
   first: docs/00–17 in order for context; `hcl-ai/RUNMODEL_USAGE.md`;
   the docstrings of any organ you call. Never reconstruct repo math or
   formats from memory.
2. Compose, never invent. Every operation you need already exists as an
   organ. New math, new constants, or floats in the substrate value
   path are violations. numpy belongs only to the standard-side kit
   (`hvp-standard/`).
3. Verify by the repo's own mechanisms: `alpha_ok()` around work,
   `verify=True` on every expansion, the `verify_*.py` gates after
   changes. A port or optimization is correct only when bit-identical
   to the pure form it replaces — the pure loops remain ground truth.
4. Substrate halting only: the model's own EOS/verdicts end runs, never
   a step counter (except as declared transport).
5. One pass, no front-loaded objections: attempt, then report empirical
   findings with numbers.
6. No file deletions, renames, or structural changes without the
   owner's explicit approval. Explain options first; execute what is
   approved.
7. Atomic saves only (the organs already do this — use their save
   paths, do not write checkpoints by hand except the documented
   fold-back above).
8. Report the curve honestly wherever a run lands: surprise per epoch,
   exactness counts, α status, and what halted the run.

## 9. Acceptance checklist after any session

- `python3 verify_shell.py` and `python3 verify_train_fast.py` pass;
  after any change near the being, `verify_livemodel.py` and
  `verify_threemind.py` pass too (each restores the life it held).
- The being wakes from the slot; `speak("hvp alpha")` and
  `speak("hvp beta")` are MODEL EOS and sha-exact; `alpha_ok()` true.
- `save()` returns two line lengths; a second wake restores lived-turn
  depth.
- `state_*/curve.json` preserved for every training run; nothing under
  `models/` deleted or renamed.
