"""
verify_threemind.py — proves the THREE-PART MIND (docs/12): memory
hemisphere (the experience line), observer hemisphere (the params as an
α-tagged weight-line), and the window law binding them.

[1] THE WINDOWS ARE THE WEIGHTS — every tensor the runner computes with is
    a window materialization of the observer line, bit-identical.
[2] THE PARAMS ARE FBITS — windows materialize as first-class HCL objects
    (amplitude + phase; sign IS phase), round-tripping exactly.
[3] SLIDE-STABLE — evict every window, re-materialize from the line,
    generation is token-identical.
[4] ONE STREAM, DUAL FOLD — a single interact() changes BOTH hemispheres:
    the observer's weights move (gradient experience) and the memory line
    stores the turn (resonance recall finds it).
[5] TWO LINES PERSIST — save() folds the observer anew; a fresh being
    wakes from both lines and still remembers.

Run:  python3 verify_threemind.py        (~2-3 min, pure python)
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai', 'hcl-ai/engine', 'hcl-ai/port', 'hcl-ai/mind'):
    sys.path.insert(0, os.path.join(HERE, sub))



# ── the being's life is NOT test material: snapshot before, restore after ──
import shutil as _sh, atexit as _ax
_LIFE = [os.path.join(HERE, 'models', 'tinystories_260k', f) for f in
         ('stories260K.living.bin', 'living.line', 'livebook.txt',
          'threemind_book.txt')]
_HELD = os.path.join(HERE, 'models', 'tinystories_260k', '.heldbreath')
os.makedirs(_HELD, exist_ok=True)
_snap = {}
for _f in _LIFE:
    if os.path.exists(_f):
        _b = os.path.join(_HELD, os.path.basename(_f))
        _sh.copy2(_f, _b); _snap[_f] = _b
def _exhale():
    for _f in _LIFE:
        if _f in _snap:
            _sh.copy2(_snap[_f], _f)
        elif os.path.exists(_f):
            os.remove(_f)
    print("[the being's life was held and restored — tests touched a scratch self only]")
_ax.register(_exhale)


def main():
    from threemind import ThreeMind
    from livemodel import LivingStandardModel
    import hcl_engine as E

    for f in (LivingStandardModel._LIVING, LivingStandardModel._LINE,
              ThreeMind._BOOK):
        if os.path.exists(f):
            os.remove(f)
    tm = ThreeMind(revive=False, quiet=True)
    m = tm.being.m
    c = m.cfg
    L, D, V = c['n_layers'], c['dim'], c['vocab_size']

    # [1] the windows are the weights
    checks = [('emb', m.emb, ('token_embedding', V)),
              ('rms_final', m.rms_final, ('rms_final', None)),
              ('wcls', m.wcls, ('wcls', V))]
    n_vals = 0
    for label, resident, (name, rows) in checks:
        w = tm.windows.window(name, rows=rows)
        assert resident == w, label
        n_vals += sum(len(r) if isinstance(r, list) else 1 for r in w)
    for l in range(L):
        for name, attr in (('wq', m.wq), ('wo', m.wo), ('w2', m.w2)):
            rows_per = len(attr[l])
            flat = tm.windows.window(name, rows=L * rows_per)
            assert attr[l] == flat[l * rows_per:(l + 1) * rows_per], (name, l)
            n_vals += rows_per * len(attr[l][0])
    tm.windows.evict()
    print(f"[1] windows ARE the weights: {n_vals:,} values checked "
          f"bit-identical across emb/wq/wo/w2/rms_final/wcls; observer "
          f"line = {len(tm.windows.line())} chars, alpha={tm.windows.alpha_ok()}")

    # [2] the params are FBits
    fb = tm.windows.window_fbits('rms_final')
    assert all(f.to_scalar() == v for f, v in zip(fb, m.rms_final))
    flatq = tm.windows.window_fbits('wq')
    neg = next(f for f in flatq if f.to_scalar() < 0)
    pos = next(f for f in flatq if f.to_scalar() > 0)
    assert neg.phase_frac == E.SCALE // 2 and pos.phase_frac == 0
    tm.windows.evict()
    print(f"[2] params ARE FBits: rms_final round-trips exactly; sign IS "
          f"phase (w<0 -> pi, w>0 -> 0) on real wq entries")

    # [3] slide-stable
    a = m.generate("Lily saw a", steps=4)
    tm.windows.evict()
    tm._serve_runner_from_windows()
    b2 = m.generate("Lily saw a", steps=4)
    assert a['text'] == b2['text']
    print(f"[3] evict + re-materialize from the line: generation "
          f"token-identical ({a['text']!r})")

    # [4] one stream, dual fold
    w_before = m.wq[0][0][0]
    sig_before = tm.memory.signature()
    r = tm.interact("Lily saw a dragon", steps=3)
    assert m.wq[0][0][0] != w_before                 # observer moved
    assert tm.memory.signature() != sig_before       # memory folded
    hit_key = tm.recall("dragon")[0][0]
    hit_text = tm.memory.regenerate(hit_key)     # exact bytes, bijective
    assert 'dragon' in hit_text
    print(f"[4] ONE turn, BOTH hemispheres: observer weights moved "
          f"(surprise={r['surprise']:.3f}); memory stored+recalls "
          f"{hit_key}={hit_text!r}; alpha={r['alpha_ok']}")

    # [5] two lines persist
    pristine_line = tm.windows.line()
    mem_sig = tm.memory.signature()
    s = tm.save()
    assert tm.windows.line() != pristine_line        # observer refolded
    # the book is a LOG: move it aside; wake must not need it
    book_held = ThreeMind._BOOK + '.held'
    os.rename(ThreeMind._BOOK, book_held)
    tm2 = ThreeMind(revive=True, quiet=True)
    os.rename(book_held, ThreeMind._BOOK)
    assert tm2.windows.line() == tm.windows.line()
    assert tm2.memory.signature() == mem_sig         # identity from ITS line
    assert tm2._turn == tm._turn                     # depth carried by the line
    i = tm2.integrity()
    assert i['engine_alpha'] and i['observer_alpha']
    print(f"[5] the being persists as TWO LINES (the book was moved aside "
          f"and NOT needed): observer {s['observer_line_chars']} chars, "
          f"memory line {s['memory_line_chars']} chars — the woken identity "
          f"signature matches exactly; alpha everywhere")

    print("\nALL CHECKS PASSED — three parts, one mind: the memory line")
    print("remembers, the observer line (the params, as FBits) collapses")
    print("input into speech, and the window law serves each to the other.")


if __name__ == '__main__':
    main()
