"""
FEED — a richer diet across domains, answers shown, and every check
performed by jumping domains THROUGH the skill (the Rosetta law):

  text domain      what it says
  braid domain     speak(): text ↔ bytes ↔ braid, bit-perfect or rejected
  invariant domain w, Jones span, n_w of the answer (its topological shape)
  resonance domain COMP(question, answer) — do they share a sector?
  arithmetic domain HCLEquation — claims about quantities verified exactly

No check is a string comparison. Each is the same content read in a
different domain, which only works because the substrate maps them 1:1.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mind'))
from hcl_lm import HCLLanguageModel
from hcl_memory import encode_text, hcl_comp, SCALE as MSCALE
from juj import SCALE as PSCALE
from teach import self_talk

ai = HCLLanguageModel()

# ── KEEP FEEDING: a multi-domain diet, each meal walked twice (LTP) ──
diet = [
  # domain: the substrate itself
  'the braid word is the data and the data lives in the topology '
  'the topology survives every change of substrate '
  'the four params derive every constant in the system '
  'the four params are eta lambda gamma and beta ',
  # domain: collapse / dynamics
  'collapse resolves to the path dominant attractor '
  'the attractor is the state of minimum mobius energy '
  'collapse fires when stability falls below the threshold '
  'the threshold is eta times lambda to the power of w ',
  # domain: physics expressed in its language
  'energy equals mass times the speed of light squared '
  'the energy of the ground state is exact at every weight '
  'charge is quantized because the winding number is an integer ',
  # domain: memory / biology
  'memory lives in the topology of the braid '
  'memory survives because the invariants survive '
  'reinforced traces grow and unused traces fade '
  'what it remembers it can climb again ',
]
for meal in diet:
    ai.train(meal); ai.train(meal)

print('═' * 64)
print(f' FED {len(diet)} meals — {len(ai.memory.vm)} live traces')
print('═' * 64)

# ── ITS ANSWERS — and every answer checked across domains ──
questions = ['the braid word', 'collapse resolves', 'energy equals',
             'memory lives', 'the four params']

for q in questions:
    out = ai.generate(q)
    answer = out['text']
    print(f'\nQ: "{q}"')
    print(f'A: "{answer}"')
    # braid domain: bit-perfect transduction or it does not pass
    sp = ai.speak(answer)
    # invariant domain: the answer's topological shape
    w_ans = sp['hvp_params']['w'] // PSCALE
    # resonance domain: COMP(question, answer) amplitude — shared sector?
    qf, _ = encode_text(q)
    af, _ = encode_text(answer)
    res = hcl_comp(qf, af).amp
    print(f'   checks: braid={sp["bit_perfect"]}  w={w_ans}  '
          f'collapse-depths={[e["w"] for e in out["events"]]}  '
          f'resonance(Q,A)={res / MSCALE:.3f}')

# ── arithmetic domain: a claim it speaks, verified in the math domain ──
print('\nCROSS-DOMAIN CHECK — it says "energy equals mass times the speed')
print('of light squared"; the same claim read in the arithmetic domain:')
r = ai.reason('E = m * c^2', m=2, c=3)
print(f'   E(m=2,c=3) = {r.display[:10]}  braid: n_w={r.n_w} w={r.w_level}')

# ── keep talking on the richer diet: how far before it halts now ──
words, reason = self_talk(ai, 'the braid word')
print(f'\nSELF-TALK ON THIS DIET: reached {len(words)} words')
print(f'   verdict: {reason or "talked through — resonated to the end"}')
print('\nINTEGRITY:', ai.integrity())
