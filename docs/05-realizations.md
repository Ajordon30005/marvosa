# 05 — Working With the Skills: Rules That Keep Results Correct

The skills are exact and self-verifying. Following them produces correct results directly. These
are the technical rules that matter when extending or porting this work — stated as engineering
constraints, not commentary.

## Read the full skill before writing code
GUHCT formulas are interdependent. A conclusion drawn from one file or one formula in isolation is
unreliable about the whole. Read `SKILL.md` and its references completely first.

## Compose; never invent a mechanism
Every behavior needed here already exists as a primitive in one of the skills. Reinforcement is
`COMP(term, term)`. Decay is `SHIFT`. Collapse fires at `I_w < ε_w`. If you reach for a new
mechanism, the one you need already exists — find it. Invented stand-ins (a fabricated coherence
formula, a "w-decrement" not in the files) break behavior; the stated mechanisms work.

## Theory-gap rule
If the files do not state something, do not substitute a standard-library or invented replacement.
Flag the gap. Where a tool can query the source corpus, query it; otherwise read the source skills
thoroughly. Do not fill gaps from priors.

## Keep computations on the substrate
No hardcoded values, no `dict`-style lookups where resonance belongs, no Python logic standing in
for substrate operations. Every reversion to substrate primitives improves correctness; every
substitution degrades it.

## Verify continuously with the tools the skill provides
The braid word is the exact operation trace. The α self-check (≈137) is the integrity test. Run
them rather than reasoning about whether something is correct. A check settles in one run what
argument cannot.

## Persistence: the one line IS the memory
The whole being is the one α-tagged line (`memory.hcl`): it holds the composite Ψ and the
topological signature, and waking restores them via the engine's own `from_expression`. The composite
resonates as itself, so a woken being is immediately the same identity (virtual-memory-hcl: "the
equation IS the index"; recall falls back to the composite when no per-trace terms are present). The
per-trace braid words that let it generate fluently are re-formed by living new input, not by
replaying a transcript — memory here is lived, not loaded. A raw-text log (the lifebook) is a
transparency record only; it is never read back as memory.

## The ghost-key rule: forgetting must stay re-learnable
LTD prunes traces from the live store. "Already known" must be computed from the **live** term
store, not a signature registry — a registry can retain ghosts of pruned traces, and treating a
ghost as known silently blocks re-learning. What is forgotten must be learnable again.

## Cost is the interaction, not the engine
A conversational exchange runs well under a second; the time in a long session is the number of
back-and-forth turns, not any single grinding call. Two properties keep each turn cheap. Internal
thinking stays in braid space — the next token is read from the collapse key, so no byte↔braid
transform runs per token; the verified bijection runs once, at delivery. And the engines are
integer-exact with no float overhead. Storage is thorough by design: a trace at every depth the
mind has grown to, which is the framework's deliberate specificity-lock, run serially on a classical
CPU as the honest, unsubsidized cost of a substrate that is parallel by design. Never change the
math for speed.

## No imposed ceiling: weight is complexity, bounded only by the substrate
`w` is the complexity depth of a configuration, not an age or a score (01_theory.md, "Weight w —
Collapse Weight / Complexity Depth"). It self-tunes by the theory's own law, `dw/dt = γ(C − ε_w)`:
coherent context drills deeper, incoherent context collapses toward a shallower attractor. Do not
impose a hardcoded `w_max` or a per-trace amplitude ceiling — either one contradicts that equation
and blocks the deep band the dynamics are meant to reach. Amplitude balance is already governed by
the substrate: LTP (`COMP(term, term)`) raises a walked trace, LTD (`SHIFT` by η) fades an unwalked
one, and MCL collapse fires at `I_w < ε_w`. The winner-takes-all ratios are a consequence of those
operations, not of any external clamp. The number rising or falling tracks the complexity being
processed; a lower number caused by the system being run on simpler input is correct, not a fault.

## Teaching: feed, do not tune
Training is inherent — generation reinforces the traces it walks, and the dw/dt dynamics self-tune.
The environment is the only lever: what to feed, in what order, at what depth. Depth and ordering
of input set what the system can become. Spaced review prevents pruning of unwalked material.
Question-forms are their own paths and must be taught as such.

## Operational notes
`teach|` not `teach:` in the ops format (a colon drops the line as an unknown op). Background
daemons must be `setsid`-detached to survive between shell sessions. A shell timeout can fire while
a batch completes — verify via the daemon before re-running.
