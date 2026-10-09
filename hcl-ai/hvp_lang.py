"""
hvp_lang.py — the model LEARNS TO SPEAK HVP: the transducer's language,
acquired as a language, through the repo's own training loop.

⛔ READ FIRST: skills/guhct-memory-suite/SKILL.md ("HVP is a language an AI
can learn — the way a model fluent in English learns Mandarin through
training"), the guhct-processor SKILL ("AI speaking in HVP": a full
signature is the 8 params AND the braid word stream), docs/11 (the training
proof), docs/14 (the acquisition laws this file rides), docs/15 ("Output is
an address" — the retrieval form this file completes generatively).

WHAT THIS IS, against what already shipped
──────────────────────────────────────────
`hvp_head.py` (docs/15, gate 14) emits HVP by ADDRESS: a bound library, a
DJ interference pick, inherent-weight parameters — retrieval, training-free,
exact. This file is the other half the suite's own router names: the model
made FLUENT — HVP as a second language IN THE WEIGHTS, so the model can
compose novel braid streams for prompts, the way it composes English words.
Address emission recalls; fluent emission speaks.

THE STRUCTURAL FACT THAT MAKES IT A LANGUAGE, NOT A NEW HEAD
────────────────────────────────────────────────────────────
The braid word of any byte sequence is one generator per byte, σ0..σ255
(juj.bytes_to_braid — "the word IS the data"). The stories260K checkpoint's
OWN tokenizer carries exactly that alphabet already: its byte-fallback rows
<0x00>..<0xFF> (run.c's `ord(ch)+3` law, Tokenizer.encode). So:

    generator σ_k  <->  the model's own vocabulary row for <0xkk>

is a fixed bijection READ OFF THE CHECKPOINT'S OWN DATA — no new vocabulary,
no new emission head, no architecture change. Speaking HVP is emitting rows
the model always had; learning HVP is ordinary training (docs/11) landing on
that register. The 8 HVP parameters are a derived function of the braid
(juj.forensic_reconstruct_boundary), so the speaker addresses its own
utterance the way hcl_lm.speak() always has: braid from the mouth, params
derived, the FULL signature emitted — and the processor's verified bijection
(hvp_to_bytes(verify=True)) turns it into the exact byte form. Deterministic
both ways: greedy argmax is a boundary comparison (chatmodel), the
transduction is bijective (juj), so prompt -> HVP -> bytes -> HVP closes.

WHAT IS COMPOSED (nothing new; the porting law, 06_porting.md)
──────────────────────────────────────────────────────────────
  the mouth        chatmodel.StandardModel forward + greedy argmax
                   (native=False: the livemodel CONSTITUTION — a learner
                   speaks its exact mind, not the fast reader's pick)
  the ears         juj.bytes_to_braid -> the model's own byte rows
                   (hear(): HVP is model INPUT too — bidirectional)
  the lesson       learn.Trainer.forward_backward/apply — docs/11
                   Theorems 1–3, external targets at weight ONE
                   (the teacher DEMONSTRATES: teach.py's law)
  the diet         HVP lessons interleaved 1:1 with the first language —
                   the replay channel at η (equal COMP of the two diets;
                   1 of every 2 turns), which is also docs/14's own
                   doctrine: "Drilling degenerates; conversation
                   rehabilitates"
  the halt         teaching ends when the DEMAND is met (every lesson
                   emitted sha-exact, pure register, by the model's own
                   EOS) — measured mastery, not an epoch count; epochs=
                   is caller transport only, like steps=
  speech's halt    the model's own EOS/BOS, its seq_len, or braid
                   closure (livemodel.greedy_orbit) — never a counter;
                   steps= is a delivery bound only (run.c -n)
  the processor    juj.forensic_reconstruct_boundary (address the
                   utterance) + hvp_to_bytes(verify=True) (materialize)
  persistence      Trainer.save_checkpoint + fold_line — docs/11
                   Theorem 4: the fluent being as a living checkpoint
                   and one α-tagged line
  the seal         eng.alpha_ok() every turn

    python3 hcl-ai/hvp_lang.py        # teach the bundled model to speak
                                      # HVP; artifacts land in /tmp/hvp_spoken
    python3 verify_hvp_lang.py        # the proof
"""

