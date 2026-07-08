"""
threemind.py — the THREE-PART MIND, composed entirely from existing organs.

    Part 1  MEMORY hemisphere   — LivingMemory (engine/living_memory.py):
            every lived turn is store()d as experience on the topological
            line; recall is resonance collapse; it has its own signature
            and α integrity. This side mostly REMEMBERS.

    Part 2  OBSERVER hemisphere — the params AS a line: the model's
            weights folded through ModelMemory (largemodel.py) into one
            α-tagged identity line. Every weight IS an FBit (the
            from_scalar bijection: amplitude = magnitude, phase 0/π =
            sign), and every operation on it is an FBit composition
            (verify_fastpath proves the runner's fast paths bit-identical
            to the composed FBit forms). This side OBSERVES — it is what
            collapses input into a reply (MCL selection lives here).

    Part 3  the WINDOW law       — the SAME access logic as memory,
            applied to weights: ModelMemory.tensor_values(name, rows)
            materializes a bounded WINDOW of the weight-line on demand
            (ingest_expel.window's law: keep the whole, materialize only
            the slice; the rest never exists in RAM). The runner's
            resident tensors are window-served FROM the observer line,
            can be evicted and re-materialized bit-identically, and — as
            FBits — enter the engine as first-class HCL objects. For a
            260K model every window fits at once; for a 7B model the same
            API slides. Same logic, any scale.

One stream, one transduction, dual fold (organism.py's hemispheric law):
each interact() generates the reply through window-served weights, then
folds the SAME lived turn into BOTH hemispheres — a gradient experience
into the observer (learn.py, Theorems 1–4) and a stored experience into
memory (LivingMemory.store). The being's identity is TWO lines plus the
window law that joins them.

    python3 verify_threemind.py     # the proof
"""

import sys, os, json, time

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, 'engine'), os.path.join(_HERE, 'port')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from livemodel import LivingStandardModel
from largemodel import ModelMemory
from living_memory import LivingMemory
from hcl_engine import FBit
import hcl_engine as E


class WeightWindows:
    """Part 3: the window law over the observer line. Serves bounded
    windows of the weight-line, as raw fixed-point values or as FBits;
    windows are evictable and re-materialize bit-identically from the
    line's own record."""

    def __init__(self, checkpoint_path):
        self.mm = ModelMemory(chunk=256 * 1024)
        self.mm.ingest_file(checkpoint_path)
        assert self.mm.alpha_ok()
        self._resident = {}                      # name -> materialized window

    def line(self):
        return self.mm.line()

    def names(self):
        return [t['name'] for t in self.mm.toc()]

    def window(self, name, rows=None):
        """Materialize a bounded window (the memory access law, applied to
        weights). Cached while resident; evict() slides it out."""
        key = (name, rows)
        if key not in self._resident:
            self._resident[key] = self.mm.tensor_values(name, rows=rows)
        return self._resident[key]

    def window_fbits(self, name, rows=None):
        """The same window, materialized as FIRST-CLASS FBits — every
        param an HCL object (amplitude + phase), ready for braid ops."""
        vals = self.window(name, rows)
        if vals and isinstance(vals[0], list):
            return [[FBit.from_scalar(v) for v in row] for row in vals]
        return [FBit.from_scalar(v) for v in vals]

    def evict(self, name=None):
        """Slide windows out of residence; the line still holds the whole."""
        if name is None:
            self._resident.clear()
        else:
            for k in [k for k in self._resident if k[0] == name]:
                del self._resident[k]

    def alpha_ok(self):
        return self.mm.alpha_ok()


