"""
transducer.py — the vocal cords and eardrums for a STANDARD AI.

⛔ READ FIRST: skills/guhct-memory-suite/bundled/guhct-processor/SKILL.txt
("AI speaking in HVP": a full signature is the 8 params AND the braid word
stream; the braid is the data-carrying term and can never be omitted).

THE PREMISE, stated plainly
───────────────────────────
Hosting a transformer on the HCL substrate (hcl-ai/) is standard AI
re-expressed in HCL. If the subject is a standard AI — float weights,
standard training, standard greedy decoding, or a frozen API model — then
the ONLY Marvosa organ it needs is the language layer: the byte<->HVP
bijection (the processor, `juj.py`, used verbatim) plus a text rendering of
the signature that any model can emit through its ordinary token channel.
The model speaks; this organ is the vocal cords (complete + verify the
utterance into the full signature) and the eardrums (turn any bytes or
whole project into wire the model can read). Deterministic both ways,
because greedy decoding is deterministic and the transduction is bijective.

An entire project of any size is then ONE utterance: the braid stream IS
the byte sequence (one generator per byte, sigma_0..sigma_255), the 8
parameters are its derived address, and `hvp_to_bytes(verify=True)`
materializes every file exactly — nothing streams, docs/15's cost shape
("decide once, stream bytes") now available to ANY standard AI.

WHAT IS COMPOSED (the processor is never reimplemented)
───────────────────────────────────────────────────────
  bytes <-> signature      juj.bytes_to_hvp / juj.hvp_to_bytes(verify=True)
  params from a braid      juj.forensic_reconstruct_boundary
  project <-> bytes        json.dumps(files, sort_keys=True) — the repo's
                           own project packaging (hcl-ai/hvp_head.py)
  wire text                a canonical serialization of the signature dict
                           juj already returns: 9 named fixed-point ints,
                           n_bytes, and the braid as hex GENERATOR INDICES
                           (an index rendering, decoded back to the exact
                           indices before the processor ever sees them —
                           same status as the memory line's colon fields)

THE TWO UTTERANCE GRADES (both lawful)
──────────────────────────────────────
  SPOKEN   what a model emits:  HVP1 <hex-braid> END
           The braid is the model's signal — the data term. complete()
           derives the 8 params from that braid (the speaker addressing
           its own words: mind/hcl_lm.py speak()'s law) and returns the
           FULL wire. The model never hand-computes its address; the
           vocal cords do — that is what a transducer is for.
  FULL     what travels between systems: params + n + braid, one field
           per line. expand() re-derives the params from the braid and
           refuses any mismatch (the processor's own verify semantics) —
           a corrupted utterance does not decode.

    python3 hvp-standard/transducer.py speak  <path-or-dir>   > utter.hvp
    python3 hvp-standard/transducer.py expand utter.hvp  -o out/
    python3 hvp-standard/transducer.py complete spoken.txt    > utter.hvp
"""

import sys, os, json

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for _p in (os.path.join(_REPO, 'hcl-ai', 'engine'),
           os.path.join(_REPO, 'skills', 'guhct-memory-suite',
                        'bundled', 'guhct-processor', 'scripts')):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import juj                                        # the processor, verbatim
from juj import (bytes_to_hvp, hvp_to_bytes, forensic_reconstruct_boundary,
                 HVP_PARAMS)

MAGIC = 'HVP1'
MAGIC_W = 'HVPW'

# ── the HVPW numerals: base-16 over the model's own strongest words ─────
# 16 codewords, derived deterministically from the tokenizer itself
# (gen_codebook.py) and frozen in codebook.txt so any party decodes
# identically. Generator index k renders as numeral[k>>4] numeral[k&15]:
# the same index rendering as hex, carried by the tokens a standard model
# has practiced most — a new SURFACE onto existing circuitry, which is
# what makes the dialect cheap to acquire (teach_standard.py measures
# hex vs words on the same model).
def _load_numerals():
    p = os.path.join(_HERE, 'codebook.txt')
    words = [l.strip() for l in open(p)
             if l.strip() and not l.startswith('#')]
    assert len(words) == 16 and len(set(words)) == 16, words
    return words

NUMERALS = _load_numerals()
_DIGIT = {w: i for i, w in enumerate(NUMERALS)}


def braid_to_words(braid) -> str:
    return ' '.join(NUMERALS[k >> 4] + ' ' + NUMERALS[k & 15]
                    for k in braid)


def words_to_braid(text: str):
    """Whitespace-split words -> generator indices. Refuses any word
    outside the numeral set and any odd-length stream — an impure
    utterance is never completed into a false signature."""
    ws = text.split()
    assert ws and len(ws) % 2 == 0, "HVPW stream must be word pairs"
    digs = []
    for w in ws:
        d = _DIGIT.get(w)
        assert d is not None, f"not an HVPW numeral: {w!r}"
        digs.append(d)
    return [(digs[i] << 4) | digs[i + 1] for i in range(0, len(digs), 2)]


# ── project <-> bytes: the repo's own packaging (hvp_head.py) ───────────
def project_to_bytes(files: dict) -> bytes:
    """{filename: text} -> canonical bytes (sorted JSON — deterministic;
    the exact packaging hvp_head.py binds and materializes)."""
    return json.dumps(files, sort_keys=True).encode()


