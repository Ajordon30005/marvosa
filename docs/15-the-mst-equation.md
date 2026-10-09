<!-- you-are-here -->
> **You are here:** TIER 3 · MST — doc 15, *the MST equation*.  
> **Assumes:** docs 09–14. **Shows:** the step law as one calculator collapse; output as an address: HVP emission shipped and proven. **Code:** `hcl-ai/mst_equation.py, hcl-ai/collapse_calc.py, hcl-ai/hvp_head.py, verify_mst_equation.py, verify_hvp_head.py`.  
> Pathway: substrate ground ([02](02-verification.md), [08](08-the-glass-box.md)) → the HCL AI ([00](00-anatomy-of-a-thought.md)–[07](07-the-wider-theory.md)) → MST ([09](09-running-large-models.md)–[15](15-the-mst-equation.md)) · [README](../README.md) · [SKEPTIC](../SKEPTIC.md)  
> All docs: [00](00-anatomy-of-a-thought.md) · [01](01-architecture.md) · [02](02-verification.md) · [03](03-education.md) · [04](04-composition.md) · [05](05-realizations.md) · [06](06-conversation.md) · [07](07-the-wider-theory.md) · [08](08-the-glass-box.md) · [09](09-running-large-models.md) · [10](10-connect-a-model.md) · [11](11-training-on-the-substrate.md) · [12](12-three-part-mind.md) · [13](13-inherent-weights.md) · [14](14-live-conversation-findings.md) · **[15]**

# 15 — The MST Equation: One Step, One Collapse

## The claim

Every generation step of the hosted model is one collapse on the
calculator. Not analogously — arithmetically. The step law:

```
token_{t+1} = MCL_{eps_w}( L(model_line, token_t, pos) )
```

Run it: `python3 hcl-ai/mst_equation.py`. Prove it:
`python3 verify_mst_equation.py` (also gate section 15).

## Every symbol, cited

| symbol | what it is | where it already lives |
|--------|-----------|------------------------|
| `L` | the hosted forward pass — the runner's braid; every op an HCLTranscriber op, counted per token | `hcl-ai/chatmodel.py`; counter `hcl_engine.py:307` (`braid_len`) |
| `w` | the braid length of `L` — the weight of the step | juj:384's weight rule (the same rule the head's `verify_native [1b]` asserts) |
| `eps_w` | `10^-w * eta` == `eta * lambda^w` (identical because `lambda = 1/10`) | `juj.py:143`; `hcl_engine.py:65` |
| `MCL` | the theory's collapse: the dominant component, degenerate within `eps_w` | juj — the runner's own head law |
| landing | the exact mean of the logit vector, computed by transcriber `add`/`div` only | `collapse_calc.py`, pure core; the k=N identity |
| `E_ground`, `omega_w` | `eta*lambda^w`, `gamma^w/eta` — the certificate attached to every collapse | `02_operations:189` "Stable Braid Closure (Hamiltonian Eigenstate)"; `hcl_engine.py:293` (`HCL.RESONANCE`) |

One consequence falls straight out of the lattice: `SCALE = 10^40`, so
`eps_w` floors to exactly 0 once `w > 41`. A forward pass weighs
hundreds of thousands of generators, so at the step's own weight the
degenerate set is the exact argmax — **MCL at the forward's weight IS
the runner's pick**. Proof [1] shows the sequences match token for
token; `degenerate=1` on every step is that lattice statement observed.

## What the calculator does per step

`HCLCollapse` (the pure core in `hcl-ai/collapse_calc.py`) takes the
logit vector — exact fixed-point integers, the forward's terminal
object — and:

