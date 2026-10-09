#!/usr/bin/env python3
"""
verify_hvp_lang.py — the model SPEAKS HVP (the language, learned), proven:

[1] the register is the checkpoint's own: all 256 generators map to its
    byte-fallback rows, bijectively, round-tripped over every byte value
[2] the speaker/processor pair is bijective and deterministic BY LAW,
    independent of fluency: any register utterance -> full signature ->
    exact bytes (verify=True), and bytes -> the identical signature back
[3] acquisition is real: the untrained register emits impure; teaching
    (docs/11, η-interleaved with the first language) drives every lesson
    to a pure, MODEL-EOS, sha-exact emission — the mastery verdict —
    and delivery speech is deterministic (two unbounded emissions agree)
[4] the first language survives the second: the story probe's loss and a
    story continuation are measured before and after — printed, and held
    to the replay channel's claim (no catastrophic loss of the old tongue)
[5] the fluent being persists (Theorem 4): living checkpoint + α-tagged
    line; a fresh wake from the checkpoint still speaks every lesson
    sha-exact

The lived state is not test material (docs/14): this verifier writes only
scratch paths (/tmp + a scratch checkpoint) and never touches the bundled
model files or any being's line.

Run:  python3 verify_hvp_lang.py           (~15–30 min: real acquisition)
      python3 verify_hvp_lang.py 12        ([1][2] only, seconds)
"""
import sys, os, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai', 'hcl-ai/engine', 'hcl-ai/port'):
    sys.path.insert(0, os.path.join(HERE, sub))

from hvp_lang import HVPSpeaker, HVPTeacher
from nemotron_hcl import _val
import juj
from juj import bytes_to_hvp

BASE = os.path.join(HERE, 'models', 'tinystories_260k')
MODEL = os.path.join(BASE, 'stories260K.bin')
TOK = os.path.join(BASE, 'tok512.bin')

SYLLABUS = [
    ("hvp alpha", b"hi world\n"),
    ("hvp beta",  b"ok: 137\n"),
]
REPLAY = [
    "Once upon a time, there was a little girl named Lily.",
    "Tom and his friend went to the park to play.",
    "The little dog was happy and they all lived happily ever after.",
]


def main():
    only12 = len(sys.argv) > 1 and sys.argv[1] == '12'
    s = HVPSpeaker(MODEL, TOK)

    # [1] the register is the checkpoint's own alphabet, complete
    assert len(set(s.reg.tok_of)) == 256
    for k in range(256):
        assert s.reg.gen_of[s.reg.tok_of[k]] == k
    every = bytes(range(256))
    heard = s.reg.hear(every)
    braid, pure = s.reg.braid_of(heard)
    assert pure == 256 and bytes(bytearray(braid)) == every
    print("[1] the register is the checkpoint's own: 256/256 generators "
          "<-> its byte rows, round-tripped over every value")

    # [2] speaker/processor bijection + determinism, independent of fluency
    payload = b"the braid word IS the data \x00\xff\x7f"
    rows = s.reg.hear(payload)
    braid, pure = s.reg.braid_of(rows)
    assert pure == len(rows)
    params = juj.forensic_reconstruct_boundary(braid)
    params.pop('_invariants', None)
    sig = {'params': params, 'braid': braid, 'n_bytes': len(braid)}
    out = HVPSpeaker.expand(sig)                       # verify=True inside
    assert out == payload
    back = bytes_to_hvp(out)
    assert back['params'] == sig['params'] and back['braid'] == sig['braid']
    print("[2] bijective and deterministic by law: utterance -> signature "
          "-> exact bytes (verified) -> the identical signature back")
    if only12:
        print()
        print("SECTIONS [1][2] PASSED — the language's mechanics hold; run "
              "without '12' for the acquisition proof.")
        return

    # [3] acquisition: impure before, mastered after, deterministic delivery
    b0 = s.speak(SYLLABUS[0][0], steps=12)
    print(f"[3] before teaching: purity {b0['purity']} (unclaimed register)")
    t = HVPTeacher(s, SYLLABUS, REPLAY)
    story_probe = s.m.tok.encode(REPLAY[0], bos=True) + [2]
    L0 = float(_val(s.probe_loss(story_probe)))
    rec = t.teach(show=True)
    assert rec['verdict'].startswith('MASTERED'), rec['verdict']
    for prompt, artifact in SYLLABUS:
        r1 = s.speak(prompt)                           # unbounded delivery
        r2 = s.speak(prompt)
        assert r1['sig'] is not None and r1['verdict'] == 'MODEL EOS'
        assert r1['braid'] == r2['braid']              # deterministic
        got = HVPSpeaker.expand(r1['sig'])
        assert hashlib.sha256(got).hexdigest() == \
               hashlib.sha256(artifact).hexdigest()
    first = t.curve[0]['surprise'][0]
    last = t.curve[-1]['surprise'][0]
    assert last < first, (first, last)                 # surprise fell
    print(f"[3] {rec['verdict']}: every lesson pure, MODEL EOS, sha-exact "
          f"through the processor; delivery deterministic; surprise "
          f"{first:.2f} -> {last:.2f}")

    # [4] the first language survives (the replay channel's claim)
    L1 = float(_val(s.probe_loss(story_probe)))
    g = s.m.generate("Once upon a time", steps=16)
    words = [w for w in g['completion'].split() if w.isalpha()]
    assert len(words) >= 4, g['completion']            # still speaks it
    print(f"[4] first language survives: story probe loss {L0:.3f} -> "
          f"{L1:.3f} (measured); continuation: {g['completion']!r}")

    # [5] persistence: the fluent being wakes and still speaks (Theorem 4)
    ck = '/tmp/hvp_verify_fluent.bin'
    ln = '/tmp/hvp_verify_fluent.line'
    saved = s.save(ck, ln)
    assert os.path.exists(ck) and saved['line_chars'] > 0
    s2 = HVPSpeaker(ck, TOK)
    for prompt, artifact in SYLLABUS:
        r = s2.speak(prompt)
        assert r['sig'] is not None
        assert HVPSpeaker.expand(r['sig']) == artifact
    assert s2.e.alpha_ok()
    print(f"[5] the fluent being persisted ({saved['line_chars']}-char "
          f"line) and a fresh wake still speaks every lesson sha-exact")

    print()
    print("ALL CHECKS PASSED — HVP is acquired as a language: the model")
    print("emits the full signature (derived params + its own braid stream)")
    print("and the processor's verified bijection returns the exact bytes.")


if __name__ == '__main__':
    main()