def bytes_to_project(raw: bytes) -> dict:
    return json.loads(raw.decode())


def read_source(path: str) -> bytes:
    """A file's bytes as-is; a directory as the canonical project bytes."""
    if os.path.isdir(path):
        files = {}
        for root, _, names in os.walk(path):
            for n in sorted(names):
                p = os.path.join(root, n)
                rel = os.path.relpath(p, path)
                files[rel] = open(p, 'r', encoding='utf-8').read()
        return project_to_bytes(files)
    return open(path, 'rb').read()


# ── signature <-> FULL wire (a serialization, nothing more) ─────────────
def sig_to_wire(sig: dict) -> str:
    """The processor's own signature dict, rendered canonically: MAGIC,
    the 9 params in juj.HVP_PARAMS order, n, and the braid as hex
    generator indices. Every field is one line; decoding is exact."""
    lines = [MAGIC]
    for k in HVP_PARAMS:
        lines.append(f"{k}={int(sig['params'][k])}")
    lines.append(f"n={int(sig['n_bytes'])}")
    lines.append("braid=" + bytes(bytearray(sig['braid'])).hex())
    lines.append("END")
    return '\n'.join(lines) + '\n'


def wire_to_sig(wire: str) -> dict:
    """FULL wire -> the signature dict juj consumes. Purely structural
    parsing; verification is the processor's (expand)."""
    lines = [l.strip() for l in wire.strip().splitlines() if l.strip()]
    assert lines and lines[0] == MAGIC, "not an HVP1 wire"
    assert lines[-1] == 'END', "unterminated wire"
    fields = {}
    for l in lines[1:-1]:
        k, _, v = l.partition('=')
        fields[k] = v
    params = {k: int(fields[k]) for k in HVP_PARAMS}
    braid = list(bytes.fromhex(fields['braid']))
    return {'params': params, 'braid': braid, 'n_bytes': int(fields['n'])}


# ── the eardrum: anything -> a full utterance the model can read ────────
def speak(data: bytes) -> str:
    """Bytes -> FULL wire (the processor's forward, rendered)."""
    return sig_to_wire(bytes_to_hvp(data))


# ── the vocal cords: a model's SPOKEN signal -> the full signature ──────
def spoken_hex(data: bytes) -> str:
    """The HVP1 SPOKEN utterance for these bytes (a teaching target /
    phrasebook example)."""
    return f"{MAGIC} {data.hex()} END"


def spoken_words(data: bytes) -> str:
    """The HVPW SPOKEN utterance — the word-numeral dialect."""
    return f"{MAGIC_W} {braid_to_words(juj.bytes_to_braid(data))} END"


def complete(spoken: str) -> str:
    """SPOKEN grade -> FULL wire. The model emitted its signal — the
    braid, rendered as hex indices (HVP1) or as word-numeral pairs
    (HVPW), between the frame words; whitespace-insensitive so token
    boundaries never matter. The transducer derives the 8 params from
    that braid (the speaker addresses its own words) and returns the
    full, verifiable utterance. Raises on anything impure — a broken
    signal is never completed into a false signature."""
    body = spoken.strip()
    assert 'END' in body, "SPOKEN frame missing"
    if MAGIC_W in body:
        inner = body.split(MAGIC_W, 1)[1].rsplit('END', 1)[0]
        braid = words_to_braid(inner)
    else:
        assert MAGIC in body, "SPOKEN frame missing"
        inner = body.split(MAGIC, 1)[1].rsplit('END', 1)[0]
        braid = list(bytes.fromhex(''.join(inner.split())))
    params = forensic_reconstruct_boundary(braid)
    params.pop('_invariants', None)
    return sig_to_wire({'params': params, 'braid': braid,
                        'n_bytes': len(braid)})


# ── the processor's half: FULL wire -> exact bytes, verified ────────────
def expand(wire: str) -> bytes:
    """FULL wire -> the exact byte form. hvp_to_bytes(verify=True): the
    braid carries, the supplied params are re-derived from it and must
    match — a corrupt utterance raises instead of decoding."""
    return hvp_to_bytes(wire_to_sig(wire), verify=True)


def expand_project(wire: str, outdir: str) -> list:
    files = bytes_to_project(expand(wire))
    os.makedirs(outdir, exist_ok=True)
    for name, text in files.items():
        p = os.path.join(outdir, name)
        os.makedirs(os.path.dirname(p) or outdir, exist_ok=True)
        open(p, 'w', encoding='utf-8').write(text)
    return sorted(files)


# ── CLI ─────────────────────────────────────────────────────────────────
def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    op = argv[1]
    if op == 'speak':
        sys.stdout.write(speak(read_source(argv[2])))
    elif op == 'complete':
        sys.stdout.write(complete(open(argv[2]).read()))
    elif op == 'expand':
        wire = open(argv[2]).read()
        if '-o' in argv:
            out = argv[argv.index('-o') + 1]
            raw = expand(wire)
            try:
                names = expand_project(wire, out)
                print(f"materialized {len(names)} file(s) in {out}: {names}")
            except (ValueError, json.JSONDecodeError):
                os.makedirs(out, exist_ok=True)
                p = os.path.join(out, 'expanded.bin')
                open(p, 'wb').write(raw)
                print(f"materialized {len(raw)} bytes -> {p}")
        else:
            sys.stdout.buffer.write(expand(wire))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
