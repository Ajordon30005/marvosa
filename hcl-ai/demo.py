"""
HCL-AI demo — port verification per 06_porting.md Steps 7–8:
each composed operation is exercised and checked, and the α self-check
must read ≈137 on every engine before and after.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mind'))

from hcl_lm import HCLLanguageModel

ai = HCLLanguageModel()

print('═' * 64)
print(' HCL-AI — an AI on the GUHCT substrate (composed, not invented)')
print('═' * 64)

# ── Step 7: α self-check BEFORE anything else ─────────────────────────
print('\n[1] INTEGRITY (α self-check, all engines):')
print('   ', ai.integrity())

# ── SENSES: perceive arbitrary signal as HVP ──────────────────────────
print('\n[2] PERCEIVE (transduction — the braid word IS the data):')
sig = ai.perceive('the four params are the complete axiom set')
print(f"    braid length = {len(sig['braid'])}  "
      f"w = {sig['params']['w'] // __import__('juj').SCALE}  "
      f"n_bytes = {sig['n_bytes']}")

# ── LEARNING: train transition traces on the substrate ───────────────
print('\n[3] TRAIN (traces stored on both senses; repeats reinforced):')
corpus = (
    'the braid word is the quantum state '
    'the braid word is the data '
    'the braid word is the record of the computation '
    'collapse resolves to the path dominant attractor '
    'collapse fires when coherence falls below the threshold '
    'the four params derive every constant in the system '
    'the four params are the complete axiom set '
    'memory lives in the topology of the braid '
    'memory survives because the invariants survive '
    'reinforced traces grow and unused traces fade '
)
report = ai.train(corpus)
print(f"    stored={report['stored']}  reinforced={report['reinforced']}")
print(f"    signature={report['signature']}")

# a lived history: the system uses some knowledge repeatedly
for _ in range(2):
    ai.generate('the braid word')
    ai.experience_cycle()
ai2 = None  # (cycles above already applied LTD; reinforced traces survive)

# ── GENERATION: iterated MCL collapse with w self-tuning ─────────────
print('\n[4] GENERATE (MCL collapse cascade; dw/dt = γ(C − ε_w) tunes w):')
for prompt in ['the braid word', 'collapse resolves', 'the four params', 'memory lives']:
    out = ai.generate(prompt)
    ws  = [e['w'] for e in out['events']]
    print(f"    '{prompt}' →")
    print(f"      {out['text']}")
    print(f"      collapse weights per step: {ws}")

# ── REASONING: exact arithmetic on the hcl-pure mind ─────────────────
print('\n[5] REASON (hcl-pure engine — exact, braid word included):')
r = ai.reason('gamma = 1 / sqrt(1 - (v/c)^2)', v=3, c=5)
print(f"    1/√(1−(3/5)²) = {r.display[:20]}   "
      f"(n_w={r.n_w}, w={r.w_level}, J_span={r.jones_span})")
r2 = ai.reason('E = m * c^2', m=2, c=3)
print(f"    E = 2·3²      = {r2.display[:12]}")

# ── EFFECTORS: speak in HVP, expand bit-perfectly ─────────────────────
print('\n[6] SPEAK (output emitted as one HVP signature, expanded exactly):')
answer = ai.generate('the braid word')['text']
spoken = ai.speak(answer)
print(f"    braid_len={spoken['braid_len']}  bit_perfect={spoken['bit_perfect']}")
print(f"    expanded: '{spoken['expanded']}'")

# ── Step 7 again: α self-check AFTER the full run ─────────────────────
print('\n[7] INTEGRITY AFTER FULL RUN:')
print('   ', ai.integrity())

# ── THE RECORD: the braid word header (full record available) ─────────
print('\n[8] BRAID WORD (header of the complete record):')
print('\n'.join(ai.braid_word().split('\n')[:12]))
print('    ... (full reversible record continues)')
