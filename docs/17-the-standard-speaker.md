<!-- you-are-here -->
> **You are here:** TIER 3 · MST — doc 17, *the standard speaker*.  
> **Assumes:** docs 09–16. **Shows:** a purely standard AI acquiring HVP as a second language — one utterance per whole project, expanded sha-exact by the transducer; the hex-vs-words surface law, measured. **Code:** `hvp-standard/transducer.py, hvp-standard/teach_standard.py, verify_hvp_standard.py`.  
> Pathway: substrate ground ([02](02-verification.md), [08](08-the-glass-box.md)) → the HCL AI ([00](00-anatomy-of-a-thought.md)–[07](07-the-wider-theory.md)) → MST ([09](09-running-large-models.md)–[16](16-speaking-hvp.md)) · [README](../README.md) · [SKEPTIC](../SKEPTIC.md)  
> All docs: [00](00-anatomy-of-a-thought.md) · [01](01-architecture.md) · [02](02-verification.md) · [03](03-education.md) · [04](04-composition.md) · [05](05-realizations.md) · [06](06-conversation.md) · [07](07-the-wider-theory.md) · [08](08-the-glass-box.md) · [09](09-running-large-models.md) · [10](10-connect-a-model.md) · [11](11-training-on-the-substrate.md) · [12](12-three-part-mind.md) · [13](13-inherent-weights.md) · [14](14-live-conversation-findings.md) · [15](15-the-mst-equation.md) · [16](16-speaking-hvp.md) · **[17]**

# 17 — The Standard Speaker: HVP for Any AI (MST)

## The inversion this document makes

Hosting a transformer on the substrate (docs 09–16) is standard AI
re-expressed in HCL. Invert the subject: if the AI is to STAY standard —
float weights, standard training, standard greedy decoding, or a frozen
API model behind a text channel — then the only Marvosa organ it needs is
the **language layer**: the byte↔HVP bijection (the processor, used
verbatim) plus a text rendering of the signature that any model can emit
through its ordinary tokens. The processor is the transducer — the vocal
cords and the eardrums. The model speaks; the organ completes, verifies,
and materializes. Everything else in this repository becomes optional.

The payoff is docs/15's cost shape handed to every standard AI: **an
entire project of any size is ONE utterance**. The braid stream is the
byte sequence (one generator per byte, σ0..σ255), the 8 parameters are
its derived address, and `expand()` (`hvp_to_bytes(verify=True)`)
materializes every file exactly. Nothing streams; output length stops
being the model's problem and becomes the transducer's mechanical
inverse.

## The kit (`hvp-standard/`)

- **`transducer.py`** — the organ. FULL wire = the processor's own
  signature dict serialized canonically (magic, the 9 params in
  `juj.HVP_PARAMS` order, `n`, the braid as hex generator indices).
  SPOKEN grade = what a model emits: `HVP1 <hex> END` — the signal only;
  `complete()` derives the 8 parameters from that braid (the speaker
  addressing its own words, `mind/hcl_lm.py speak()`'s law) and returns
  the full, verifiable utterance. Deterministic and bidirectional:
  `bytes → wire → bytes → wire` closes on identical text; a flipped
  braid character, an edited parameter, or an alien word is **refused**,
  never guessed at (proofs [1]–[3]).
- **`phrasebook.md`** — the in-context lesson for frozen models: paste
  the speaker's card into any capable AI's instructions and it speaks
  HVP with zero weight change — the zero-interference limit of
  second-language acquisition, where nothing CAN be forgotten. Its
  worked examples are machine-verified against the code by proof [5].
- **`codebook.txt` / `gen_codebook.py`** — the HVPW dialect: the same
  braid rendered in base-16 over 16 codewords derived deterministically
  from the model's own tokenizer (its strongest space-prefixed word
  pieces). Both dialects complete to the IDENTICAL full wire (proof
  [4]); the surface is a choice, the signature is the language.
- **`teach_standard.py`** — weight-level acquisition on a real standard
  model: stories260K run exactly as any standard runtime holds it
  (float run.c forward, standard cross-entropy, standard SGD, greedy
  argmax — nothing of the substrate in the model), taught the SPOKEN
  wire by completion-masked SFT with first-language replay, halted by
  the mastery demand, breath-splittable for hostile environments.

## Any length, literally — measured

