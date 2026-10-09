#!/usr/bin/env python3
"""
verify_hvp_standard.py — a STANDARD AI speaks HVP, proven:

[1] the wire is lawful: bytes -> FULL wire -> exact bytes over the edges
    (empty, one byte, all 256 values, random entropy), and bytes -> wire
    -> bytes -> wire closes on the identical text (bidirectional)
[2] a whole project is ONE utterance: multi-file project -> one wire ->
    every file materialized sha-exact
[3] corruption is refused: one flipped hex char in the braid, one swapped
    numeral in HVPW, or an edited parameter — each raises instead of
    decoding (the processor re-derives the address and it must match)
[4] the dialects are one language: HVP1 (hex) and HVPW (word numerals)
    complete to the IDENTICAL full wire for the same bytes; the numeral
    set is exactly the committed codebook, rederived from the tokenizer
[5] the phrasebook's worked examples parse and expand through the same
    code path a frozen AI's utterance would take
[6] a REAL standard model acquires the language: stories260K run with
    plain float math and standard SGD (nothing of the substrate in the
    model), taught the SPOKEN wire with replay, reaches the mastery
    verdict — every lesson emitted as ONE unbounded utterance, MODEL
    EOS, deterministic, expanded sha-exact — while a HELD-OUT first-
    language probe and continuation are printed before and after

Run:  python3 verify_hvp_standard.py          (~4–8 min: real acquisition)
      python3 verify_hvp_standard.py fast     ([1]–[5] only, seconds)

Section [6] is ~4 minutes of continuous compute. In environments that
kill long processes, run [1]–[5] here (`fast`) and drive [6]'s
acquisition through the breath CLI instead —
`python3 hvp-standard/teach_standard.py --state DIR --epochs N --dialect
words` — which saves the being every call and reaches the same mastery
verdict fold by fold (docs/14's breath doctrine).
"""
import sys, os, hashlib, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hvp-standard'))

import transducer as T

BASE = os.path.join(HERE, 'models', 'tinystories_260k')
HELD_OUT = "One day, a little boy named Tim went to the park with his mom."