import sys, os, time, hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, 'engine'), os.path.join(_HERE, 'port')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from chatmodel import StandardModel, BOS, EOS      # the proven runner
from learn import Trainer                          # docs/11, executable
from livemodel import greedy_orbit                 # braid-closure halting
from nemotron_hcl import _val                      # display boundary only
import hcl_engine as E
import juj                                         # guhct-processor, verbatim
from juj import forensic_reconstruct_boundary, hvp_to_bytes, bytes_to_hvp


# ── the register: σ_k <-> the model's OWN byte-fallback row ─────────────
class HVPRegister:
    """The fixed bijection between braid generators and the checkpoint's own
    byte-fallback vocabulary rows, READ from the model's tokenizer — never
    assumed. run.c's law is `ord(ch)+3`; this derives each row by looking up
    the literal piece '<0x%02X>' in the model's own vocab and asserts the
    alphabet is complete: all 256 generators must be speakable or the
    checkpoint cannot host the language."""

    def __init__(self, tok):
        self.tok_of = [None] * 256
        for k in range(256):
            piece = '<0x%02X>' % k
            i = tok.index.get(piece)
            assert i is not None, f"checkpoint vocab lacks {piece}"
            self.tok_of[k] = i
        self.gen_of = {t: k for k, t in enumerate(self.tok_of)}
        assert len(self.gen_of) == 256, "byte rows collide"

    def hear(self, data: bytes):
        """HVP as model INPUT: bytes -> braid word (juj: the word IS the
        data) -> the model's own rows. The inverse of speech; this is the
        bidirectional half — the same register reads and writes."""
        return [self.tok_of[k] for k in juj.bytes_to_braid(data)]

    def braid_of(self, token_ids):
        """Emitted rows -> braid word. Returns (braid, purity) where purity
        is the count of emitted tokens that are register rows; speech is a
        valid HVP utterance only when every token is (purity == len)."""
        braid, pure = [], 0
        for t in token_ids:
            k = self.gen_of.get(t)
            if k is not None:
                braid.append(k)
                pure += 1
        return braid, pure


