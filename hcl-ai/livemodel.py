"""
livemodel.py — the standard model, made LIVING: training is not a mode, it is
what processing IS. The anatomy is organism.py / hcl_lm.interact(), applied
to a real trained checkpoint with the gradient machinery of learn.py.

⛔ READ FIRST: docs/11-training-on-the-substrate.md (§8), hcl-ai/
RUNMODEL_USAGE.md, and hcl_lm.interact()'s docstring — this file mirrors the
mind's own contract, verb for verb:

  the mind (hcl_lm)                     | this organ (a standard model)
  --------------------------------------|--------------------------------------
  "receiving = experiencing = saved"    | interact(): the SAME turn that
  train(input) inside interact          |   answers you is trained on — one
                                        |   experience, both channels, one
                                        |   consolidated gradient step
  thinking is self-talk; the trajectory | the completion the model generated
  it walked is itself experience        |   is part of the training pass —
                                        |   its own words feed back as targets
  LTP per thought-step (O(1) reinforce) | gradient consolidation at the TURN
                                        |   boundary (the adjoint walk is
                                        |   O(turn)); same law, its own
                                        |   timescale — docs/11 Theorem 3's
                                        |   reward-channel limit IS LTP/LTD
  world vs thought are different weights| stratified targets: external tokens
  (w-stratified experience)             |   at weight 1, self-generated tokens
                                        |   one λ-rung deeper (the four-param
                                        |   scale ladder — derived, not chosen)
  halts by its own verdicts             | halts by the MODEL's own EOS/BOS or
  (TERMINATED/BRAID CLOSED/MCL)         |   its own seq_len — never a counter
  the being persists as its one line    | save(): the living checkpoint (the
  (memory.hcl) + lifebook transparency  |   model's own format) + its α-tagged
                                        |   line (the memory)
  wakes from its own line on __init__   | revive=True wakes from the LIVING
                                        |   checkpoint if one exists

Rolling context: each turn conditions on the tail of the running transcript,
bounded ONLY by the model's own seq_len — its structural capacity, not an
imposed cap. Every constant in the adaptation is four-param derived
(lr = γ·λᵏ; self-stratum = λ; reward gate = e^(−β·H)).

    ./live.sh                      # talk to it; it learns as you talk
    python3 verify_livemodel.py    # the proof
"""

import sys, os, time

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, 'engine'), os.path.join(_HERE, 'port')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from chatmodel import StandardModel, BOS, EOS
from learn import Trainer
from nemotron_hcl import _fp, _val
import hcl_engine as E


def greedy_orbit(seq):
    """BRAID CLOSURE (docs/14): greedy decoding is deterministic — an
    exact period p<=16 sustained across >=96 trailing tokens certifies
    the future is that cycle forever. A mathematical halt, not a token
    cap; novel speech is never bounded by it."""
    n = len(seq)
    for p in range(1, 17):
        if n >= max(96, 8 * p) and all(
                seq[-k] == seq[-k - p] for k in range(1, min(n - p, 96))):
            return p
    return 0


