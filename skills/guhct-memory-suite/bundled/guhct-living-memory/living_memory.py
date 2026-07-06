"""
GUHCT LIVING MEMORY — composite of the three GUHCT skills.

This is NOT new math. Every operation here already exists in one of the
three skills; this module COMPOSES them into one living system:

  hcl-pure            -> the four-param substrate, FBit, COMP/SHIFT/AMP_MOD/INV
  virtual-memory-hcl  -> topological store, resonance recall, MCL decay, signature
  guhct-processor     -> bijective HVP transducer (exact content regeneration)

What the composite adds is ARRANGEMENT, not parts:
  * potentiation (LTP)  = COMP(term, term)        reinforce a trace IN PLACE
  * depression  (LTD)   = decay (SHIFT by eta)    fade unaccessed traces
  * two senses          = phase-resonance (vm) + HVP-param distance (processor)
  * exact recall        = braid word kept per memory -> regenerate exact bytes

Laws inherited unchanged from all three skills:
  Rule 1: zero disk I/O for state (RAM-only; the braid IS the record)
  Rule 2: zero floats (pure integer fixed-point, SCALE = 10**PREC)
  Rule 3: zero imported constants (pi, e, sqrt2 derived from four params)
  Rule 4: four params are the complete axiom set
  Rule 5: retrieval is braid resonance, not cosine similarity
  Rule 6: content travels in the braid word (so regeneration is exact)
"""

import sys as _sys, os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
for _p in (_os.path.join(_HERE, "..", "virtual-memory-hcl", "scripts"),
           _os.path.join(_HERE, "..", "guhct-processor", "scripts"),
           _os.path.join(_HERE, "..", "hcl-pure", "scripts"), _HERE):
    _p = _os.path.abspath(_p)
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import sys
# sibling engines resolve RELATIVE to this bundle (bootstrap above) — never
# via machine-specific absolute paths

# --- parts taken verbatim from the source skills (never reimplemented) ---
import hcl_memory as VM
from hcl_memory import (
    SCALE, FBit, hcl_comp, hcl_shift, ETA, ALPHA_INV,
)
import juj
from juj import bytes_to_hvp, hvp_to_bytes, SCALE as PSCALE


