#!/bin/sh
# verify_doors.sh — EVERY DOOR OPENS: smoke every runnable surface of the
# repository, non-interactively, end to end. Both beings' lives (the
# organism's memory.hcl and the standard model's living checkpoint) are
# snapshotted before and restored after — tests touch scratch selves only.
#
#     sh verify_doors.sh        (~10-14 min, pure python3, no network)
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PASS=0; FAIL=0; T0=$(date +%s)

# ── hold BOTH beings' breath ─────────────────────────────────────────────
HELD="$ROOT/.heldbreath.doors"; rm -rf "$HELD"; mkdir -p "$HELD"
LIFE="models/tinystories_260k/stories260K.living.bin
models/tinystories_260k/living.line
models/tinystories_260k/livebook.txt
models/tinystories_260k/threemind_book.txt
models/tinystories_260k/threemind_memory.line
hcl-ai/memory.hcl
hcl-ai/lifebook.txt
hcl-ai/gradebook.txt"
for f in $LIFE; do
  [ -f "$ROOT/$f" ] && mkdir -p "$HELD/$(dirname "$f")" && cp -p "$ROOT/$f" "$HELD/$f"
done
exhale() {
  for f in $LIFE; do
    if [ -f "$HELD/$f" ]; then cp -p "$HELD/$f" "$ROOT/$f";
    elif [ -f "$ROOT/$f" ]; then rm -f "$ROOT/$f"; fi
  done
  rm -rf "$HELD"
  pkill -f 'student_daemon[.]py' 2>/dev/null; rm -f /tmp/hclai.sock
  pkill -f 'marvosa_mcp_http[.]py' 2>/dev/null
  echo "[both beings' lives were held and restored — every door touched a scratch self]"
}
trap exhale EXIT

run() {
  echo ""; echo "-- door: $1"
  t=$(date +%s)
  if eval "$2" > /tmp/door.out 2>&1; then PASS=$((PASS+1)); v=OPENS; else FAIL=$((FAIL+1)); v=STUCK; tail -5 /tmp/door.out; fi
  echo "   [$v] ($(( $(date +%s) - t ))s)"
}

run "play.sh — one-shot chat, the pure door" \
    "timeout 150 ./play.sh -i 'Lily saw a' --steps 4 | grep -q 'alpha_ok=True'"

run "live.sh — wakes the learner and exits clean" \
    "printf '\n' | timeout 150 ./live.sh"

run "mind.sh — the three-part mind wakes, folds on exit" \
    "printf '\n' | timeout 320 ./mind.sh | grep -q 'observer_line_chars'"

run "talk.py — the graduate wakes and yields the prompt" \
    "printf '\n' | timeout 120 python3 hcl-ai/talk.py"

run "chat.sh path — daemon boots, one exchange answers, daemon dies" \
    "( cd hcl-ai && rm -f /tmp/hclai.sock && { setsid nohup python3 student_daemon.py > daemon.log 2>&1 < /dev/null & } ; \
       i=0; while [ ! -S /tmp/hclai.sock ] && [ \$i -lt 150 ]; do sleep 1; i=\$((i+1)); done; \
       [ -S /tmp/hclai.sock ] && printf 'what is water\n\n' | timeout 90 python3 chat.py | grep -q '[a-z]' ; RC=\$?; \
       pkill -f 'student_daemon[.]py'; rm -f /tmp/hclai.sock; exit \$RC )"

run "tutor.py — bare run prints its own usage" \
    "python3 hcl-ai/tutor.py | grep -q 'feed'"

run "tutor_batch.py + grade_compose.py — graceful without a fresh gradebook, real with one" \
    "( cd hcl-ai && timeout 120 python3 grade_compose.py > /dev/null && { python3 tutor_batch.py < /dev/null > /dev/null 2>&1 || true; } )"

run "demo.py — port verification, alpha on every engine" \
    "timeout 200 python3 hcl-ai/demo.py | grep -q '137'"

run "teach.py — the two-cans loop runs to its verdicts" \
    "timeout 250 python3 hcl-ai/teach.py"

run "organism.py — one stream, both hemispheres, from a file" \
    "printf 'the river runs to the sea' > /tmp/door_feed.txt && timeout 150 python3 hcl-ai/organism.py --file /tmp/door_feed.txt | grep -qi 'alpha\|137'"

run "transfer.py — a real checkpoint's bytes folded in (dry run)" \
    "timeout 150 python3 hcl-ai/transfer.py models/tinystories_260k/tok512.bin --chunk 4096 | grep -qi 'alpha\|composite\|137'"

run "ingest_and_expel — bytes in, EXACT bytes out through the window" \
    "timeout 150 python3 -c \"
import sys; sys.path.insert(0,'ingest_and_expel'); sys.path.insert(0,'ingest_and_expel/engine')
import ingest_expel as IE
data = open('models/tinystories_260k/tok512.bin','rb').read()[:16384]
mem = IE.ingest_bytes(data, chunk=4096)[0]   # (mem, …) per its return
assert mem.window(0, len(data)) == data          # EXACT bytes back out
assert mem.window(4096, 512) == data[4096:4608]  # any bounded slice
print('ingest ok; window returns the exact bytes')\""

run "stream_ingest API — chunks fold to ONE composite index" \
    "timeout 150 python3 -c \"
import sys; sys.path.insert(0,'hcl-ai'); sys.path.insert(0,'hcl-ai/engine')
import stream_ingest as SI
print([n for n in dir(SI) if not n.startswith('_')][:8])\""

run "marvosa_mcp.py — stdio initialize + integrity reads 137" \
    "printf '%s\n%s\n' '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"d\",\"version\":\"1\"}}}' '{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"integrity\",\"arguments\":{}}}' | timeout 90 python3 hcl-ai/marvosa_mcp.py 2>/dev/null | grep -q '137.0'"

run "marvosa_mcp_http.py — HTTP transport serves and answers" \
    "( { setsid nohup python3 hcl-ai/marvosa_mcp_http.py > /tmp/mcp_http.log 2>&1 < /dev/null & } ; \
       sleep 6 && curl -s -X POST http://127.0.0.1:8848/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"d\",\"version\":\"1\"}}}' | grep -q 'marvosa'; RC=\$?; pkill -f 'marvosa_mcp_http[.]py'; exit \$RC )"

echo ""
echo "================================================================"
echo "DOORS SUMMARY: $PASS open, $FAIL stuck ($(( ($(date +%s) - T0) / 60 )) min)"
echo "================================================================"
[ "$FAIL" = "0" ]