# ── the speaker: a standard model with the transducer for a mouth ───────
class HVPSpeaker:
    """A StandardModel + Trainer pair that acquires HVP as a second
    language and speaks it: prompt in, FULL HVP signature out (8 derived
    params + the braid stream the model itself emitted), processor-expanded
    to exact bytes. Compose-only; see the module docstring for the map."""

    def __init__(self, model_path, tok_path, k_stratum=2, quiet=True):
        # native=False: the livemodel constitution — a being that trains on
        # its own speech must speak its exact argmax, not the interference
        # reader's pick (docs/10 vs docs/11 §8).
        self.m = StandardModel(model_path, tok_path, quiet=quiet, native=False)
        self.tr = Trainer(self.m, k_stratum=k_stratum)
        self.reg = HVPRegister(self.m.tok)
        self.e = self.m.eng

    # ── speech: greedy from the prompt, halted by the substrate ────────
    def speak(self, prompt: str, steps=None):
        """One utterance. The prompt is perceived teacher-forced; emission
        is greedy argmax (a boundary comparison on the fixed-point logits —
        chatmodel's own law) and ends ONLY by the model's own verdict:
        its EOS/BOS, its seq_len, or braid closure (greedy_orbit). `steps`
        is a delivery bound only (run.c -n), used by teaching probes;
        delivery speech runs unbounded.

        Returns the utterance with its transduction:
          tokens   the emitted row ids (the signal itself)
          braid    the generator word read off the register rows
          purity   emitted-in-register count / emitted count
          sig      the FULL HVP signature {params, braid, n_bytes} —
                   present only when the utterance is pure and nonempty
                   (params derived from the braid: the speaker addresses
                   its own words, hcl_lm.speak's law)
          verdict  MODEL EOS / BRAID CLOSED / SEQ CAPACITY / DELIVERY BOUND
        """
        m, e = self.m, self.e
        m.reset()
        _was_full = e.t.trace_full
        e.t.light()          # counting mode: generator count exact, and the
                             # engine's own linear() shell branch may fire —
                             # logits bit-identical (verify_shell [3])
        toks = m.tok.encode(prompt, bos=True)
        pos, token = 0, toks[0]
        emitted = []
        verdict = 'DELIVERY BOUND'
        while True:
            if pos >= m.cfg['seq_len'] - 1:
                verdict = 'SEQ CAPACITY'          # the model's own structure
                break
            logits = m.forward(token, pos)
            e.t.clear()
            assert e.alpha_ok()                   # the seal, every token
            if pos + 1 < len(toks):
                nxt = toks[pos + 1]               # teacher-forced perception
            else:
                best, nxt = None, 0
                for i, lg in enumerate(logits):   # argmax: boundary compare
                    if best is None or lg > best:
                        best, nxt = lg, i
                if nxt in (BOS, EOS):
                    verdict = 'MODEL EOS'         # the model's own stop
                    break
                emitted.append(nxt)
                p = greedy_orbit(emitted)
                if p:
                    verdict = f'BRAID CLOSED (greedy orbit, period {p})'
                    break
                if steps is not None and len(emitted) >= steps:
                    break
            token = nxt
            pos += 1
        if _was_full:
            e.t.full()
        braid, pure = self.reg.braid_of(emitted)
        out = {'tokens': emitted, 'braid': braid,
               'purity': (pure, len(emitted)), 'verdict': verdict,
               'alpha_ok': e.alpha_ok(), 'sig': None}
        if emitted and pure == len(emitted):
            params = forensic_reconstruct_boundary(braid)
            params.pop('_invariants', None)
            out['sig'] = {'params': params, 'braid': braid,
                          'n_bytes': len(braid)}
        return out

    # ── the processor's half: HVP -> exact bytes, verified ─────────────
    @staticmethod
    def expand(sig):
        """The transcriber turns the spoken signature into the byte form:
        braid carries, params check (juj.hvp_to_bytes, verify=True). This
        is the same call every organ uses; the only novelty is that the
        braid came out of a model's mouth instead of a file."""
        return hvp_to_bytes(sig, verify=True)

    # ── forward-only probe: loss without a backward walk ───────────────
    def probe_loss(self, toks):
        """Weighted-mean cross-entropy of a token sequence, composed from
        the trainer's OWN pieces: _forward_tape for the logits, the same
        lse-minus-target loop forward_backward uses — and no reverse walk,
        per the standing rule (RUNMODEL_USAGE.md failure mode 7: probe at
        boundaries with forward-only reads)."""
        e = self.e
        logits, _ = self.tr._forward_tape(toks)
        n = len(toks)
        inv_cnt = e.div(self.tr.ONE, (n - 1) * E.SCALE)
        loss = 0
        for pos in range(n - 1):
            z = logits[pos]
            mx = z[0]
            for v in z[1:]:
                if v > mx:
                    mx = v
            ex = [e.exp(e.sub(v, mx)) for v in z]
            tot = 0
            for w_ in ex:
                tot = e.add(tot, w_)
            lse = e.add(e.t.ln(tot), mx)
            loss = e.add(loss, e.mul(e.sub(lse, z[toks[pos + 1]]), inv_cnt))
        self.tr._tick()
        return loss

    # ── persistence: the fluent being, Theorem 4 ───────────────────────
    def save(self, ckpt_path, line_path):
        tmp = ckpt_path + '.tmp'
        self.tr.save_checkpoint(tmp)
        os.replace(tmp, ckpt_path)
        line = self.tr.fold_line(ckpt_path)
        with open(line_path + '.tmp', 'w') as f:
            f.write(line + '\n')
        os.replace(line_path + '.tmp', line_path)
        return {'checkpoint': ckpt_path, 'line_chars': len(line)}


