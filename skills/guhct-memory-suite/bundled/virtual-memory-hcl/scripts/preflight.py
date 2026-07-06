#!/usr/bin/env python3
"""
Preflight for a GUHCT/HCL skill.

Run this FIRST, before doing the task. It does two things:

  1. Prints every file in this skill that must be read before producing any
     answer or code. Reading them is mandatory — this skill does not work from
     memory.

  2. States the tool-availability rule for theory gaps. (Python cannot detect
     which tools you, the model, have — so this is a rule for you to apply, not
     an automated check.)

It has no dependencies and never fails the task; it only reports.
"""

import os
import sys

SELF = os.path.abspath(__file__)
SKILL_DIR = os.path.dirname(os.path.dirname(SELF))   # scripts/.. == skill root
SKILL_NAME = os.path.basename(SKILL_DIR)

SKIP_DIRS = {'__pycache__', '.git'}
SKIP_NAMES = {os.path.basename(SELF)}


def collect_files():
    """All readable files in the skill, SKILL.md first, then references, then
    scripts, then the rest. Returns list of (relpath, size_bytes)."""
    found = []
    for root, dirs, files in os.walk(SKILL_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f in SKIP_NAMES:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, SKILL_DIR)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = -1
            found.append((rel, size))

    def rank(item):
        rel = item[0]
        if rel == 'SKILL.md':
            return (0, rel)
        if rel.startswith('references' + os.sep):
            return (1, rel)
        if rel.startswith('scripts' + os.sep):
            return (2, rel)
        return (3, rel)

    return sorted(found, key=rank)


def main():
    files = collect_files()
    bar = '=' * 64
    print(bar)
    print(f"PREFLIGHT — skill: {SKILL_NAME}")
    print(bar)
    print("This skill does NOT work from memory. Before producing any answer")
    print("or code, READ every file listed below, in order:\n")

    for i, (rel, size) in enumerate(files, 1):
        sz = f"{size:,}B" if size >= 0 else "unreadable"
        print(f"  [ ] {i:>2}. {rel}  ({sz})")

    print()
    print("-" * 64)
    print("THEORY-GAP RULE (apply this yourself — not auto-detectable here):")
    print("  - If a NotebookLM query tool IS available to you, you may query")
    print("    the GUHCT NotebookLM source for anything the files don't cover.")
    print("  - If such a tool is NOT available, do NOT stall or fail. Continue")
    print("    the task and rely on reading every file above thoroughly.")
    print("  - Either way: never invent a stand-in formula.")
    print("-" * 64)
    print(f"{len(files)} file(s) to read. Preflight complete — proceed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
