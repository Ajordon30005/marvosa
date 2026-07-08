#!/bin/sh
# PLUG AND PLAY — the skills' OWN tests, run verbatim. Nothing here is modified;
# this script only changes directory and invokes each skill's existing preflight
# exactly as shipped.
ROOT="$(cd "$(dirname "$0")" && pwd)"
set -e

echo "################################################################"
echo "## 1/5  hcl-pure — the skill's own preflight (verbatim)"
echo "################################################################"
cd "$ROOT/skills/hcl-pure/scripts" && python3 preflight.py

echo ""
echo "################################################################"
echo "## 2/5  guhct-memory-suite — router preflight (verbatim)"
echo "##      (loads all three engines, checks alpha_inv on each)"
echo "################################################################"
cd "$ROOT/skills/guhct-memory-suite" && python3 preflight.py

echo ""
echo "################################################################"
echo "## 3/5  virtual-memory-hcl — bundled preflight (verbatim)"
echo "################################################################"
cd "$ROOT/skills/guhct-memory-suite/bundled/virtual-memory-hcl/scripts" && python3 preflight.py

echo ""
echo "################################################################"
echo "## 4/5  guhct-processor — bundled preflight (verbatim)"
echo "################################################################"
cd "$ROOT/skills/guhct-memory-suite/bundled/guhct-processor/scripts" && python3 preflight.py

echo ""
echo "################################################################"
echo "## 5/5  guhct-living-memory — bundled preflight (verbatim)"
echo "################################################################"
cd "$ROOT/skills/guhct-memory-suite/bundled/guhct-living-memory" && python3 preflight.py

echo ""
echo "All five preflights ran verbatim. If every alpha_inv above reads 137.0,"
echo "the substrate is intact on this machine."