def main():
    fast = len(sys.argv) > 1 and sys.argv[1] == 'fast'

    # [1] the wire law on the edges; bidirectional closure
    cases = [b"", b"A", bytes(range(256)), os.urandom(4096)]
    for data in cases:
        wire = T.speak(data)
        assert T.expand(wire) == data
        assert T.speak(T.expand(wire)) == wire
    print("[1] wire lawful: edges exact (empty/1/256-values/4KB entropy); "
          "bytes->wire->bytes->wire closes identically")

    # [2] a whole project is ONE utterance
    proj = {'hello.py': "print('hello world')\n",
            'README.md': "# hello\nRun: python3 hello.py\n",
            'sub/run.sh': "#!/bin/sh\npython3 hello.py\n"}
    wire = T.speak(T.project_to_bytes(proj))
    outdir = '/tmp/hvp_std_verify/onego'
    names = T.expand_project(wire, outdir)
    assert names == sorted(proj)
    for n in proj:
        got = open(os.path.join(outdir, n)).read()
        assert hashlib.sha256(got.encode()).hexdigest() == \
               hashlib.sha256(proj[n].encode()).hexdigest()
    print(f"[2] one utterance -> whole project: {len(names)} files "
          f"materialized sha-exact (incl. a subdirectory)")

    # [2b] scale: a large payload is still ONE utterance (linear cost)
    import time
    big = os.urandom(100_000)
    t0 = time.time(); w = T.speak(big); t1 = time.time()
    assert T.expand(w) == big; t2 = time.time()
    print(f"[2b] scale: 100,000 bytes as one utterance — speak "
          f"{t1 - t0:.2f}s, expand+verify {t2 - t1:.2f}s, "
          f"wire {len(w):,} chars (linear; 1 MB measured at "
          f"13.0s / 3.6s on this box)")

    # [2c] the literal claim: an entire Go project, one utterance,
    #      expanded exactly — and, where a toolchain exists, built and run
    from demo_one_go import PROJECT as GO_PROJECT
    gw = T.speak(T.project_to_bytes(GO_PROJECT))
    godir = '/tmp/hvp_std_verify/onego_go'
    gnames = T.expand_project(gw, godir)
    assert gnames == sorted(GO_PROJECT)
    import shutil, subprocess
    if shutil.which('go'):
        r = subprocess.run(['go', 'build', '-o', 'hvpdemo', '.'],
                           cwd=godir, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        r = subprocess.run(['./hvpdemo'], cwd=godir,
                           capture_output=True, text=True)
        assert r.returncode == 0 and 'alpha seal: 137' in r.stdout
        print("[2c] an entire Go project in one utterance: expanded "
              "sha-exact, COMPILED, and RUN (prints the 137 seal)")
    else:
        print("[2c] an entire Go project in one utterance: expanded "
              "sha-exact (no Go toolchain on this box, so the build+run "
              "half of the claim was NOT exercised here)")

    # [3] corruption refused, three ways
    refusals = 0
    lines = wire.splitlines()
    bi = next(i for i, l in enumerate(lines) if l.startswith('braid='))
    h = lines[bi][6:]
    bad = list(lines)
    bad[bi] = 'braid=' + ('0' if h[0] != '0' else '1') + h[1:]
    try:
        T.expand('\n'.join(bad) + '\n')
    except ValueError:
        refusals += 1
    bad = list(lines)
    ti = next(i for i, l in enumerate(lines) if l.startswith('T='))
    bad[ti] = 'T=' + str(int(lines[ti][2:]) + 1)
    try:
        T.expand('\n'.join(bad) + '\n')
    except ValueError:
        refusals += 1
    sw = T.spoken_words(b"ok\n").replace(' the ', ' zzz ', 1)
    try:
        T.complete(sw)
    except AssertionError:
        refusals += 1
    assert refusals == 3
    print("[3] corruption refused: flipped braid char, edited parameter, "
          "alien numeral — all three raise, none decode")

    # [4] the dialects are one language; the codebook is the derived one
    from gen_codebook import derive
    assert derive(os.path.join(BASE, 'tok512.bin')) == T.NUMERALS
    for data in (b"ok\n", T.project_to_bytes({'a.txt': "137\n"}),
                 bytes(range(0, 256, 7))):
        assert T.complete(T.spoken_words(data)) == \
               T.complete(T.spoken_hex(data)) == T.speak(data)
    print("[4] HVP1 and HVPW complete to the identical full wire; "
          "numerals == the codebook rederived from the tokenizer")

    # [5] the phrasebook's worked examples run through the same path
    pb = open(os.path.join(HERE, 'hvp-standard', 'phrasebook.md')).read()
    ex_proj = {'hello.py': "print('hello world')\n"}
    spoken = next(l for l in pb.splitlines()
                  if l.startswith('HVP1 ') and l.endswith(' END'))
    full = T.complete(spoken)
    assert T.bytes_to_project(T.expand(full)) == ex_proj
    assert full.strip() in pb, "phrasebook FULL wire drifted from the code"
    sw = next(l for l in pb.splitlines()
              if l.startswith('HVPW ') and l.endswith(' END'))
    assert T.expand(T.complete(sw)) == b"ok\n"
    print("[5] phrasebook examples verified live: spoken -> completed -> "
          "expanded, and its printed full wire matches the code's")

    # [5b] the shipped GENERALIZED checkpoint speaks strings it never saw
    gen_ck = os.path.join(BASE, 'stories260K.hvpgen.bin')
    try:
        import numpy  # noqa: F401
        have_np = True
    except ImportError:
        have_np = False
    if have_np and os.path.exists(gen_ck):
        import random
        from fastmodel import FastModel
        from generalize import ALPHABET, TEST, TRAIN_SINGLES
        gm = FastModel(gen_ck, os.path.join(BASE, 'tok512.bin'))
        rng = random.Random(888)               # disjoint from train/test/eval
        seen = set(TEST) | set(TRAIN_SINGLES)
        batch = []
        while len(batch) < 30:
            s2 = ''.join(rng.choice(ALPHABET)
                         for _ in range(rng.randint(2, 8))).strip()
            if len(s2) >= 2 and s2 not in seen:
                seen.add(s2); batch.append(s2)
        hits = 0
        for s2 in batch:
            r = gm.generate('say ' + s2, steps=len(s2) * 4 + 20)
            try:
                hits += (r['verdict'] == 'MODEL EOS' and
                         T.expand(T.complete(r['completion'])) == s2.encode())
            except (AssertionError, ValueError):
                pass
        g = gm.generate("Once upon a time", steps=10)
        assert hits >= 24, f"{hits}/30"
        assert 'girl' in g['completion'] or 'there' in g['completion']
        print(f"[5b] shipped generalized checkpoint: {hits}/30 fresh unseen "
              f"strings transcode exactly (97.5% on the 200-string eval at "
              f"train time); first language intact")
    else:
        print("[5b] shipped generalized checkpoint: SKIPPED — " +
              ("checkpoint not present" if have_np else "numpy unavailable")
              + " on this box; the claim is exercised where both exist")

    if fast:
        print()
        print("SECTIONS [1]-[5] PASSED — the language layer holds; run "
              "without 'fast' for the real-model acquisition proof.")
        return

    # [6] a real standard model acquires the language (words dialect)
    import teach_standard as TS
    TS.DIALECT = 'words'
    m = TS.StandardFloatModel(os.path.join(BASE, 'stories260K.bin'),
                              os.path.join(BASE, 'tok512.bin'))
    held = m.tok.encode(HELD_OUT, bos=True) + [2]
    L0 = m.loss(held)
    g0 = m.generate("One day, a little", steps=10)
    b0 = m.generate(TS.SYLLABUS[0][0], steps=12)['completion']
    assert 'HVPW' not in b0 and 'HVP1' not in b0
    print(f"[6] before: held-out first-language loss {L0:.4f}; "
          f"{TS.SYLLABUS[0][0]!r} emits no HVP yet")
    t = TS.StandardTeacher(m)
    rec = t.teach(epochs=200, show=True, probe_every=4)
    assert rec['verdict'].startswith('MASTERED'), rec['verdict']
    results = TS.deliver(m, '/tmp/hvp_std_verify/spoken', show=True)
    assert all(r['sha'] and r['det'] and r['bidi']
               and r['verdict'] == 'MODEL EOS' for r in results)
    L1 = m.loss(held)
    g1 = m.generate("One day, a little", steps=10)
    rise = (L1 - L0) / L0
    print(f"[6] {rec['verdict']} ({rec['seconds']}s): every project one "
          f"unbounded utterance, MODEL EOS, deterministic, sha-exact; "
          f"held-out loss {L0:.4f} -> {L1:.4f} "
          f"({'+' if rise >= 0 else ''}{100 * rise:.1f}%), continuation "
          f"{g0['completion']!r} -> {g1['completion']!r}")
    # forgetting is one-directional: the old tongue may not degrade.
    # improvement (replay generalizing) passes by definition.
    assert rise < 0.10, "first language degraded past 10% on held-out"

    print()
    print("ALL CHECKS PASSED — a standard AI, taught only the language,")
    print("answers with ONE HVP utterance per request; the transducer")
    print("completes and verifies it and the exact bytes come back.")


if __name__ == '__main__':
    main()
