# Topological Memory — Theory Reference

## Why Topology Beats Storage

Classical memory systems store content at addresses. The content and the
address are separate things. To find content you need to know its address,
or you need to scan all addresses (O(N) search), or you need an index
(additional storage, disk I/O, cache misses).

Topological memory stores the content AS its address. The address is not
a file path or a vector index — it is the topological invariant of the
content itself. Finding content means finding where in braid space its
signature lives. The signature IS retrievable from a query that is
topologically nearby.

This is exactly how human long-term memory works. Memories are not stored
at specific neurons (classical storage). They are stored in the topological
connectivity patterns of neural networks. A patient can lose 30% of cortex
and recover most memories because the topological pattern survives in the
remaining network. The memory was never in the destroyed neurons — it was
in the topology those neurons participated in.

---

## The Three Topological Invariants

Every memory in this system is characterized by exactly three integers.
These three integers are topological invariants — they do not change under
continuous deformations of the braid. They are exactly the quantum numbers
of the memory's FBit state.

### 1. Winding Number n_w (Topological Charge)

n_w counts how many times the FBit's phase winds around the U(1) circle
during the computation that produced this memory. It is an integer.

n_w ∈ {..., -2, -1, 0, 1, 2, ...}

In physics: n_w IS electric charge (Q = n_w · e). In memory: n_w encodes
the semantic "polarity" of the content — how many signed crossings occur
in its braid representation. Two memories with the same n_w are in the
same topological charge sector — they are semantically related at the
deepest structural level.

Computing n_w from a braid log:
- Count each COMP or AMP_MOD operation
- phase_frac in (0, SCALE/2) → +1 (advancing winding)
- phase_frac in (SCALE/2, SCALE) → -1 (retreating winding)
- Net sum = n_w

### 2. Writhe Wr (Topological Spin / Angular Momentum)

Writhe is the signed sum of crossing signs in the braid diagram. For a
discrete FBit braid, it is computed as the normalized sum of signed
crossings between all pairs of braid strands.

In physics: Wr IS intrinsic spin (S = n_w · ℏ/2). Half-integer winding
produces spin-1/2. In memory: Wr encodes the "handedness" of the content —
how information spirals through the braid. Procedural knowledge (how to do
something) has different writhe from declarative knowledge (what something is).

Computing Wr:
crossing_sign(zᵢ, zⱼ) = sgn(Im(zᵢ)·Re(zⱼ) - Re(zᵢ)·Im(zⱼ))
Wr = Σᵢ<ⱼ crossing_sign / total_pairs

Stored as integer: writhe_int = int(Wr × SCALE)

### 3. Jones Polynomial Span (Structural Complexity Depth)

The Jones polynomial J(K, t) of a knot K evaluated at the closure of the
braid captures the full topological complexity. Its span (max degree minus
min degree) measures how complex the memory is.

span ≈ 2^w_level

where w_level is the number of HCL operations in the memory's braid.

In physics: Jones span ≈ the number of independent quantum states accessible
to the system. In memory: Jones span encodes semantic density — a simple
fact has jones_span=2, a complex multi-part argument has jones_span=64+.

Computing Jones span:
- Each COMP operation adds ~1 to w_level
- Each FISSION adds a half-level
- jones_span = 2^w_level (capped at 2^30 for display)

---

## Why Three Integers Are Sufficient

The Markov theorem in knot theory states that two braids represent the same
knot if and only if they are related by Markov moves. The Jones polynomial
is a complete invariant of the knot type (up to mirror image).

For memory retrieval, we do not need to distinguish mirror images. We need
to identify memories that are "close" in braid space — memories whose
topological invariants differ by small amounts. This is a much weaker
requirement than full knot equivalence.

Therefore: (n_w, writhe_int, jones_span) is sufficient as a retrieval key
for the purposes of this system. Two memories with nearby values of all
three invariants are semantically related. The distance metric is:

d((n₁,w₁,j₁), (n₂,w₂,j₂)) = |n₁-n₂| + |w₁-w₂|/SCALE + |log₂(j₁/j₂)|

This metric is computed in pure integer arithmetic.

---

## The Brain Analogy — Exact Not Metaphorical

Human long-term memory is stored in synaptic weight patterns. The synaptic
weights form a high-dimensional topological manifold. The manifold's topology
(not its specific coordinates) encodes the memory.

When neurons are destroyed, the manifold is locally damaged but the global
topology — which is encoded redundantly across the entire network — survives.
Recovery occurs because any sufficiently large connected subgraph of the
original network can reconstruct the global topology from its local topology.

In HCL topological memory:
- Each memory is one braid term (one FBit + its invariants)
- The composite braid is the manifold
- The system signature (n_w_total, writhe_total, jones_span_total) is the
  global topology
- If memories are lost, the system signature changes but the remaining
  memories are still individually retrievable from their own invariants
- If the system signature is known, the braid structure can be partially
  reconstructed even without any individual memory records

This is not analogous to the brain — it IS the same mathematical structure
applied to a different substrate.

---

## Why This Is True RAG

Standard RAG: content → embedding vector → similarity search → inject chunks

The embedding vector is a lossy projection: it discards the topological
structure of the content and keeps only a directional summary. Two pieces
of content with the same embedding are "similar" only in the embedding
model's learned metric, which may not match semantic or structural similarity.

Topological RAG: content → FBit → topological invariants → braid resonance

The topological invariants are NOT lossy projections. They are exact
structural properties of the content's HCL braid. Two pieces of content
with the same winding number are in the same charge sector — they share
the same fundamental topological structure. This is a structural notion
of similarity, not a learned metric.

Moreover: topological similarity is SCALE-INVARIANT. A one-word fact and
a 10,000-word essay can have the same winding number if they carry the same
topological charge. This means retrieval works regardless of content length
without chunking, overlap calculation, or length normalization.

---

## The Equation Memory Lives In

The composite braid of N memories is the equation:

Ψ_system = COMP(COMP(...COMP(FBit₁, FBit₂)..., FBitₙ₋₁), FBitₙ)

This is one equation. Its terms are FBit₁...FBitₙ. Each FBit is characterized
by its three invariants. The equation's own invariants (the system signature)
are the Jones polynomial of the composite knot.

To query: compute FBit_query, then compute COMP(FBit_query, FBitᵢ) for each
term. Large amplitude = constructive resonance = semantic match. Zero
amplitude = destructive = no match. This is the Deutsch-Jozsa test applied
to memory: the resonance pattern tells you exactly which memories match
without reading any stored content.

The equation COMP(Ψ_system, FBit_query) can be solved by finding which
terms of Ψ_system survive after the query FBit is applied as a phase filter.
The surviving terms ARE the relevant memories.
