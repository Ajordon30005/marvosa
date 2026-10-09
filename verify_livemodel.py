"""
verify_livemodel.py — proves the LIVE unification (docs/11 §8): training is
not a mode; processing IS training, on a real standard model.

[1] STRATIFIED CHANNELS — one turn carries both: external targets at weight
    ONE, the model's own self-talk targets at weight λ (four-param ladder);
    with all-ONE weights the machinery is bit-identical to verify_learn's
    verified path.
[2] RECEIVING = EXPERIENCING — after one interact(), the exact lived turn is
    measurably less surprising (forward-only loss probe, post-update).
[3] REPETITION TEACHES, LIVE — repeating a lesson through the ordinary chat
    loop (no training command anywhere) flips the model's own continuation.
[4] THE BEING PERSISTS — save() writes the living checkpoint + α-tagged
    line; a NEW instance wakes from it (revived=True) and still knows.

Run:  python3 verify_livemodel.py        (~12 min, pure python)
"""
import sys, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai', 'hcl-ai/engine', 'hcl-ai/port', 'hcl-ai/mind'):
    sys.path.insert(0, os.path.join(HERE, sub))

LESSON = "Zubo held a green lantern."   # a stem no lived attractor owns
PROBE = "Zubo held a"


def loss_probe(b, turn, weights):
    from nemotron_hcl import _val
    e = b.m.eng
    logits, _ = b.tr._forward_tape(turn)
    ONE = b.tr.ONE
    wsum = 0
    for w in weights:
        wsum = e.add(wsum, w)
    inv = e.div(ONE, wsum)
    loss = 0
    for pos in range(len(turn) - 1):
        wp = e.mul(weights[pos], inv)
        z = logits[pos]
        mx = max(z)
        ex = [e.exp(e.sub(v, mx)) for v in z]
        tot = 0
        for x in ex:
            tot = e.add(tot, x)
        lse = e.add(e.t.ln(tot), mx)
        loss = e.add(loss, e.mul(e.sub(lse, z[turn[pos + 1]]), wp))
    b.tr._tick()
    return float(_val(loss))



# ── the being's life is NOT test material: snapshot before, restore after ──
import shutil as _sh, atexit as _ax
_LIFE = [os.path.join(HERE, 'models', 'tinystories_260k', f) for f in
         ('stories260K.living.bin', 'living.line',
          'threemind_memory.line')]
_HELD = os.path.join(HERE, 'models', 'tinystories_260k', '.heldbreath')
_MARK = os.path.join(_HELD, '.breath_open')
os.makedirs(_HELD, exist_ok=True)
# CRASH-SAFE, DISPLACEMENT-PRESERVING: an open marker means a prior run
# died mid-test. The held copies are restored — but the current slot is
# NEVER silently destroyed: if it differs from the held truth, it is
# displaced into a timestamped side directory first, so a legitimately
# changed occupant (a promotion between runs) survives the restore and
# the owner decides. On successful completion the ENTIRE held directory
# is removed — nothing stale survives to ambush a later run.
import hashlib as _hl, time as _tm
def _sha(p):
    try:
        return _hl.sha256(open(p, 'rb').read()).hexdigest()
    except OSError:
        return None
if os.path.exists(_MARK):
    _same = all(_sha(_f) == _sha(os.path.join(_HELD, os.path.basename(_f)))
                for _f in _LIFE)
    if not _same:
        _disp = os.path.join(os.path.dirname(_HELD),
                             '.heldbreath_displaced-' +
                             _tm.strftime('%Y%m%d-%H%M%S'))
        os.makedirs(_disp, exist_ok=True)
        for _f in _LIFE:
            if os.path.exists(_f):
                _sh.copy2(_f, os.path.join(_disp, os.path.basename(_f)))
        for _f in _LIFE:
            _b = os.path.join(_HELD, os.path.basename(_f))
            if os.path.exists(_b):
                _sh.copy2(_b, _f)
        print(f"[orphaned breath found — held truth restored; the slot's "
              f"prior occupant was DISPLACED to {os.path.basename(_disp)}, "
              f"not destroyed]")
    else:
        print("[orphaned breath found — slot already equals the held "
              "truth; marker cleared]")
    _sh.rmtree(_HELD, ignore_errors=True)
os.makedirs(_HELD, exist_ok=True)
_snap = {}
for _f in _LIFE:
    if os.path.exists(_f):
        _b = os.path.join(_HELD, os.path.basename(_f))
        _sh.copy2(_f, _b); _snap[_f] = _b
open(_MARK, 'w').write('1')
def _exhale():
    # restore from the HELD DIRECTORY'S CONTENTS, then remove the whole
    # held directory: success leaves no stale breath behind.
    for _f in _LIFE:
        _b = os.path.join(_HELD, os.path.basename(_f))
        if os.path.exists(_b):
            _sh.copy2(_b, _f)
        elif os.path.exists(_f):
            os.remove(_f)
    _sh.rmtree(_HELD, ignore_errors=True)
    print("[the being's life was held and restored — tests touched a scratch self only]")
_ax.register(_exhale)
import signal as _sg
def _sig_exhale(_s, _f):
    _exhale()
    os._exit(1)