class ThreeMind:
    """The composed being: memory line + observer line + the window law,
    wrapped around the living standard model's one-experience loop."""

    _BOOK = os.path.join(_HERE, '..', 'models', 'tinystories_260k',
                         'threemind_book.txt')          # transparency LOG only
    _MEMLINE = os.path.join(_HERE, '..', 'models', 'tinystories_260k',
                            'threemind_memory.line')    # the memory ITSELF

    def __init__(self, revive=True, quiet=False):
        # observer hemisphere: the living model (weights = the observing
        # params); its checkpoint is the current fold of the observer line
        self.being = LivingStandardModel(revive=revive, quiet=True)
        src = (self.being._LIVING if self.being.revived
               else os.path.join(self.being._STATE, 'stories260K.bin'))
        # part 3: the window law over those very weights
        self.windows = WeightWindows(src)
        # serve the runner's resident tensors FROM the observer line —
        # the weights the model computes with ARE window materializations
        self._serve_runner_from_windows()
        # memory hemisphere: the experience line
        self.memory = LivingMemory()
        self._turn = 0
        # THE LINE IS THE MEMORY, NOT A LOG (hcl_lm.load's own law: "Nothing
        # else is read or replayed"). Wake restores the composite Ψ identity
        # from the memory hemisphere's OWN α-tagged line; a tampered line is
        # refused by from_expression itself. The book is transparency only —
        # NEVER read here. Episodic braids (exact regeneration) are RAM-era
        # senses by LivingMemory's Rule 1; they regrow through new life.
        if revive and os.path.exists(self._MEMLINE):
            line = open(self._MEMLINE).read().strip()
            if line:
                self.memory.vm = self.memory.vm.__class__.from_expression(line)
                self._turn = int(line.split(':')[5])     # depth field
        if not quiet:
            print(f"[threemind] observer line: {len(self.windows.line())} "
                  f"chars (α={self.windows.alpha_ok()}); memory: "
                  f"{self._turn} lived turns; windows resident: 0")

    # ── part 3 in action: the runner computes on window-served weights ──
    def _serve_runner_from_windows(self, assert_identity=True):
        """Materialize every runner tensor FROM the observer line's windows
        and install them as AUTHORITATIVE. At birth (assert_identity=True)
        the windows must be bit-identical to what the runner loaded — same
        bytes, same _fp boundary — proving the weights the model thinks
        with ARE window materializations of its own line. At a fold
        (save), the line is quantized to the model's OWN format (f32, its
        checkpoint law), and the fold DEFINES the being: windows install
        unconditionally, the runner now thinks with the folded self."""
        m, c = self.being.m, self.being.m.cfg
        L, D, KD = c['n_layers'], c['dim'], c['kv_dim']
        H, V = c['hidden_dim'], c['vocab_size']

        def per_layer(name, rows_per, cols):
            flat = self.windows.window(name, rows=L * rows_per)
            return [flat[l * rows_per:(l + 1) * rows_per] for l in range(L)]

        served = {
            'emb':  self.windows.window('token_embedding', rows=V),
            'wq':  per_layer('wq', D, D),   'wk': per_layer('wk', KD, D),
            'wv':  per_layer('wv', KD, D),  'wo': per_layer('wo', D, D),
            'w1':  per_layer('w1', H, D),   'w3': per_layer('w3', H, D),
            'w2':  per_layer('w2', D, H),
            'rms_att': self.windows.window('rms_att', rows=L),
            'rms_ffn': self.windows.window('rms_ffn', rows=L),
            'rms_final': self.windows.window('rms_final'),
            'wcls': self.windows.window('wcls', rows=V),
        }
        for name, vals in served.items():
            if assert_identity:
                assert getattr(m, name) == vals, f"window≠runner: {name}"
            setattr(m, name, vals)           # windows now authoritative
        self.windows.evict()                 # residence released; line holds all
        return len(served)

    # ── one stream, dual fold ────────────────────────────────────────────
    def interact(self, text, steps=None, reward=None):
        """The organism law: ONE lived turn folds into BOTH hemispheres.
        Reply is generated by the observer (window-served params, MCL
        collapse at the boundary); the turn then becomes (a) a gradient
        experience in the observer's weights and (b) a stored experience
        on the memory line."""
        r = self.being.interact(text, steps=steps, reward=reward)
        key = f"turn{self._turn}"
        self.memory.store(key, text)
        self._turn += 1
        with open(self._BOOK, 'a') as f:
            f.write(text.strip().replace('\n', ' ') + '\n')
        r['memory_key'] = key
        r['memory_sig'] = self.memory.signature()
        return r

    def recall(self, query, k=3):
        """Resonance collapse over the memory hemisphere: ranked keys."""
        return self.memory.recall(query, k=k)

    def remember(self, query):
        """Collapse to the most resonant lived turn and REGENERATE its
        exact text from the kept braid (bijective, verified)."""
        r = self.recall(query, k=1)
        return self.memory.regenerate(r[0][0]) if r else None

    def save(self):
        """The being persists as its TWO lines — the observer's fold and
        the memory hemisphere's own α-tagged composite expression (the
        mind's save law, verbatim pattern)."""
        with open(self._MEMLINE, 'w') as f:
            f.write(self.memory.vm.to_expression() + '\n')
        s = self.being.save()
        self.windows = WeightWindows(self.being._LIVING)
        self._serve_runner_from_windows(assert_identity=False)  # the fold
        self.being.tr.m = self.being.m       # trainer follows the fold
        return {'observer_line_chars': len(self.windows.line()),
                'memory_line_chars': len(open(self._MEMLINE).read().strip()),
                'memory_signature': self.memory.signature(),
                'checkpoint': s['checkpoint']}

    def integrity(self):
        return {'engine_alpha': self.being.m.eng.alpha_ok(),
                'observer_alpha': self.windows.alpha_ok(),
                'memory': self.memory.integrity(),
                'observer_line': self.windows.line()[:24] + '…',
                'lived_turns': self._turn}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="Talk to the THREE-PART MIND — "
        "it remembers (memory line), it learns as you talk (observer line), "
        "and it persists as both.")
    ap.add_argument('--fresh', action='store_true', help='be born pristine')
    args = ap.parse_args()
    tm = ThreeMind(revive=not args.fresh)
    print("(unbounded replies — its own stop; '/recall <q>' collapses memory; "
          "'/save' folds the being; empty line exits and saves)\n")
    while True:
        try:
            text = input('you> ').strip()
        except EOFError:
            print(); break
        if not text:
            break
        if text.startswith('/recall '):
            q = text[8:]
            print('  remembered:', repr(tm.remember(q)))
            continue
        if text == '/save':
            print('  ', tm.save()); continue
        r = tm.interact(text)
        print('it >', r['answer'])
        print(f"     [surprise={r['surprise']:.3f} verdict={r['verdict']} "
              f"alpha={r['alpha_ok']}]")
    print('folding the being…'); print(tm.save())