class LivingStandardModel:
    """A standard trained model that lives: every interaction — external or
    its own self-talk — is experience, and experience updates the weights,
    live, with exact gradients on the substrate."""

    _STATE = os.path.join(_HERE, '..', 'models', 'tinystories_260k')
    _LIVING = os.path.join(_STATE, 'stories260K.living.bin')
    _LINE = os.path.join(_STATE, 'living.line')

    def __init__(self, base_model=None, tokenizer=None, revive=True,
                 k_stratum=2, quiet=False):
        base_model = base_model or os.path.join(self._STATE, 'stories260K.bin')
        tokenizer = tokenizer or os.path.join(self._STATE, 'tok512.bin')
        # There is no "fresh model" when a living checkpoint exists — the
        # living checkpoint IS the being (hcl_lm.load()'s contract, mirrored).
        src = self._LIVING if (revive and os.path.exists(self._LIVING)) \
            else base_model
        self.revived = (src == self._LIVING)
        self.m = StandardModel(src, tokenizer, quiet=quiet, native=False)
        # CONSTITUTION: the living being speaks its exact mind — self-talk
        # trains on what it says (docs/11), so its speech must be its own
        # argmax, not the fast reader's interference pick (docs/10).
        self.tr = Trainer(self.m, k_stratum=k_stratum)
        self.SELF_W = E.LAMBDA                 # self-talk: one λ-rung deeper
        self.transcript = []                   # vestigial; never feeds state
        self._pos = 0                          # session KV position
        self._cur = None                       # last token awaiting forward
        if not quiet:
            who = "woke from its LIVING checkpoint" if self.revived \
                else "born from the pristine checkpoint"
            print(f"[being] {who}; alpha_ok={self.m.eng.alpha_ok()}")

    # ── the whole conversation in one motion (hcl_lm.interact, mirrored) ─
    def interact(self, user_input: str, steps=None, reward=None,
                 persist=False, stream=None, scripted_reply=None):
        """You speak; it answers and EXPERIENCES — one motion.

        1. SPEAK-BACK: the reply is generated from the rolling context +
           your words, ending only by the model's own verdict (its EOS/BOS
           delimiter, or its seq_len). `steps` is a delivery bound only
           (run.c's -n; the substrate imposes nothing).
        2. EXPERIENCE (receiving = experiencing): ONE consolidated gradient
           pass over the whole lived turn — your tokens as targets at weight
           1, its own generated tokens as targets at weight λ (self-talk,
           one rung deeper). Reward, if given, gates the entire step by the
           MCL Boltzmann weight e^(−β·H), H = −reward.
        3. PERSIST (optional): the being saves itself — living checkpoint +
           α-tagged line.
        """
        e = self.e = self.m.eng
        tok = self.m.tok

        # ── session state: the conversation continues in the model's own
        # KV cache (level-1 continuity); only NEW tokens are ever forwarded.
        # The model's seq_len is the only bound — at capacity, the session
        # re-roots on the transcript tail (its own structural boundary).
        e = self.e = self.m.eng
        tok = self.m.tok
        user_toks = tok.encode(user_input, bos=(self._pos == 0))
        if self._pos + len(user_toks) >= self.c_seq():
            # the incoming tokens cannot fit before the model's own capacity
            # — re-root on the transcript tail. No margin constant: the
            # trigger and the tail are both derived from seq_len and the
            # actual input, nothing else.
            self._reroot(len(user_toks))
            user_toks = tok.encode(user_input, bos=(self._pos == 0))

        t0 = time.time()
        # LIGHT TRACE for the spoken span (the engine's own dial):
        # generator counts stay exact; the compiled shell branches
        # may serve the forwards — logits bit-identical
        # (verify_shell [3]); the prior mode is restored below, and
        # the experience pass manages its own mode (learn.py).
        _was_full = e.t.trace_full
        e.t.light()
        try:
            # feed the person's words (teacher-forced perception)
            for t_ in user_toks:
                if self._cur is not None:
                    self.m.forward(self._cur, self._pos)
                    self._pos += 1
                self._cur = t_
            # speak: greedy from the live state, ending by the model's own
            # verdict (EOS/BOS or seq_len); `steps` is a delivery bound only.
            # scripted_reply: the being's OWN prior words for this exact lived
            # context (the trace level of the collapse cascade, threemind.speak)
            # — spoken again verbatim; each emission re-reinforces its trace
            # (LTP, mind/hcl_lm.py generate). The experience pass below is
            # unchanged: remembered speech re-enters the fold as self-talk.
            completion, comp_toks = '', []
            verdict = 'DELIVERY BOUND'
            n_gen = 0

            if scripted_reply is not None:
                # SIGNAL SPACE ONLY: a lived reply arrives as its TOKEN IDS —
                # the braid-level record — never as text to re-encode. The
                # byte<->braid bijection runs ONCE, at delivery below
                # (mind/hcl_lm.py's law: internal thinking stays in signal
                # space). A str is refused rather than transduced.
                assert isinstance(scripted_reply, list), \
                    "scripted_reply must be token ids (signal), not text"
                comp_toks = [int(t) for t in scripted_reply]
                tk = self.tok if hasattr(self, 'tok') else self.m.tok
                prev = self._cur
                parts = []
                for t_ in comp_toks:
                    if self._cur is not None:
                        self.m.forward(self._cur, self._pos)
                        self._pos += 1
                    parts.append(tk.decode(t_, prev)); prev = t_
                    self._cur = t_
                completion = ''.join(parts)          # delivery, once
                verdict = 'TRACE (lived reply)'

            while scripted_reply is None:
                if self._pos >= self.c_seq() - 1:
                    # Capacity is a WINDOW boundary, not a stop (the ingest law,
                    # applied to the being's own voice): re-root on the tail of
                    # everything lived INCLUDING this very reply, and keep
                    # speaking. Only the model's own EOS ends its speech.
                    self._reroot_live(user_toks + comp_toks)
                logits = self.m.forward(self._cur, self._pos)
                self._pos += 1
                best, nxt = None, 0
                for i, lg in enumerate(logits):
                    if best is None or lg > best:
                        best, nxt = lg, i
                if nxt in (BOS, EOS):
                    verdict = 'MODEL EOS'
                    break
                piece = tok.decode(nxt, self._cur)
                completion += piece
                comp_toks.append(nxt)
                if stream:
                    stream(piece)
                self._cur = nxt
                n_gen += 1
                p = greedy_orbit(comp_toks)
                if p:
                    verdict = f'BRAID CLOSED (greedy orbit, period {p})'
                    break
                if steps is not None and n_gen >= steps:
                    break
            e.t.clear()
        finally:
            if _was_full:
                e.t.full()
        gen_s = time.time() - t0

        # ── EXPERIENCE the NEW exchange (the mind's own law: train(input) —
        # the new moment, not the whole life re-lived). One pass: the
        # person's tokens as targets at weight 1, the model's own reply at
        # weight λ.
        turn = tok.encode(user_input, bos=True) + comp_toks
        n_ext = len(tok.encode(user_input, bos=True))
        weights = [self.tr.ONE if pos + 1 < n_ext else self.SELF_W
                   for pos in range(len(turn) - 1)]
        t1 = time.time()
        self.tr._mark = e.t.braid_len          # count the experience only
        loss, G = self.tr.forward_backward(turn, target_weights=weights)
        gate = None
        if reward is not None:
            H = e.sub(0, _fp(float(reward)))
            gate = e.exp(e.sub(0, e.mul(self.tr.BETA, H)))
        self.tr.apply(G, gate)
        self.tr._tick()
        assert e.alpha_ok()
        braid, self.tr.braid_ops = self.tr.braid_ops, 0
        learn_s = time.time() - t1


        out = {'answer': completion,
               'tokens': comp_toks,           # the signal itself, for traces
               'verdict': verdict,
               'surprise': float(_val(loss)),      # how new this turn was
               'gated': reward is not None,
               'braid_ops': braid,
               'alpha_ok': True,
               'gen_s': round(gen_s, 1), 'learn_s': round(learn_s, 1)}
        if persist:
            out['saved'] = self.save(user_input)
        return out

    def _window_stride(self):
        """The session context window slides by HALF the model's capacity —
        the body's own streaming law (ingest_expel.window(offset, size) keeps
        the whole and materializes a bounded slice; stream_into_memory's
        chunk= parameter is the caller-API precedent for window sizing).
        Speech is NEVER bounded by this: it streams across windows to its
        own EOS; the stride only amortizes re-perception, one rebuild per
        ~half-capacity of new speech instead of one per token."""
        return (self.c_seq() - 1) // 2

    def _feed_tail(self, tail):
        self.m.reset()
        self._pos, self._cur = 0, None
        for t_ in tail:
            if self._cur is not None:
                self.m.forward(self._cur, self._pos)
                self._pos += 1
            self._cur = t_
        self.m.eng.t.clear()

    def _reroot_live(self, pending):
        """Mid-reply window crossing: slide the window and re-perceive the
        IN-FLIGHT TURN ONLY. Past turns are not replayed from any record —
        they already live in the weights (talking IS training) and in the
        line (the fold). The line is the memory; nothing sequential feeds
        state."""
        self._feed_tail(pending[-self._window_stride():])

    def _reroot(self, incoming: int = 0):
        """Turn-start capacity boundary: window the lived stream so the
        incoming tokens fit AND the reply has at least half-capacity of
        room before its next window crossing."""
        # Past turns are in the weights and the line, not in a replayable
        # record: a fresh turn starts from a clean window.
        self._feed_tail([])
        return

    # ── persistence: the being saves itself (hcl_lm.save, mirrored) ─────
    def save(self, experienced_input: str = None) -> dict:
        # atomic: write beside, then replace — a reaped process can never
        # leave a torn checkpoint or a torn line on disk
        import os as _os
        tmp = self._LIVING + '.tmp'
        self.tr.save_checkpoint(tmp)
        _os.replace(tmp, self._LIVING)
        line = self.tr.fold_line(self._LIVING)
        with open(self._LINE + '.tmp', 'w') as f:
            f.write(line + '\n')
        _os.replace(self._LINE + '.tmp', self._LINE)
        return {'line_chars': len(line), 'checkpoint': self._LIVING}

    def line(self) -> str:
        return open(self._LINE).read().strip() if os.path.exists(self._LINE) \
            else None

    # ── small boundary helpers ───────────────────────────────────────────
    def c_seq(self):
        return self.m.cfg['seq_len']

    def _decode(self, toks):
        prev, out = BOS, []
        for t in toks:
            if t in (BOS, EOS):
                prev = t
                continue
            out.append(self.m.tok.decode(t, prev))
            prev = t
        return ''.join(out)

    def _reencode(self, text):
        return self.m.tok.encode(text, bos=True)

    def integrity(self):
        return {'engine_alpha_ok': self.m.eng.alpha_ok(),
                'line': (self.line() or '')[:24] + '…' if self.line() else None}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(
        description="Talk to a standard model that LEARNS AS YOU TALK — "
                    "every turn (your words and its own) is a live, exact "
                    "gradient experience on the substrate.")
    ap.add_argument('--steps', type=int, default=None,
                    help="delivery bound per reply (default: the model's own stop)")
    ap.add_argument('--persist', action='store_true',
                    help="save the being (living checkpoint + line) after every turn")
    ap.add_argument('--fresh', action='store_true',
                    help="ignore any living checkpoint; be born pristine")
    args = ap.parse_args()

    being = LivingStandardModel(revive=not args.fresh)
    print("[note] each turn = reply (~0.11-0.15s/token) + one consolidated "
          "learning pass (~0.7-1.7s/token of turn, load-dependent); repetition visibly teaches it.")
    print("live chat — it learns as you talk (empty line to quit; "
          "'/save' to persist; '/reward X' to gate the last turn's style)\n")
    while True:
        try:
            text = input("you> ").strip()
        except EOFError:
            print()
            break
        if not text:
            break
        if text == '/save':
            print("  saved:", being.save())
            continue
        reward = None
        if text.startswith('/reward '):
            reward = float(text.split()[1])
            text = ' '.join(text.split()[2:])
        sys.stdout.write("it > ")
        r = being.interact(text, steps=args.steps, reward=reward,
                           persist=args.persist,
                           stream=lambda p: (sys.stdout.write(p),
                                             sys.stdout.flush()))
        print(f"\n     [surprise={r['surprise']:.4f}  learned in "
              f"{r['learn_s']}s  braid_ops={r['braid_ops']}  "
              f"alpha_ok={r['alpha_ok']}]")
