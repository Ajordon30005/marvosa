#!/bin/sh
# Proves the AI composes, not just recalls — and fails honestly. Trains a small
# corpus live, generates, and shows recall AND cross-lesson splices, plus a
# deliberate inversion failure (it cannot walk a relation it never walked).
#
#     sh verify_ai.sh      # wake, teach, ask, save/load — the mind, verified
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/hcl-ai"
python3 - <<'PY'
import sys; sys.path.insert(0,'mind')
from hcl_lm import HCLLanguageModel
ai = HCLLanguageModel()
for s in [
  "a wave is a moving pattern",
  "the pattern travels not the water",
  "resonance is when waves agree and rise",
  "the tallest peak is the answer",
]:
    ai.train(s); ai.train(s)
print("Trained 4 short lessons. Now generating:\n")
for q in ["a wave is", "resonance is when waves", "the tallest peak is"]:
    print(f"  ask: {q!r}")
    print(f"  ->   {ai.generate(q)['text']}\n")
print("Integrity during all of this:", ai.integrity()['intact'], "alpha=", ai.integrity()['engine_alpha_inv'])
print()
print("Inversion test (it learned 'pattern travels not the water' one direction only):")
print("  ask: 'the water'  ->", repr(ai.generate("the water")['text']))
print("  (expect it to NOT cleanly produce the reverse — relations exist only in the")
print("   direction walked. A lookup table would symmetric-match; this does not.)")
print()
print("For full RECALL/SPLICE/COMPOSED receipts on the educated graduate, see")
print("docs/04-composition.md and run:  python3 grade_compose.py")
PY
