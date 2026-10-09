"""
generalize.py — past the syllabus: does the standard model learn the
HVPW ENCODING RULE, or only the sentences it was taught?

Task: `say <s>` -> the HVPW utterance for the utf-8 bytes of s, over the
alphabet a–z plus space (27 symbols). Training covers every symbol (all
27 single-character drills) plus a fixed set of multi-character strings;
the TEST set is disjoint strings never seen in training. A test string
can only come out exact if the model learned the per-byte mapping and
applies it position by position — generalization, not recall.

Same standard trainer as teach_standard.py (float stories260K, SGD,
completion-masked, story replay every 2nd epoch). Breath-split state.

    python3 hvp-standard/generalize.py --state DIR --epochs N
"""
import sys, os, json, time, random

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import transducer as T
from teach_standard import StandardFloatModel, _write_ckpt, REPLAY, EOS
from fastmodel import FastModel

ALPHABET = 'abcdefghijklmnopqrstuvwxyz '
LR = 0.03

_rng = random.Random(137)          # fixed seed: the sets are part of the spec
def _mk(n, lo, hi, taken):
    out = []
    while len(out) < n:
        s = ''.join(_rng.choice(ALPHABET) for _ in range(_rng.randint(lo, hi)))
        s = s.strip()
        if len(s) >= lo and s not in taken:
            taken.add(s); out.append(s)
    return out

_taken = set(ALPHABET)
TRAIN_SINGLES = list(ALPHABET)                     # every symbol, once
TRAIN_MULTI = _mk(24, 2, 6, _taken)                # fixed, seeded
TEST = _mk(8, 4, 7, _taken)                        # disjoint, never trained


def utter(s: str) -> str:
    return T.spoken_words(s.encode())


class GenTeacher:
    def __init__(self, m: StandardFloatModel):
        self.m = m

    def _turn(self, s: str):
        p = self.m.tok.encode('say ' + s, bos=True)
        return (p + self.m.tok.encode(' ' + utter(s), bos=False) + [EOS],
                len(p))

    def probe(self, strings, slack=16):
        exact = 0
        for s in strings:
            want = utter(s)
            r = self.m.generate('say ' + s, steps=len(want.split()) * 2 + slack)
            if r['verdict'] != 'MODEL EOS':
                continue
            try:
                if T.expand(T.complete(r['completion'])) == s.encode():
                    exact += 1
            except (AssertionError, ValueError):
                pass
        return exact

    def teach(self, epochs=None, probe_every=2, show=True, online=False,
              start_epoch=0, batch=24, harden_until=0):
        t0 = time.time()
        epoch = start_epoch
        curve = []
        test_set = set(TEST)
        while True:
            epoch += 1
            if online:
                # fresh strings every epoch: memorization cannot reduce
                # loss, so the only descending solution is the mapping
                # itself. Seeded per epoch: deterministic, replayable.
                r = random.Random(5000 + epoch)
                fresh, guard = [], 0
                while len(fresh) < batch and guard < 10 * batch:
                    guard += 1
                    s2 = ''.join(r.choice(ALPHABET)
                                 for _ in range(r.randint(2, 8))).strip()
                    if len(s2) >= 2 and s2 not in test_set:
                        fresh.append(s2)
                order = list(TRAIN_SINGLES) + fresh
            else:
                order = list(TRAIN_SINGLES + TRAIN_MULTI)
            random.Random(1000 + epoch).shuffle(order)   # seeded: replayable
            tot = 0.0
            for s in order:
                toks, npr = self._turn(s)
                tot += self.m.train_turn(toks, LR, mask_from=npr)
            if epoch % 2 == 0:
                for meal in REPLAY:
                    self.m.train_turn(self.m.tok.encode(meal, bos=True)
                                      + [EOS], LR)
            rec = {'epoch': epoch, 'surprise': round(tot / len(order), 4)}
            if epoch % probe_every == 0 or (epochs is not None
                                            and epoch >= epochs):
                rec['train_exact'] = self.probe(order[-8:] if online
                                                else TRAIN_MULTI[:8])
                rec['test_exact'] = self.probe(TEST)
                if show:
                    print(f"  epoch {epoch:>3}: surprise {rec['surprise']:.3f}"
                          f"  train {rec['train_exact']}/8"
                          f"  TEST {rec['test_exact']}/{len(TEST)}")
                if rec['test_exact'] == len(TEST) and epoch >= harden_until:
                    curve.append(rec)
                    return {'verdict': f'GENERALIZED (epoch {epoch})',
                            'curve': curve,
                            'seconds': round(time.time() - t0, 1)}
            elif show:
                print(f"  epoch {epoch:>3}: surprise {rec['surprise']:.3f}")
            curve.append(rec)
            if epochs is not None and epoch >= epochs:
                return {'verdict': 'DELIVERY BOUND', 'curve': curve,
                        'seconds': round(time.time() - t0, 1)}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--state', default=None)
    ap.add_argument('--epochs', type=int, default=None)
    ap.add_argument('--online', action='store_true',
                    help="fresh seeded strings every epoch (anti-memorize)")
    ap.add_argument('--lr', type=float, default=None,
                    help="override SGD rate (anneal for the endgame)")
    ap.add_argument('--harden', type=int, default=0,
                    help="keep training past the TEST demand until this "
                         "epoch (consolidation)")
    a = ap.parse_args()
    global LR
    if a.lr is not None:
        LR = a.lr

    base = os.path.join(_REPO, 'models', 'tinystories_260k')
    src = os.path.join(base, 'stories260K.bin')
    st = None
    if a.state:
        os.makedirs(a.state, exist_ok=True)
        ck = os.path.join(a.state, 'gen.bin')
        meta = os.path.join(a.state, 'curve.json')
        st = json.load(open(meta)) if os.path.exists(meta) else \
            {'epochs': 0, 'curve': [], 'done': False}
        if os.path.exists(ck):
            src = ck

    m = FastModel(src, os.path.join(base, 'tok512.bin'))
    woke = st is not None and src != os.path.join(base, 'stories260K.bin')
    print(f"[gen] alphabet {len(ALPHABET)} symbols; train "
          f"{len(TRAIN_SINGLES)}+{len(TRAIN_MULTI)} strings; "
          f"TEST {len(TEST)} unseen strings"
          + (f"; woke at epoch {st['epochs']}" if woke else ""))
    t = GenTeacher(m)
    rec = t.teach(epochs=a.epochs, online=a.online,
                  start_epoch=st['epochs'] if st else 0,
                  harden_until=a.harden)
    done = rec['verdict'].startswith('GENERALIZED')
    if st is not None:
        st['epochs'] += len(rec['curve'])
        st['curve'] += rec['curve']
        st['done'] = done
        m.save(os.path.join(a.state, 'gen.bin'))
        json.dump(st, open(os.path.join(a.state, 'curve.json'), 'w'))
        print(f"[breath] {rec['verdict']} ({rec['seconds']}s); "
              f"life at epoch {st['epochs']}, saved")
    if done:
        print("[gen] unseen strings transcode exactly — the model learned "
              "the rule, not the sentences")
        for s in TEST[:3]:
            r = m.generate('say ' + s)
            out = T.expand(T.complete(r['completion'])).decode()
            print(f"    'say {s}' -> {out!r} ({r['verdict']})")


if __name__ == '__main__':
    main()
