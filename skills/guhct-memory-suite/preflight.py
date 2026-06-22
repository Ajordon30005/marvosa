#!/usr/bin/env python3
"""
Preflight for guhct-memory-suite.
Confirms all three bundled skills are present and load on the shared substrate.
Run this first; then read the chosen bundled skill's own SKILL.md and preflight.
"""
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
B    = os.path.join(HERE, 'bundled')

CHECKS = [
    ('virtual-memory-hcl', 'scripts/hcl_memory.py', 'HCLMemory'),
    ('guhct-processor',    'scripts/juj.py',        'bytes_to_hvp'),
    ('guhct-living-memory','living_memory.py',      'LivingMemory'),
]

def load(skill, relpath):
    # make the bundled skills importable from their own dirs
    for sub in ('scripts', ''):
        p = os.path.join(B, skill, sub)
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    full = os.path.join(B, skill, relpath)
    spec = importlib.util.spec_from_file_location(
        f"{skill.replace('-','_')}_mod", full)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

print("GUHCT MEMORY SUITE — preflight")
print("=" * 50)
ok = True
for skill, rel, symbol in CHECKS:
    path = os.path.join(B, skill, rel)
    if not os.path.exists(path):
        print(f"  [MISSING] {skill}: {rel}"); ok = False; continue
    try:
        mod = load(skill, rel)
        has = hasattr(mod, symbol)
        # shared-substrate alpha check where the skill exposes it
        alpha = getattr(mod, 'ALPHA_INV', None)
        ascale = getattr(mod, 'SCALE', None)
        a = f"  alpha_inv={alpha/ascale:.1f}" if alpha and ascale else ""
        print(f"  [OK]      {skill}: {symbol} present{a}")
        ok &= has
    except Exception as e:
        print(f"  [FAIL]    {skill}: {e}"); ok = False

print("=" * 50)
print("suite ready." if ok else "suite has problems — see above.")
print("\nNext: pick a skill from SKILL.md's router table, then read")
print("bundled/<skill>/SKILL.md in full and run its own preflight.")
sys.exit(0 if ok else 1)
