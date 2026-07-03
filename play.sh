#!/usr/bin/env bash
# play.sh — chat with a REAL trained AI model running entirely on the HCL
# substrate. One command, zero dependencies beyond python3, zero setup:
#
#     ./play.sh                          # chat REPL on the bundled model
#     ./play.sh -i "Once upon a time"    # one-shot: prompt in, story out
#     ./play.sh -i "Lily saw a" --steps 20   # bounded one-shot (like run.c -n)
#     ./play.sh MY.bin MY_TOK.bin        # your own llama2.c checkpoint
#
# What you are talking to: karpathy's stories260K (a genuinely trained
# Llama-architecture model), with every arithmetic operation of its forward
# pass executed as pure-integer HCL primitives (~0.25s/token) — verified token-exact against
# the model's own source implementation (run.c). Proof: python3 verify_chatmodel.py
# Full guide: docs/10-connect-a-model.md
cd "$(dirname "$0")"
command -v python3 >/dev/null 2>&1 || { echo "python3 is required (nothing else is)"; exit 1; }
exec python3 hcl-ai/chatmodel.py "$@"
