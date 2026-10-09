#!/usr/bin/env bash
# calc.sh — the GUHCT collapse calculator (functionality only, no logging).
#   ./calc.sh "sin(pi/6)+sqrt(2)"
#   ./calc.sh --prog 'def f(theta,tape): return tape[0]+theta' --init 1
cd "$(dirname "$0")"
exec python3 hcl-ai/collapse_calc.py "$@"
