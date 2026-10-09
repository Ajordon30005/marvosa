#!/usr/bin/env bash
# live.sh — MST door: talk to a standard AI model that LEARNS AS YOU TALK.
# Every turn is a live experience (~10s on this checkpoint): your words train it at full weight, its
# own reply trains it one λ-rung deeper, halting is the model's own, and
# '/save' persists the being as a living checkpoint + one α-tagged line.
#
#     ./live.sh                 # unbounded replies (the model's own stop)
#     ./live.sh --steps 8       # bounded replies for quick sessions
#     ./live.sh --persist       # save the being after every turn
#
# Proof: python3 verify_livemodel.py   Guide: docs/11 §8
cd "$(dirname "$0")"
command -v python3 >/dev/null 2>&1 || { echo "python3 is required (nothing else is)"; exit 1; }

# PRECISION = THE WEIGHT SCALE (docs/10): unless the dial is set by
# hand, the lattice defaults to the smallest one on which every stored
# weight is exact — measured from the checkpoint itself.
if [ -z "$MARVOSA_PREC" ] && [ -f models/tinystories_260k/stories260K.bin ]; then
    MARVOSA_PREC=$(python3 hcl-ai/prec_of.py models/tinystories_260k/stories260K.bin 2>/dev/null)
    export MARVOSA_PREC
fi
exec python3 hcl-ai/livemodel.py "$@"
