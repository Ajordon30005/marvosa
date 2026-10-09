#!/usr/bin/env bash
# bootstrap_1b.sh — ZERO TO BILLION-PARAMETER HOLOGRAPHIC IDENTITY.
# Run in an environment whose network allowlist includes:
#   huggingface.co  cdn-lfs.huggingface.co  cdn-lfs-us-1.hf.co
#   cas-bridge.xethub.hf.co  transfer.xethub.hf.co
#
#     ./bootstrap_1b.sh          # fetch TinyLlama-1.1B (2.2 GB) and fold it
#                                # into ONE alpha-tagged line via MST intake
#
# Target: TinyLlama/TinyLlama-1.1B-Chat-v1.0 — 1,100,048,384 params,
# dim 2048, 22 layers, 32 heads (GQA kv=4), vocab 32000, bfloat16
# safetensors (the dock's native format). Expected: download minutes;
# intake ~90-120 min at the measured ~0.4 MB/s transduction — run it
# detached and pour a coffee; the line at the end is ~150 chars and ends
# in the alpha seal, same as a 1 MB toy.
cd "$(dirname "$0")"
set -e
mkdir -p models/tinyllama_1b
B=models/tinyllama_1b
[ -f "$B/model.safetensors" ] || curl -L --fail -o "$B/model.safetensors" \
  https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0/resolve/main/model.safetensors
[ -f "$B/tokenizer.model" ] || curl -L --fail -o "$B/tokenizer.model" \
  https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0/resolve/main/tokenizer.model
ls -la "$B"
exec python3 hcl-ai/holo_intake.py "$B/model.safetensors" --chunk 4194304
