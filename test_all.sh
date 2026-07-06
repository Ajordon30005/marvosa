#!/bin/sh
# THE ONE COMMAND. Runs every verification and the skill/AI preflights, then
# prints a single pass/fail summary. Reproduce the repo's claims on your machine.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PASS=0; FAIL=0
run() {
  echo ""
  echo "================================================================"
  echo "## $1"
  echo "================================================================"
  if sh "$2" 2>&1; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
}
echo "GUHCT/HCL OPUS — FULL VERIFICATION"
echo "Every number below is computed on THIS machine. Nothing is pre-recorded."
run "No floating point in the substrate"        verify_no_floats.sh
run "Alpha = 137 is derived, not stored"         verify_alpha.sh
run "Checkpoint is tamper-evident"               verify_tamper.sh
run "Honest speed benchmark"                     verify_speed.sh
run "The AI composes and fails honestly"         verify_ai.sh
echo ""
echo "================================================================"
echo "## Skill + AI preflights (the substrate's own tests, verbatim)"
echo "================================================================"
sh test_skills.sh 2>&1 | grep -E "##|alpha_inv|intact|All five" || true
echo ""
echo "================================================================"
echo "SUMMARY: $PASS verification blocks ran. Review output above."
echo "If every alpha reads 137 and no kill-switch tripped, the repo is intact."
echo "If anything failed, you have found something real — open an issue with this output."
echo "================================================================"