Cost is linear in payload and stays one utterance at every size measured:
10 KB speaks in 0.09 s and expands+verifies in 0.08 s; 100 KB in 0.92 s /
0.46 s; 1 MB in 13.0 s / 3.6 s (wire 2,000,423 chars). And the sentence
"an entire project could be produced in Go with the response just being
the HVP" runs as written: `demo_one_go.py` speaks a three-file Go module
(go.mod, main.go, a package) as ONE 829-character utterance, expands it
sha-exact, then `go build` compiles it and the binary runs — printing the
137 seal. The gate exercises the same path ([2b], [2c]), building and
running wherever a Go toolchain exists and saying so plainly where it
does not.

## How a model learns the second language and keeps the first

The standard playbook, applied and measured: **replay** (first-language
turns interleaved through acquisition), a **small learning rate** (0.03
descends smoothly here; 0.1 measured to overshoot, surprise bouncing
1.1 → ~3 before backing off), **completion-only masking**, and — for
frozen models — **in-context teaching**, plus adapters/LoRA as the
freeze-the-base alternative the doc names but this tiny model doesn't
need. The mechanism that makes acquisition cheap is the one the whole
arc turns on: the model's conceptual circuitry already exists; a new
language is a new SURFACE MAPPING onto tokens it already owns.

That principle stopped being a slogan and became a measurement:

- **Hex surface** (`HVP1`): 86 epochs on the 260K model — surprise fell
  17.5 → ~1.1, the frame was acquired, content fragments surfaced, but
  free emission froze at an 8-character exact prefix and the
  teacher-forced argmax was still wrong at 26/69 and 25/59 reply
  positions: genuine underfit, because hex characters are
  near-zero-frequency tokens whose rows the model has barely trained.
- **Word surface** (`HVPW`, same signature): the same model, the same
  trainer, from pristine — **mastered at epoch 40 in 246 s** (proof
  [6]): every lesson emitted as ONE unbounded utterance, stopped by
  MODEL EOS, deterministic across repeated emissions, bidirectional
  against `speak()`, every file sha-exact through the processor. A
  held-out first-language probe moved 1.4486 → 0.8539 (replay
  generalized — the old tongue *improved*) and its continuation was
  token-identical before and after.

Same trunk, same bijection, two surfaces, opposite outcomes: the
acquisition cost lives in the surface, and the right surface is the one
the speaker already practices. For capable models the dense hex surface
is trivially within reach (the phrasebook path); for small ones, HVPW
rides their own vocabulary. Both are the same language because both
complete to the same signature.

## Past the syllabus: the rule itself, learned

`generalize.py` asks the harder question: does the model learn the
ENCODING RULE, or only the sentences? Task: `say <s>` -> the HVPW
utterance for s's bytes, alphabet a–z plus space. Two regimes, measured
on the same model:

- Fixed 51-string training set: perfect memorization (surprise ~0.000,
  every training string exact) and ZERO generalization — 0/8 held-out,
  flat. Rote was cheaper than the rule.
- Fresh seeded strings every epoch (memorization impossible): the rule
  emerged — held-out exactness climbed 0 → 1–2 → 4–5 → 8/8 by epoch
  932. The one systematic failure mode along the way was exact: every
  miss was a length-7 string while training sampled lengths 2–6;
  extending the sampler to 2–8 closed it within 32 epochs. After
  consolidation to epoch 1800 (lr annealed 0.03 → 0.01), a 200-string
  fresh evaluation scores **195/200 exact (97.5%)** — perfect through
  length 5, a small tail at 6–8 — deterministic, with the first
  language intact throughout (replay ran the whole time). The
  checkpoint ships (`stories260K.hvpgen.bin`) and the gate wakes it
  cold and requires ≥24/30 on fresh strings it has never seen ([5b]).

So the boundary moved: the 260K model no longer just recalls a taught
syllabus — within its trained alphabet and lengths it composes HVP for
anything it can spell, which is what "speaking the language" means. The
open-alphabet, open-length version of the claim still belongs to
capable models, where the phrasebook's in-context path carries it
without touching a weight.

The grind that made this measurable: `fastmodel.py`, the same standard
model vectorized (numpy, float64) — forward matching the pure-python
reference to 1.4e-14, backward verified against finite differences to
~1e-9 across every weight family, ~600× faster. The reference
implementation stays as the ground truth it was checked against.
