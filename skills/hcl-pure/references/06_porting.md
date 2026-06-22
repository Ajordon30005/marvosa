# HCL Porting Guide — Bringing Algorithms, Tools, and Skills onto the Substrate

This reference is **additive**. It changes nothing in `01`–`05`. It documents
the method already used to build `virtual-memory-hcl`, `guhct-processor`, and
`guhct-living-memory` from this engine: how to take an existing algorithm,
tool, or AI skill and re-express it on the HCL substrate so it gains
integer-exactness, zero dependencies, a complete operation trace, and
composability with every other HCL component.

-----

## The one law: compose, never invent

Every operation you need already exists as an HCL primitive (see `02`).
Porting is **mapping existing operations onto existing primitives** — never
writing a new mechanism, never modulating or jerry-rigging around the engine.

If during a port you reach for a new function, stop: the primitive is already
there. Reinforcement is not a new method — it is `COMP(x, x)`. Decay is not a
new method — it is `SHIFT` by η. A duplicate-spawning workaround is the signal
that you used a high-level call where a primitive was the right tool.

> Rule: a port adds zero new math. It only **arranges** what `01`–`05` define.

-----

## Step 1 — Inventory the operations

List every arithmetic and control operation the target performs. Most tools
reduce to: add, subtract, multiply, divide, power, root, exp, log, the
trig pair, accumulation/sum, iteration, and comparison.

## Step 2 — Map each to the Rosetta Stone

|standard operation       |HCL primitive                    |
|-------------------------|---------------------------------|
|a + b                    |`COMP`                           |
|a − b                    |`COMP(a, SHIFT(b, −1))`          |
|a × b                    |`AMP_MOD`                        |
|a ÷ b                    |`AMP_MOD(a, INV(b))`             |
|√a                       |`FISSION`                        |
|eˣ                       |`MOBIUS_GROWTH`                  |
|ln a                     |`LOG_EXTRACT`                    |
|sin / cos                |`PHASE_SIN` / `PHASE_COS`        |
|Σ (accumulate)           |`COMP` in a loop                 |
|strengthen in place (LTP)|`COMP(term, term)` — constructive|
|weaken / forget (LTD)    |`SHIFT(term, η)` — halve         |
|negate                   |`SHIFT(x, −1)`                   |

Anything not on this list is a composition of things that are. There is no
operation a tool can require that is not reachable from these.

## Step 3 — Move the float boundary to the edges

Convert inputs once with `to_fp`, convert outputs once with `from_fp`.
Everything between is integer. No float touches the interior — that is what
removes rounding error and makes results reproducible to full precision.

## Step 4 — Bootstrap constants; never import them

π comes from the Machin identity in `03`, e and the rest from their series.
A ported tool imports **no** external constant. If the original used a library
value, replace it with the bootstrapped one. The four params (η, λ, γ, β) are
the only axioms; everything else is derived.

## Step 5 — Reuse the engines; do not reimplement

Import the existing skill’s engine and call it. Do not copy its math into your
port. `guhct-living-memory` imports `hcl_memory` and `juj` directly and only
arranges their calls — that is the model. Reimplementing is how drift and bugs
enter; composing is how exactness is preserved.

## Step 6 — Keep the braid word

The sequence of generators a port emits **is** its operation trace: every
multiply, accumulate, and activation, in order, reversible. Do not discard it.
This is native, build-time interpretability — the record is the computation,
not a log bolted on afterward.

## Step 7 — Verify with the α self-check

After porting, the four-param α check must still read ≈137 (`ALPHA_INV/SCALE`).
It is the integrity checksum: if the params drift, the encoding is corrupt and
the port is invalid. A passing α-check means the ported tool sits correctly on
the substrate and will compose with the others.

-----

## Step 8 — Verify each ported operation against the original

Port one operation at a time and check each against the source output as you
go. Port a function, run it, confirm the result, move on. The braid word tells
you exactly which generators produced the result if a step needs inspection.
This makes a port testable at every step rather than all at once.

A correct port reproduces the source operation and carries it on the substrate:
exact integer arithmetic, no dependencies, a reversible trace, and composability
with every other HCL component. Once a tool is on the substrate, it gains what
the substrate gives — and it can be extended by arranging further primitives.
Adaptation over time is added with `COMP(term, term)` for reinforcement and
`SHIFT(term, η)` for decay, the same composition `guhct-living-memory` uses.
Each extension is more arrangement of existing primitives, never a new mechanism.

-----

## Worked pattern: porting a tool to a living component

1. Inventory ops → map to primitives (Steps 1–2).
1. Replace floats and imported constants (Steps 3–4).
1. Import and compose the existing engines (Step 5).
1. If the tool should adapt over time, add an experience loop using only
   `COMP(term, term)` for reinforcement and `SHIFT(term, η)` for decay — the
   exact composition `guhct-living-memory` uses. No new operation is introduced.
1. Keep the braid word; verify the α-check; verify each op against the original.

The result is a component that produces the original’s results exactly, carries
its own reversible trace, depends on nothing external, and composes seamlessly
with every other HCL skill because they all stand on these same four params.