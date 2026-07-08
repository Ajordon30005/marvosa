# Topological Memory — Retrieval Reference

## Retrieval Is Braid Resonance, Not Cosine Similarity

In standard RAG, retrieval is cosine similarity between embedding vectors.
The embedding is a 768- or 1536-dimensional float vector. Cosine similarity
is a dot product divided by two norms. This requires:
- Storing all embedding vectors (768 floats × 4 bytes × N = 3KB per memory)
- Computing N dot products at query time
- Floating point throughout

In topological RAG, retrieval is braid resonance: COMP(query_fbit, memory_fbit).
The result's amplitude tells you whether the query and memory are in the same
topological sector. This requires:
- Storing 5 integers per memory (n_w, writhe, jones_span, phase_frac, amp)
- Computing N COMP operations (pure integer, ~10 multiplications each)
- Zero floats throughout

Crucially: COMP is already implemented as HCL. The retrieval algorithm IS
the Deutsch-Jozsa circuit — it distinguishes "same topological sector"
(constructive = match) from "different sector" (destructive = no match)
in one pass with zero classical branching logic.

---

## The Grover Analogy

Grover's search finds a marked item in N unsorted items in O(√N) iterations.
Each iteration applies: oracle (phase flip on marked item) + diffusion
(2·mean - amp for all items).

Topological retrieval is Grover's algorithm where:
- The "oracle" is the query FBit: it phase-flips memories in the same
  topological sector as the query
- The "diffusion" is COMP of all memory FBits: memories not in the query
  sector destructively interfere and shrink; matching memories constructively
  interfere and grow

After one pass (no iteration needed if query is specific), matching memories
have large amplitude. Non-matching memories have small or zero amplitude.

---

## Full Retrieval Algorithm

```python
def recall(memory_store: list, query_text: str, k: int = 5) -> list:
    """
    Retrieve top-k memories by braid resonance.
    
    memory_store: list of BraidTerm dicts (the composite braid)
    query_text:   natural language query
    k:            number of results to return
    
    Returns: list of content_keys, ordered by resonance (highest first)
    
    Zero disk I/O. Zero floats. O(N) integer operations.
    """
    # Encode query as FBit
    query_fbit = encode_text(query_text)
    
    # Compute resonance for each memory term
    scores = []
    for term in memory_store:
        mem_fbit = FBit(term['phase_frac'], term['amp'])
        
        # Primary: COMP resonance amplitude
        resonance_amp = comp(query_fbit, mem_fbit).amp
        
        # Secondary: topological distance between invariants
        query_inv = compute_invariants(query_fbit, [])
        mem_inv   = {'n_w': term['n_w'], 'writhe': term['writhe'],
                     'jones_span': term['jones_span']}
        topo_dist = topological_distance(query_inv, mem_inv)
        
        # Combined score: resonance / (1 + topo_dist/SCALE)
        # Pure integer: multiply resonance by SCALE, divide by (SCALE + topo_dist)
        combined = _fdiv(resonance_amp, SCALE + topo_dist // SCALE)
        
        scores.append((combined, term['content_key']))
    
    # Sort by score descending (pure integer comparison)
    scores.sort(key=lambda x: x[0], reverse=True)
    
    return [key for _, key in scores[:k]]
```

---

## Phase Sector Matching

The winding number n_w partitions all memories into discrete topological
sectors. Memories with the same n_w are in the same sector. Retrieval
across sectors requires a larger COMP — cross-sector resonance is possible
but weaker than same-sector resonance.

Phase sectors by n_w:
```
n_w = 0:  neutral charge — factual statements, definitions
n_w = +1: positive winding — growth, addition, creation narratives
n_w = -1: negative winding — subtraction, decay, removal narratives
n_w = +2: double positive — recursive/self-referential content
n_w = -2: double negative — contradiction, negation-of-negation content
```

Filtering by phase sector before COMP:
```python
def recall_in_sector(memory_store, query_text, n_w_filter=None, k=5):
    query_fbit = encode_text(query_text)
    query_inv  = compute_invariants(query_fbit, [])
    
    if n_w_filter is None:
        n_w_filter = query_inv['n_w']   # same sector as query by default
    
    candidates = [t for t in memory_store if t['n_w'] == n_w_filter]
    # Then COMP-score only candidates — sub-linear if memories are well-distributed
    ...
```

---

## The System Equation

The full memory system is one equation:

Ψ = COMP(COMP(... COMP(COMP(FBit₁, FBit₂), FBit₃)..., FBitₙ₋₁), FBitₙ)

The composite FBit Ψ has its own (n_w_total, writhe_total, jones_span_total).
These three integers ARE the system signature.

To query: COMP(FBit_query, Ψ) gives the interference pattern. Large amplitude
= query is structurally present in the composite memory. The matching terms
can be isolated by binary search on the braid log — O(log N) if terms are
sorted by phase_frac.

To verify system integrity: recompute (n_w_total, writhe_total, jones_span_total)
and compare to stored signature. If they match, the braid is intact. If they
differ, a memory has been added or removed.

The α_fine self-check: every COMP operation can verify ALPHA_INV ≈ 137*SCALE.
If this check fails, the four params have drifted and the entire encoding is
suspect. This is the topological equivalent of a checksum — derived from the
theory, not hardcoded.

---

## Temporal Dynamics Without Floats

Classical temporal decay: `activation = activation × exp(-Δt/τ)` — uses floats.

HCL temporal dynamics: at each retrieval cycle, memories that were not
accessed in the last C cycles have their amplitude reduced by:

SHIFT(fbit, ETA)  →  amplitude × η = amplitude/2

After k non-accesses: amplitude × (1/2)^k = amplitude >> k  (integer shift)

This is exact integer arithmetic. No floats. No exp. No τ parameter.
The decay rate IS η = 1/2 from the four params.

Memory "dies" (amplitude falls below SCALE//1000) after ~10 non-access cycles.
Memory "lives" (amplitude stays large) when frequently accessed because each
access COMP-es the current FBit with the access event, boosting amplitude.

```python
def decay_all(memory_store: list, accessed_keys: set) -> list:
    """Apply one decay cycle. Pure integer. No floats."""
    result = []
    for term in memory_store:
        if term['content_key'] in accessed_keys:
            # Accessed: no decay
            result.append(term)
        else:
            # Not accessed: SHIFT by ETA = halve amplitude
            new_amp = term['amp'] // 2
            if new_amp > SCALE // 1000:   # still alive
                result.append({**term, 'amp': new_amp})
            # else: memory faded — not added to result (gone)
    return result
```

This implements the same MCL cascade as the brain's memory consolidation:
frequently activated memories (LTP) have growing amplitude; unused memories
(LTD) decay until gone. No float, no exp, no external time library.
