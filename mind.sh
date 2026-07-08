#!/usr/bin/env bash
# mind.sh — MST door: talk to the THREE-PART MIND (Model Substrate Translation):
# memory line + observer line + the window law. It remembers, learns live,
# and persists as two lines. Unbounded replies — its own stop, always.
#
#     ./mind.sh            # talk; /recall <q>; /save; empty line exits+folds
#     ./mind.sh --fresh    # be born pristine
cd "$(dirname "$0")"
exec python3 hcl-ai/threemind.py "$@"