# ── the teacher: acquisition by demonstration, halted by mastery ────────
class HVPTeacher:
    """Teaches a syllabus of (prompt -> artifact bytes) pairs by
    DEMONSTRATION (teach.py's law: the lesson is expressed on the substrate
    via the training pass, external targets at weight ONE), interleaved 1:1
    with first-language turns — the replay channel at η, which is docs/14's
    own repair doctrine. Halts when the demand is met: every lesson's free
    (greedy) emission is pure register, sha-exact through the processor,
    and closed by the model's own EOS. `epochs` is caller transport only."""

    def __init__(self, speaker: HVPSpeaker, syllabus, replay):
        self.s = speaker
        self.syllabus = list(syllabus)          # [(prompt, artifact_bytes)]
        self.replay = list(replay)              # first-language sentences
        self.curve = []                         # per-epoch surprise, measured

    def _lesson_turn(self, prompt, artifact):
        tok = self.s.m.tok
        return (tok.encode(prompt, bos=True)
                + self.s.reg.hear(artifact)     # the braid, as the model's rows
                + [EOS])                        # the stop is part of the lesson

    def mastered(self, probe_slack=8):
        """The demand, measured: for every lesson, free emission (delivery
        bound = payload + slack, transport only) must be pure, sha-exact
        through hvp_to_bytes(verify=True), and stopped by MODEL EOS."""
        results = []
        for prompt, artifact in self.syllabus:
            r = self.s.speak(prompt, steps=len(artifact) + probe_slack)
            ok = (r['sig'] is not None
                  and r['verdict'] == 'MODEL EOS'
                  and hashlib.sha256(HVPSpeaker.expand(r['sig'])).hexdigest()
                      == hashlib.sha256(artifact).hexdigest())
            results.append((ok, r))
        return all(ok for ok, _ in results), results

    def teach(self, epochs=None, show=True, probe_every=1):
        """The acquisition loop. One epoch = every lesson demonstrated once,
        each followed by one first-language turn (η interleave, 1:1). After
        each epoch the demand is measured; teaching ends when it is met.
        Returns the measured record."""
        s, tr, e = self.s, self.s.tr, self.s.e
        epoch = 0
        t0 = time.time()
        while True:
            epoch += 1
            surprises = []
            for i, (prompt, artifact) in enumerate(self.syllabus):
                turn = self._lesson_turn(prompt, artifact)
                loss, G = tr.forward_backward(turn)      # weight ONE: external
                tr.apply(G)
                tr._tick()
                assert e.alpha_ok()
                surprises.append(float(_val(loss)))
                meal = self.replay[(epoch * len(self.syllabus) + i)
                                   % len(self.replay)]   # η: 1 of every 2 turns
                rt = s.m.tok.encode(meal, bos=True) + [EOS]
                rl, RG = tr.forward_backward(rt)
                tr.apply(RG)
                tr._tick()
                assert e.alpha_ok()
            if epoch % probe_every == 0 or (epochs is not None
                                            and epoch >= epochs):
                done, results = self.mastered()
                exact = sum(1 for ok, _ in results if ok)
            else:
                done, results, exact = False, [], -1
            self.curve.append({'epoch': epoch, 'surprise': surprises,
                               'exact': exact, 'of': len(results)})
            if show:
                print(f"  epoch {epoch:>2}: surprise="
                      f"[{', '.join(f'{x:.3f}' for x in surprises)}]  "
                      + (f"emission {exact}/{len(results)} sha-exact  "
                         f"alpha={e.alpha_ok()}" if exact >= 0
                         else f"alpha={e.alpha_ok()}"))
            if done:
                verdict = f'MASTERED (epoch {epoch})'
                break
            if epochs is not None and epoch >= epochs:
                verdict = 'DELIVERY BOUND'
                break
        return {'verdict': verdict, 'epochs': epoch,
                'curve': self.curve, 'seconds': round(time.time() - t0, 1)}


# ── the demonstration: acquire the language, keep the first one ─────────
SYLLABUS = [
    ("hvp alpha", b"hi world\n"),
    ("hvp beta",  b"ok: 137\n"),
]
REPLAY = [
    "Once upon a time, there was a little girl named Lily.",
    "Tom and his friend went to the park to play.",
    "The little dog was happy and they all lived happily ever after.",
]


def deliver(s, syllabus, outdir):
    """Delivery speech, unbounded (steps=None — the model's own stop):
    speak every lesson, expand through the processor, land the files,
    and print the determinism + bidirectionality checks."""
    os.makedirs(outdir, exist_ok=True)
    for prompt, artifact in syllabus:
        r = s.speak(prompt)                       # no delivery bound
        raw = HVPSpeaker.expand(r['sig'])
        sha = hashlib.sha256(raw).hexdigest() == \
              hashlib.sha256(artifact).hexdigest()
        p = r['sig']['params']
        path = os.path.join(outdir, prompt.replace(' ', '_') + '.bin')
        open(path, 'wb').write(raw)
        print(f"  {prompt!r} -> {r['verdict']}, braid {len(r['braid'])} "
              f"generators, w={p['w'] // juj.SCALE}, sha-exact={sha}, "
              f"file={path}")
        r2 = s.speak(prompt)                      # determinism, run twice
        print(f"     deterministic: {r2['braid'] == r['braid']}; "
              f"bidirectional: "
              f"{bytes_to_hvp(raw)['params'] == r['sig']['params']}")