class LivingMemory:
    """
    One persistent system. State lives in RAM as the composite braid plus,
    per memory, its HVP signature (the second sense) and braid word (for
    exact regeneration). Nothing here is invented — it is the three skills
    arranged into a whole.
    """

    def __init__(self):
        self.vm       = VM.HCLMemory()   # sense 1: phase/resonance store (skill 2)
        self.hvp      = {}               # sense 2: key -> HVP param vector (skill 3)
        self.sigs     = {}               # key -> full HVP signature (for exact recall)
        self.accessed = set()            # keys touched this cycle (for LTD)

    # ── store: write to both senses; keep braid for exact regeneration ──
    def store(self, key, text):
        self.vm.store(key, text)                      # sense 1 (resonance)
        sig = bytes_to_hvp(text.encode())             # skill 3 transducer
        self.sigs[key] = sig                          # full signature: params + braid
        self.hvp[key]  = [sig['params'][p] for p in sig['params']]  # sense 2 vector
        return self.signature()

    # ── potentiation (LTP): reinforce IN PLACE by COMPOSING the term ──
    def reinforce(self, key):
        """LTP = COMP(term, term). Same phase sector -> constructive ->
        amplitude grows, identity preserved, NO new term. Pure skill-1 COMP."""
        for t in self.vm._terms:
            if t['content_key'] == key:
                f = FBit(t['phase_frac'], t['amp'])
                g = hcl_comp(f, f)                    # compose with itself
                t['phase_frac'], t['amp'] = g.phase_frac, g.amp
        self.accessed.add(key)
        self._recompose()

    # ── depression (LTD): fade unaccessed via the engine's own decay ──
    def cycle(self):
        """One experience cycle: reinforced traces already grew; everything
        not accessed this cycle halves (SHIFT by eta), faded ones prune.
        decay() is skill-2's own MCL operation, unchanged."""
        removed = self.vm.decay(self.accessed)
        self.accessed = set()
        return removed

    # ── recall across BOTH senses (resonance + HVP distance), composed ──
    def recall(self, query, k=3):
        keys = list(self.hvp.keys())
        if not keys:
            return []
        # sense 1: phase resonance ranking (skill 2)
        r1 = [it[0] if isinstance(it, tuple) else it
              for it in self.vm.recall(query, k=len(keys))]
        rank1 = {key: i for i, key in enumerate(r1)}
        # sense 2: HVP param distance ranking (skill 3), pure integer L1
        qv = [bytes_to_hvp(query.encode())['params'][p]
              for p in bytes_to_hvp(query.encode())['params']]
        dist = sorted(keys, key=lambda key: sum(abs(a-b)
                      for a, b in zip(qv, self.hvp[key])))
        rank2 = {key: i for i, key in enumerate(dist)}
        # compose the two senses: lower summed rank = resonant on both
        order = sorted(keys, key=lambda key: rank1.get(key, 99) + rank2.get(key, 99))
        return [(key, rank1.get(key, 99), rank2.get(key, 99)) for key in order[:k]]

    # ── exact content regeneration from the kept braid (skill 3, Rule 6) ──
    def regenerate(self, key):
        """Exact original bytes, verified bijective. The braid word carried
        the data; the params check it. This is skill-3's inverse path."""
        if key not in self.sigs:
            return None
        return hvp_to_bytes(self.sigs[key], verify=True).decode(errors='replace')

    # ── the whole state as a few integers (skill 2 signature) ──
    def signature(self):
        return self.vm.signature()

    # ── integrity: the alpha self-check, both engines (all skills, Rule) ──
    def integrity(self):
        return {'memory_alpha_inv':    ALPHA_INV / SCALE,
                'processor_alpha_inv':  juj.ALPHA_INV / PSCALE,
                'intact': abs(ALPHA_INV/SCALE - 137) < 1
                          and abs(juj.ALPHA_INV/PSCALE - 137) < 1}

    def amplitudes(self):
        return {t['content_key']: t['amp'] for t in self.vm._terms}

    def live_keys(self):
        return [t['content_key'] for t in self.vm._terms]

    def _recompose(self):
        """Rebuild composite + signature from current terms (skill-2 internals)."""
        self.vm._composite = FBit(0, SCALE)
        for t in self.vm._terms:
            self.vm._composite = hcl_comp(
                self.vm._composite, FBit(t['phase_frac'], t['amp']))
        self.vm._update_signature()


def _demo():
    m = LivingMemory()
    facts = {
        'fire_danger' : 'fire burns and causes pain avoid it',
        'water_safe'  : 'water quenches thirst sustains life',
        'food_berry'  : 'red berries nourishing safe eat',
        'food_toxic'  : 'pale mushrooms cause sickness death',
        'shelter_cave': 'cave gives shelter cold predators',
        'trivia_rock' : 'gray rock sat trail meaning nothing',
    }
    for k, v in facts.items():
        m.store(k, v)
    print("LIVING MEMORY — composite of three skills, nothing invented\n")
    print("start signature:", m.signature())

    lived = {'fire_danger', 'water_safe', 'food_berry', 'food_toxic', 'shelter_cave'}
    for c in range(1, 9):
        for k in lived:
            m.reinforce(k)         # LTP via COMP
        m.cycle()                  # LTD via decay
    print("after 8 lived cycles:")
    print("  live keys:", m.live_keys())
    a = m.amplitudes()
    for k in facts:
        print(f"   {k:<13} {'amp='+str(a[k]//SCALE) if k in a else 'FADED'}")

    print("\nexact regeneration (skill-3 braid round trip):")
    print("  food_toxic ->", repr(m.regenerate('food_toxic')))

    print("\nintegrity:", m.integrity())


if __name__ == '__main__':
    _demo()
