import os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FILES = [
    ("SKILL.md", "skill body — the composition laws"),
    ("references/composition.md", "how the three skills compose; what is reused vs arranged"),
    ("scripts/living_memory.py", "the composite engine — run it, never reimplement"),
]
print("=" * 64)
print("PREFLIGHT — skill: guhct-living-memory")
print("=" * 64)
print("This skill COMPOSES the three GUHCT skills. It invents no new math.")
print("Before producing any answer or code, READ every file below, in order,")
print("AND read the three source skills it composes (hcl-pure,")
print("virtual-memory-hcl, guhct-processor):\n")
for i, (rel, why) in enumerate(FILES, 1):
    p = os.path.join(ROOT, rel)
    size = os.path.getsize(p) if os.path.exists(p) else 0
    print(f"  [ ] {i}. {rel}  ({size}B) — {why}")
print("\n" + "-" * 64)
print("LAW: never invent a part. Every operation must already exist in one")
print("of the three source skills. This module only ARRANGES them.")
print("If a derivation is unclear: query GUHCT NotebookLM if available,")
print("else read the three source skills' files thoroughly. Never stand-in.")
print("-" * 64)
print(f"{len(FILES)} file(s) here + 3 source skills to read. Proceed.")