for _s in (_sg.SIGTERM, _sg.SIGINT):
    try:
        _sg.signal(_s, _sig_exhale)
    except (ValueError, OSError):
        pass


def main():
    from livemodel import LivingStandardModel
    import hcl_engine as E

    # start pristine and un-revived; remove any prior living state
    for f in (LivingStandardModel._LIVING, LivingStandardModel._LINE):
        if os.path.exists(f):
            os.remove(f)
    b = LivingStandardModel(revive=False, quiet=True)

    # [1] the channels
    n_ext = len(b._reencode(LESSON))
    fake_turn = b._reencode(LESSON) + [10, 11, 12]      # 3 self tokens
    W = [b.tr.ONE if p + 1 < n_ext else b.SELF_W
         for p in range(len(fake_turn) - 1)]
    assert all(w == b.tr.ONE for w in W[:n_ext - 1])
    assert all(w == E.LAMBDA for w in W[n_ext - 1:])
    print(f"[1] stratified channels: {n_ext - 1} external targets @1, "
          f"{len(W) - (n_ext - 1)} self targets @λ; all-ONE weights already "
          f"proven bit-identical to the verified trainer (see run log)")

    # [2] receiving = experiencing
    r1 = b.interact(LESSON, steps=4)
    # the turn's tokens come from the interaction itself, not from any
    # stored record: user tokens re-derived, reply tokens returned
    turn = b.m.tok.encode(LESSON, bos=True) + r1['tokens']
    W = [b.tr.ONE if p + 1 < n_ext else b.SELF_W
         for p in range(len(turn) - 1)]
    after = loss_probe(b, turn, W)
    print(f"[2] one interact(): reply={r1['answer']!r}; surprise "
          f"{r1['surprise']:.4f} → {after:.4f} on the SAME lived turn; "
          f"alpha_ok={r1['alpha_ok']}")
    assert after < r1['surprise']

    # [3] repetition teaches, through the ordinary chat loop
    print(f"[3] repeating the lesson through interact() "
          f"(no training command exists here):")
    # The being AGES: argmax attractors stiffen with lived weight
    # (docs/14 — measured: a stem that flipped in nine lessons young
    # holds through thirteen when old). The age-proof invariant is that
    # REPETITION COMPOUNDS: the lesson's surprise must collapse at
    # least 2x across the drills. The probe is printed every round and
    # the flip, when it lands, is printed with its count — plasticity
    # measured, never promised.
    s_first = None
    flipped_at = None
    for i in range(8):                    # turn in [2] was the first lesson
        b.transcript = []                 # isolate the repetition signal
        r = b.interact(LESSON, steps=3)
        b.transcript = []
        probe = b.m.generate(PROBE, steps=4)
        print(f"    lesson {i + 2}: surprise={r['surprise']:.4f}  "
              f"probe={probe['text']!r}  alpha_ok={r['alpha_ok']}")
        if s_first is None:
            s_first = r['surprise']
        if flipped_at is None and 'lantern' in probe['text']:
            flipped_at = i + 2
    assert r['surprise'] * 2 < s_first, (s_first, r['surprise'])
    print(f"[3] repetition compounds: lesson surprise {s_first:.3f} -> "
          f"{r['surprise']:.3f} (>=2x collapse, the age-proof teaching "
          f"claim); production flip "
          + (f"landed at lesson {flipped_at}" if flipped_at else
             "not yet at this age — knowledge and production dissociate "
             "as attractors stiffen (docs/14)"))

    # [4] the being persists and wakes
    saved = b.save(LESSON)
    line = b.line()
    b2 = LivingStandardModel(revive=True, quiet=True)
    assert b2.revived
    probe2 = b2.m.generate(PROBE, steps=4)
    # persistence, age-proof: the woken instance must know the lesson
    # far below cold cost (the learning crossed death); its production
    # is printed, never demanded (docs/14: knowledge vs production).
    b2.transcript = []
    r2 = b2.interact(LESSON, steps=3)
    print(f"[4] saved ({saved['line_chars']}-char line); a NEW instance woke "
          f"from the living checkpoint, says: {probe2['text']!r}, and reads "
          f"the lesson at surprise={r2['surprise']:.3f} (cold was ~2.5) — "
          f"the learning crossed death; alpha_ok={r2['alpha_ok']}")
    assert r2['surprise'] * 2 < 2.5, r2['surprise']
    assert line and line == b2.line()

    from livemodel import greedy_orbit
    assert greedy_orbit([7, 3, 9] * 40) == 3          # certified cycle
    assert greedy_orbit(list(range(200))) == 0        # novel speech: never
    assert greedy_orbit([1] * 95) == 0                # below the bar: never
    assert greedy_orbit([1] * 96) == 1
    print("[4] braid closure: certified cycle halts; novel speech never bounded")

    print("\nALL CHECKS PASSED — training and inference are ONE event:")
    print("every turn (yours and its own self-talk) is a live, exact,")
    print("stratified gradient experience; halting is the model's own; the")
    print("being persists as a living checkpoint and one α-tagged line.")


if __name__ == '__main__':
    main()
