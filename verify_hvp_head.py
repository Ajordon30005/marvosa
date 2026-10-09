#!/usr/bin/env python3
"""
verify_hvp_head.py — emission in HVP, proven:

[1] the address book is exact: every emitted parameter equals the
    library parameter, through runner dots on inherent weights
[2] every bound prompt emits its own artifact (right address each time)
[3] materialization is bijective: every file sha-exact
[4] zero streamed tokens; alpha sealed on every emission
[5] a paraphrase's resonance pick — printed each run, never promised
"""
import os, sys, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'engine'))

from chatmodel import StandardModel
from hvp_head import HVPEmitter

BASE = os.path.join(HERE, 'models', 'tinystories_260k')

LIB = [
    ("build me the adder tool project", {
        'README.md': "# tiny-tool\nRun: python3 tool.py data.csv\n",
        'tool.py': "import sys\nfor line in open(sys.argv[1]):\n"
                   "    a,b=line.split(',')\n    print(int(a)+int(b))\n",
        'data.csv': "1,2\n10,20\n100,200\n"}),
    ("write the morning poem", {
        'poem.txt': "The sun climbs slow,\nthe kettle sings,\n"
                    "the day begins\non small warm wings.\n"}),
    ("give me the server config bundle", {
        'server.conf': "port=8848\nworkers=2\nlog=quiet\n",
        'notes.md': "# config\nport matches the mcp http door.\n"}),
]


def main():
    m = StandardModel(os.path.join(BASE, 'stories260K.bin'),
                      os.path.join(BASE, 'tok512.bin'), quiet=True)
    em = HVPEmitter(m)
    em.bind(LIB)

    # [1] address book exactness across every artifact and parameter
    from hcl_engine import SCALE
    for i, sig in enumerate(em.artifacts):
        e_i = [SCALE if j == i else 0 for j in range(len(em.artifacts))]
        for k in em.param_names:
            assert m.eng.dot(e_i, em.W[k]) == int(sig['params'][k])
    print(f"[1] the address book is exact: {len(em.artifacts)} artifacts x "
          f"{len(em.param_names)} params, every dot equals its demand")

    # [2][3][4] each prompt emits its own artifact, sha-exact, no stream
    for i, (prompt, artifact) in enumerate(LIB):
        out = f"/tmp/hvp_verify/{i}"
        r = em.emit(prompt, out)
        assert r['index'] == i, (prompt, r['index'])
        for f, text in artifact.items():
            got = open(os.path.join(out, f), 'rb').read()
            assert hashlib.sha256(got).hexdigest() == \
                   hashlib.sha256(text.encode()).hexdigest()
        assert r['streamed_tokens'] == 0 and r['alpha']
    print("[2] every bound prompt collapses to its own address")
    print("[3] every file materialized sha-exact through the processor")
    print("[4] zero streamed tokens; alpha sealed on every emission")

    # [5] paraphrase resonance — measured, printed
    r = em.emit("please make the adder project for me", "/tmp/hvp_verify/p")
    print(f"[5] paraphrase pick: index {r['index']} "
          f"(the adder is 0) — printed every run, never promised")

    print()
    print("ALL CHECKS PASSED — emission is an address: one forward pass,")
    print("an interference pick, inherent-weight parameters, and the")
    print("processor's bijection. The artifact never streams.")


if __name__ == '__main__':
    main()
