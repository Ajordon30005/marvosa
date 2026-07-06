#!/bin/sh
# PLUG AND PLAY — the AI's OWN demonstration, run verbatim. Nothing here is
# modified; this script only invokes hcl-ai/demo.py exactly as shipped:
# integrity (alpha=137 on every engine), perception (text -> braid), training,
# generation (MCL collapse cascade with live w-tuning), exact reasoning,
# the one-line checkpoint, and tamper rejection.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/hcl-ai" && python3 demo.py

echo ""
echo "----------------------------------------------------------------"
echo "To CHAT with the graduate yourself (type prompts, read answers):"
echo "  ./chat.sh"
echo "----------------------------------------------------------------"