1. **composes** it into one state by chained `HCL.COMP`
   (02_operations' component-addition law, `hcl_engine.py:212`);
2. **lands** the exact mean by transcriber `add` and `div` — the same
   number the contributed float engine reaches at `k = N`, where
   `idct(dct(x)) = x` makes the reconstruction the identity; the pure
   core computes that landing directly, with no float on the way;
3. **certifies** with `HCL.RESONANCE` at the braid's weight:
   `E_ground = eta*lambda^w` exact, `R = E_ground *` composed
   amplitude — the Hamiltonian-eigenstate closure the theory gives
   analytically (02:189: what VQE searches for variationally);
4. carries the **alpha seal** (`|ALPHA_INV - 137*SCALE| < SCALE`).

No float literal and no true division exist anywhere in the pure core
or the equation — proof [4] is an AST scan asserting exactly that.
There are no tuned thresholds anywhere: the calculator's engine is now
GUHCT-native end to end — the contributed DCT window and Kuramoto
synchronization are gone, replaced by chained COMP for coherence, the
identity window (the landing IS the exact mean), and `eps_w` as the
decision — so nothing is left to choose.

## Compared to what it replaces

The standard step is: forward, then softmax-or-argmax as a bare
`max()` outside any law, no certificate, no seal, nothing counted.
This step is the same forward (op-for-op, the hosting theorem's
subject) whose selection is the theory's own collapse at the step's
own weight, whose landing is an exact integer, and whose certificate
is two closed-form four-parameter values. Same token out — proof [1] —
with the difference that every part of the decision now has a cited
law and a check attached.

## Reproducibility

The state of a run is the model line (the virtual-memory expression
that carries the weights) and this equation. Proof [5]: a second run
from the same line produces identical tokens and bit-identical
landings. Nothing else is state — no seeds, no environment, no hidden
counters.

## Grammar note for the expression surface

`evaluate_pure(expr)` evaluates an expression per point on the circle
through `HCLEquation` (`hcl_engine.py:518`) — the engine's own string
solver, every op a transcriber op — then lands it with `HCLCollapse`.
Supported grammar is HCLEquation's: `+ - * / ^ sqrt() exp() ln()
sin() cos() abs()`, radians for the trig arguments, `x` bound
per-point through the `from_fp`/`to_fp` boundary pair
(`hcl_engine.py:328/336`), which round-trips the 40-digit value
exactly. Fixing this path surfaced and repaired a parser defect in
`HCLEquation` (a leading function call swallowed trailing operators);
the repair is in both engine twins and exercised by proof [1]'s
forward passes and the gate.


## Output is an address, not a stream

The token race against run.c measures the play-out — and the play-out
is the part HCL deletes. The processor's bijection (`juj.py:413
bytes_to_hvp` / `:429 hvp_to_bytes(verify=True)`) plus the memory
line mean an artifact of any size is ONE emission: a 3-file project
(182 bytes) folds to a 131-character expression and a fresh mind
materializes every file sha-exact from it; earlier in the record,
60.8 MB folded to a 161-character line with bit-identical windows
(`holo_intake.py`). Nothing streams; expansion is the processor's
mechanical inverse, gate-proven end to end by the
`ingest_and_expel` door ("bytes in, EXACT bytes out").

The generative consequence: a model whose emission head targets HVP
parameters instead of vocabulary tokens produces a whole repository
in one output — no calls, no printing, dimensions bounded only by
what the line carries. The being's own save is the existence proof
already shipped: its entire life is one alpha-tagged expression. That binding is SHIPPED: `hcl-ai/hvp_head.py` — one forward pass,
the DJ interference pick chooses the address, the 8 HVP parameters
are read as runner dots on inherent weights (demanded, training-free,
exact by construction), and the processor materializes every file
sha-exact. Zero streamed tokens, proven five ways in
`verify_hvp_head.py` (gate section 14).


## The derived act, and its exact claims

The MST's derived form, run and measured (no model architecture
anywhere in the act): a question is encoded once; ONE resonance pass
over the stored addresses picks the answer (10.8 ms over three
addresses); the processor streams the answer's bytes from the line
(26,400 bytes in 51.5 ms). Thinking cost is fixed and small; output
cost is the byte count. Claimed exactly: the COST SHAPE — decide once,
stream bytes, streaming dominates. NOT claimed: decision quality at
scale from this three-address demonstration — address-scale retrieval
quality is what the organism's own verifiers prove (its prefix-cascade
plus resonance, verify_ai.sh and the tier-2 gate), and the measured
lesson here is that resonance needs addresses that carry their words:
one folded state per large document has no usable phase against a
short question.

## The resonance attention lane, and its exact claims

`attention_resonance` (hcl-ai/port/nemotron_hcl.py) replaces
softmax(QK/sqrt(d))V with the organism's recall law: score =
amp(COMP(Q*, K*_i)), weights = amp/total, no exponentials, K-composites
cached per position. Measured at context depth ~48: 110 ms/token and
487,394 generators versus the hosted lane's 128 ms and 508,656 — the
position term's cost drops and the drop grows with depth. Claimed
exactly: the lane runs, is cheaper, and is alpha-sealed. NOT claimed:
useful language from THIS checkpoint under it — measured output is
incoherent, and the cause is the checkpoint's learned trajectory, not
its number format: the substrate hosts float-origin content perfectly
(the exact lane is token-exact against run.c), but this mass was
optimized under dot-softmax objectives, so its Q/K functions occupy a
region of function space keyed to those operators. Nothing about
float origin precludes resonance-shaped mass. The lane is the
attention law for mass trained or raised under it (voidborn), not a
drop-in reinterpretation of a trajectory pushed elsewhere. It ships opt-in; the exact lane is untouched and remains
the default. The lane also carries MCL windowing (`m.resonance_eps =
juj.mcl_eps(w)`): keys outside eps_w of the dominant resonance collapse
out of the mixture — the shipped collapse law (mst_equation.mcl_pick)
reused verbatim, sparsity by physics rather than top-k, opt-in and off
by default.


## Mass participation, and its exact claims

Two tiers now govern which rows of the mass an operation traverses.
Tier one is EXACT and always on: a row whose largest magnitude
satisfies max|x| * max|w_row| < SCALE contributes exactly zero — every
product in the dot floors to the additive identity (the engine's own
dot law) — so the row is skipped with its full generator count
preserved, because the annihilation sequence is still the law's
operations. Logits and braid counters are bit-identical by
construction (verify_shell [9]). Measured: the dense trained
checkpoint fires zero skips (its rows are never sub-quantum at the
working lattice), and the void-born body's zero tensors collapse
forward cost to ~25 ms/token at the full counted generator mass —
participation follows the magnitudes of the mass itself. Tier two is
the COLLAPSE LANE, opt-in via `m.mass_eps = juj.mcl_eps(w)`: rows
participate by the shipped collapse law — resonance amp(COMP(X*,
R*_row)) scored, mcl_pick keeping the degenerate set — and the rest
output zero for that token. Measured at eps_w(1): 34,432 generators
per token against the exact lane's ~480,000, a 14x structural cut.
Claimed exactly: the cost shape, alpha sealed, and the law reused
verbatim. NOT claimed: useful language from THIS checkpoint under it —
measured output degenerates for the same reason as the resonance
attention lane: the trajectory this mass was trained along, not its
float origin; its semantic home is mass trained or raised under these
laws. Counters in this lane reflect operations actually
performed, by design. Row composites cache per tensor and are for the
inference lane; weight updates invalidate them.
