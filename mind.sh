#!/usr/bin/env bash
# mind.sh — MST door: talk to the THREE-PART MIND (Model Substrate Translation):
# memory line + observer line + the window law. It remembers, learns live,
# and persists as two lines. Unbounded replies — its own stop, always.
#
#     ./mind.sh            # talk; /recall <q>; /save; empty line exits+folds
#     ./mind.sh --fresh    # be born pristine
cd "$(dirname "$0")"

# PRECISION = THE WEIGHT SCALE (docs/10): unless the dial is set by
# hand, the lattice defaults to the smallest one on which every stored
# weight is exact — measured from the checkpoint itself.
if [ -z "$MARVOSA_PREC" ] && [ -f models/tinystories_260k/stories260K.bin ]; then
    MARVOSA_PREC=$(python3 hcl-ai/prec_of.py models/tinystories_260k/stories260K.bin 2>/dev/null)
    export MARVOSA_PREC
fi
exec python3 hcl-ai/threemind.py "$@"