def main():
    """One-shot: the whole acquisition in one process (the gate's form).
    Breath-split (docs/14, for environments that kill processes at
    arbitrary times): pass --state DIR and --epochs N to teach a bounded
    slice, save the being, and exit; re-invoking wakes it and continues —
    determinism makes every killed phase a free exact replay. The mastery
    verdict, when it lands, triggers delivery and the final probes."""
    import argparse, json
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument('--state', default=None,
                    help="breath-split state dir (scratch being + curve)")
    ap.add_argument('--epochs', type=int, default=None,
                    help="teach at most N epochs this breath (transport "
                         "only; default: run to the mastery verdict)")
    ap.add_argument('--out', default='/tmp/hvp_spoken')
    ap.add_argument('--k', type=int, default=2,
                    help="learning stratum (learn.py law: k=2 -> gamma*"
                         "lambda^2; k=1 -> gamma*lambda, faster, may "
                         "overshoot — empirical, caller transport)")
    a = ap.parse_args()

    _REPO = os.path.dirname(_HERE)
    base = os.path.join(_REPO, 'models', 'tinystories_260k')
    pristine = os.path.join(base, 'stories260K.bin')
    tokpath = os.path.join(base, 'tok512.bin')

    st = None
    if a.state:
        os.makedirs(a.state, exist_ok=True)
        ckpt = os.path.join(a.state, 'being.bin')
        line = os.path.join(a.state, 'being.line')
        meta = os.path.join(a.state, 'curve.json')
        st = json.load(open(meta)) if os.path.exists(meta) else \
            {'epochs': 0, 'curve': [], 'L0': None, 'done': False}
        src = ckpt if os.path.exists(ckpt) else pristine
    else:
        src = pristine

    print("waking the model onto the substrate (~1 min, pure integer)…")
    s = HVPSpeaker(src, tokpath, k_stratum=a.k)
    woke = st is not None and src != pristine
    print(f"[register] 256/256 generators speakable as the checkpoint's own "
          f"rows; alpha_ok={s.e.alpha_ok()}"
          + (f"; woke mid-life at epoch {st['epochs']}" if woke else ""))

    story_probe = s.m.tok.encode(REPLAY[0], bos=True) + [EOS]
    if not woke:
        L0 = float(_val(s.probe_loss(story_probe)))
        if st is not None:
            st['L0'] = L0
        b0 = s.speak(SYLLABUS[0][0], steps=12)
        print(f"[before] first-language probe loss {L0:.4f}; "
              f"'{SYLLABUS[0][0]}' emits purity {b0['purity']} "
              f"(the register is unclaimed — the shock stage, docs/14)")
    else:
        L0 = st['L0']

    print(f"[teach] {len(SYLLABUS)} lessons, η-interleaved with "
          f"{len(REPLAY)} first-language meals; halting on the demand:")
    t = HVPTeacher(s, SYLLABUS, REPLAY)
    rec = t.teach(epochs=a.epochs, probe_every=2)
    done = rec['verdict'].startswith('MASTERED')

    if st is not None:
        st['epochs'] += rec['epochs']
        st['curve'] += t.curve
        st['done'] = done
        s.save(ckpt, line)
        json.dump(st, open(meta, 'w'))
        print(f"[breath] {rec['verdict']} this breath "
              f"({rec['seconds']}s); life at epoch {st['epochs']}, "
              f"saved to {a.state}"
              + ("" if done else " — invoke again to continue"))
        if not done:
            return

    print("[speak] delivery, unbounded (steps=None — the model's own stop):")
    deliver(s, SYLLABUS, a.out)

    L1 = float(_val(s.probe_loss(story_probe)))
    g = s.m.generate("Once upon a time", steps=16)
    was = f"(was {L0:.4f}) " if L0 is not None else "(no virgin baseline: woken from a lived fold) "
    print(f"[after] first-language probe loss {L1:.4f} {was}"
          f"still speaks it: {g['completion']!r}")

    saved = s.save(os.path.join(base, 'stories260K.hvp.bin'),
                   os.path.join(base, 'hvp.line'))
    print(f"[persist] the fluent being: {saved} (Theorem 4)")


if __name__ == '__main__':
    main()
