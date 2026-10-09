#!/bin/sh
# PLUG AND PLAY CHAT — talk to the educated HCL-AI graduate from your terminal.
# Boots the student (which wakes the graduate and re-lives its full syllabus),
# waits for it to be ready, then drops you into a live ask/answer chat.
#
#     ./chat.sh            # boots the graduate daemon (once), then live chat
ROOT="$(cd "$(dirname "$0")" && pwd)"

# PRECISION = THE WEIGHT SCALE (docs/10): unless the dial is set by
# hand, the lattice defaults to the smallest one on which every stored
# weight is exact — measured from the checkpoint itself.
if [ -z "$MARVOSA_PREC" ] && [ -f "$ROOT"/models/tinystories_260k/stories260K.bin ]; then
    MARVOSA_PREC=$(python3 "$ROOT"/hcl-ai/prec_of.py "$ROOT"/models/tinystories_260k/stories260K.bin 2>/dev/null)
    export MARVOSA_PREC
fi
cd "$ROOT/hcl-ai"

# start the daemon detached if it isn't already up
if [ ! -S /tmp/hclai.sock ]; then
  echo "Waking the graduate (re-living its education — about a minute)..."
  setsid nohup python3 student_daemon.py > daemon.log 2>&1 < /dev/null &
  # wait until the socket is live and answering
  i=0
  while [ ! -S /tmp/hclai.sock ] && [ $i -lt 120 ]; do sleep 1; i=$((i+1)); done
  sleep 2
  # confirm it actually wakes (the daemon prints "student awake ...")
  i=0
  while ! grep -q "listening" daemon.log 2>/dev/null && [ $i -lt 120 ]; do sleep 1; i=$((i+1)); done
fi

python3 chat.py
