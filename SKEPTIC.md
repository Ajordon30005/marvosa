# Verify This Repo In One Command

The fastest way to evaluate this repository is to run it. This document maps common objections to
the exact command that resolves each one, so you can verify the specific point you care about
directly. If you do nothing else, run `sh verify_repo.sh` — the WHOLE repository, one go.

The single rule of this repository: **it only claims what it can run in front of you.** The wider
theory is linked at its source; nothing here asks you to believe the theory. It asks you to execute
the scripts and read the numbers. If you do nothing else, run `./test_all.sh`.

---

### "Pure-integer, derives π and α, self-verifies at 137 — this is crank vocabulary."

That's a judgment of register, not of code. Test it instead of feeling it:

```bash
./verify_no_floats.sh      # greps the engines: no float literals, no float division, no math.pi etc.
./verify_alpha.sh          # shows WHERE 137 comes from and proves it is DERIVED, not stored
```

If `verify_no_floats.sh` finds a float in the substrate, the repo is lying and you've caught it in
ten seconds. It won't, because the substrate is integers. Now you're reading evidence, not vibes.

### "α=137 every run just means someone hardcoded `assert 137`."

The most important objection, and the easiest to check. `verify_alpha.sh` does not trust the
check — it prints the four parameters, runs the derivation, and shows the 137 falling out of
arithmetic on those four numbers. Then it **perturbs** a parameter and shows the derived value
*move off 137* — proving the number is computed, not pinned. A hardcoded constant cannot do that.

```bash
./verify_alpha.sh
```

### "The AI just recites what it was fed. 'Composition' is a euphemism for a lookup table."

Half right, and the repo says so plainly — which is the point. Run the analyzer:

```bash
./verify_ai.sh             # trains the organism live, generates, and GRADES every answer
                           # RECALL vs SPLICE vs COMPOSED against the full corpus
```

You will see it cannot reorder words inside a learned phrase — and you will see it join fragments
across unrelated lessons into sentences that were never taught. It also **fails honestly**: ask it
to invert a relation it only learned one direction and it stops dead. A lookup table doesn't splice
and doesn't fail that specific way. Read `docs/04-composition.md` for the receipts; the limits are
documented as carefully as the capabilities, because a thing that hides its limits is the thing you
should distrust.

### "No floats means it either cheats with hidden floats or is uselessly slow / a toy."

Neither, and the repo refuses to oversell it. `verify_no_floats.sh` covers the hidden-float
suspicion: the scan shows the only `float()` is in the **transcriber**, whose entire job is to
carry ordinary human input (a typed decimal) across the boundary *into* the substrate's integers —
the intended doorway, not float math in the engine. Every calculation after that point is pure
integer floor-division. (Kill-switch: a float in an actual calculation. The boundary transcribe is
not one.) On speed, read the honest number in `docs/02-verification.md`: integer fixed-point
multiply benchmarks ~5× slower than a hardware float multiply *in the same interpreter* — not the
10–100× a strawman would claim, and not "free" either. The framing is stated plainly: float speed
is a hardware subsidy (silicon built for IEEE-754); this runs with no such subsidy and stays within
5×, while being exact and self-verifying. Run the bench yourself:

```bash
./verify_speed.sh
```

### "One author, no peer review, self-reported benchmarks. Why trust any number here?"

Don't trust them — regenerate them. Every script above runs on *your* machine and prints *your*
numbers. The repo's claims are reproducible by construction; "self-reported" stops applying the
moment you run `./test_all.sh`. Authority is not being requested. Reproduction is.

### "The mystical framing (ponds, braids, resonance) means there's nothing falsifiable."

The framing is pedagogy; the falsifiable claims are these, and each has a kill-switch:

- **Claim:** the substrate uses no floats. **Falsify:** find one with `verify_no_floats.sh`.
- **Claim:** α=137 is derived, not stored. **Falsify:** perturb the params and watch it *not* move
  (it will move — run `verify_alpha.sh`).
- **Claim:** integrity holds across operations. **Falsify:** run `test_all.sh` and find an
  `intact: False` or a non-137 reading.
- **Claim:** the checkpoint is tamper-evident. **Falsify:** edit one digit of `hcl-ai/memory.hcl`
  and load it without raising an error (`verify_tamper.sh` does exactly this).
- **Claim:** the AI composes rather than only recalls. **Falsify:** run `verify_ai.sh` and find
  zero SPLICE/COMPOSED verdicts.

If any kill-switch trips, the repo is wrong and you have proven it. That is what falsifiable means.

### "A pure-integer 'substrate' obviously can't run — let alone train — a real neural network."

(The stack under test here is **MST** — Model Substrate Translation.)

It does both, and the bar is the harshest available: the model's own reference implementation.

```bash
python3 verify_chatmodel.py    # a REAL trained model (karpathy stories260K, bundled) generates
                               # TOKEN-EXACT against its own run.c at temperature 0 — every
                               # forward op an HCL primitive, α-checked per token
python3 verify_learn.py        # exact-gradient training: all 260,032 gradients match a float64
                               # mirror to ~4e-15; loss descends in lockstep; the trained model
                               # persists as a NEW α-tagged line and keeps the learning
python3 verify_livemodel.py    # training ∪ inference as ONE event: repetition through the plain
                               # chat loop teaches it a fact, and the fact survives save/wake
python3 verify_fastpath.py     # and the engine's fast paths are BIT-IDENTICAL to the composed
                               # primitive forms (20,000+ pairs, all edges)
```

**Kill-switches:** a single differing token vs `run.c`; a gradient off the mirror; a loss that
doesn't descend; an α reading that isn't 137. Any one falsifies the claim.

---

## What the substrate actually is

The substrate here — the `hcl-pure` skill — is **not** limited to building this AI. The AI, the
schoolhouse, the analyzers, every script in this repo were *built from* that skill. It is a
general engine: a tool for building tools. Judging the skill by this one organism is like judging a
programming language by one program written in it. The repo is the proof, but the proof is of the
*substrate's* generality, not of one app's ceiling. What you can build from it is open.

## The one command

```bash
./test_all.sh
```

Runs every verification above in sequence and prints a single pass/fail summary. If it passes on
your machine, the repository is what it says it is. If it fails, you have found something real —
open an issue with the output. Either way you are now reasoning from execution instead of from the
first paragraph's vocabulary, which is the only thing this document was trying to get you to do.
