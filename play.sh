#!/usr/bin/env bash
# play.sh — MST door: chat with a REAL trained AI model running entirely on the HCL
# substrate. One command, zero dependencies beyond python3, zero setup:
#
#     ./play.sh                          # chat REPL on the bundled model
#     ./play.sh -i "Once upon a time"    # one-shot: prompt in, story out
#     ./play.sh -i "Lily saw a" --steps 20   # bounded one-shot (like run.c -n)
#     ./play.sh MY.bin MY_TOK.bin        # your own llama2.c checkpoint
#
# What you are talking to: karpathy's stories260K (a genuinely trained
# Llama-architecture model), with every arithmetic operation of its forward
# pass executed as pure-integer HCL primitives (~0.12s/token, ~8.7 tok/s) — verified token-exact against
# the model's own source implementation (run.c). Proof: python3 verify_chatmodel.py
# Full guide: docs/10-connect-a-model.md
cd "$(dirname "$0")"
command -v python3 >/dev/null 2>&1 || { echo "python3 is required (nothing else is)"; exit 1; }

# PRECISION = THE WEIGHT SCALE (docs/10): unless the dial is set by
# hand, the lattice defaults to the smallest one on which every stored
# weight is exact — measured from the checkpoint itself.
if [ -z "$MARVOSA_PREC" ] && [ -f models/tinystories_260k/stories260K.bin ]; then
    MARVOSA_PREC=$(python3 hcl-ai/prec_of.py models/tinystories_260k/stories260K.bin 2>/dev/null)
    export MARVOSA_PREC
fi

# Hands-free model choice: with no arguments, every translated model under
# models/ is discovered (a checkpoint *.bin next to its tok*.bin). One found:
# it runs. Several found: pick by number. Arguments always pass through.
if [ "$#" -eq 0 ]; then
    PAIRS=""
    for d in models/*/; do
        m=$(ls "$d" 2>/dev/null | grep -E '\.bin$' | grep -v '^tok' | grep -v living | head -1)
        t=$(ls "$d" 2>/dev/null | grep -E '^tok.*\.bin$' | head -1)
        [ -n "$m" ] && [ -n "$t" ] && PAIRS="$PAIRS$d$m $d$t\n"
    done
    N=$(printf "$PAIRS" | grep -c .)
    if [ "$N" -gt 1 ]; then
        echo "Translated models found:"
        i=1
        printf "$PAIRS" | while read -r mm tt; do echo "  $i) $mm"; i=$((i+1)); done
        printf "which model? [1-%s] " "$N"; read -r CH
        SEL=$(printf "$PAIRS" | sed -n "${CH:-1}p")
        exec python3 hcl-ai/chatmodel.py $SEL
    elif [ "$N" -eq 1 ]; then
        SEL=$(printf "$PAIRS" | sed -n 1p)
        echo "one translated model found: ${SEL%% *}"
        exec python3 hcl-ai/chatmodel.py $SEL
    fi
fi
exec python3 hcl-ai/chatmodel.py "$@"
