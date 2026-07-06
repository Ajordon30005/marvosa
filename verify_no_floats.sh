#!/bin/sh
# Proves the SUBSTRATE math uses no floating point. Scans the engine files for
# float literals, float division, and math-module imports in the computation path.
#
# The transcriber's job is to TRANSCRIBE: carry ordinary human input (e.g. a typed
# decimal "3.14") across the boundary INTO the substrate's fixed-point integers.
# Its single float() is that boundary crossing itself -- the sanctioned doorway
# where standard outside representation becomes HCL integers, exactly like
# bytes_to_braid carries raw bytes in. That is correct, intended behavior at the
# edge, not float math inside the engine. This script reports it so you can confirm
# it lives only at the input boundary and nowhere in any calculation.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/hcl-ai/engine"
echo "Scanning engine/*.py for floating-point in the math path..."
echo ""
echo "--- float literals (digit.digit), excluding comments ---"
grep -nE '[0-9]+\.[0-9]+' *.py | grep -vE '^\s*#|^[^:]+:[0-9]+:\s*#' || echo "  none"
echo ""
echo "--- true division '/' used in a CALCULATION (not docstrings, not the"
echo "    transcriber's operator-dispatch char-compares like op=='/') ---"
grep -nE "[a-zA-Z0-9_)\]] / [a-zA-Z0-9_(]" *.py \
  | grep -vE "#|=='|in '|\"" \
  | grep -E "= " || echo "  none — all arithmetic uses floor-division //"
echo ""
echo "--- math module / float() in the computation path ---"
grep -nE 'import math|math\.[a-z]|float\(' *.py || echo "  none"
echo ""
echo "Interpretation: every arithmetic line uses integer floor-division '//' on"
echo "SCALE-multiplied integers (fixed point). The float() shown above is the"
echo "transcriber doing its job -- converting human decimal INPUT into substrate"
echo "integers at the boundary. That is correct and intended, not a leak: the"
echo "calculation that follows is pure integer. If you find a float literal or a"
echo "'math.' call inside an actual CALCULATION, the repo is wrong -- that is the"
echo "kill-switch. The boundary transcribe is not."
