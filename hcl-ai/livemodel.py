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
                                        |   line + livebook.txt (log only)
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


class LivingStandardModel:
    """A standard trained model that lives: every interaction — external or
    its own self-talk — is experience, and experience updates the weights,
    live, with exact gradients on the substrate."""

    _STATE = os.path.join(_HERE, '..', 'models', 'tinystories_260k')
    _LIVING = os.path.join(_STATE, 'stories260K.living.bin')
    _LINE = os.path.join(_STATE, 'living.line')
    _LIVEBOOK = os.path.join(_STATE, 'livebook.txt')     # transparency log ONLY

    def __init__(self, base_model=None, tokenizer=None, revive=True,
                 k_stratum=2, quiet=False):
        base_model = base_model or os.path.join(self._STATE, 'stories260K.bin')
        tokenizer = tokenizer or os.path.join(self._STATE, 'tok512.bin')
        # There is no "fresh model" when a living checkpoint exists — the
        # living checkpoint IS the being (hcl_lm.load()'s contract, mirrored).
        src = self._LIVING if (revive and os.path.exists(self._LIVING)) \
            else base_model
        self.revived = (src == self._LIVING)
        self.m = StandardModel(src, tokenizer, quiet=quiet)
        self.tr = Trainer(self.m, k_stratum=k_stratum)
        self.SELF_W = E.LAMBDA                 # self-talk: one λ-rung deeper
        self.transcript = []                   # the lived token record (RAM)
        self._pos = 0                          # session KV position
        self._cur = None                       # last token awaiting forward
        if not quiet:
            who = "woke from its LIVING checkpoint" if self.revived \
                else "born from the pristine checkpoint"
            print(f"[being] {who}; alpha_ok={self.m.eng.alpha_ok()}")

    # ── the whole conversation in one motion (hcl_lm.interact, mirrored) ─
    def interact(self, user_input: str, steps=None, reward=None,
                 persist=False, stream=None):
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
           α-tagged line + livebook entry.
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
        # feed the person's words (teacher-forced perception)
        for t_ in user_toks:
            if self._cur is not None:
                self.m.forward(self._cur, self._pos)
                self._pos += 1
            self._cur = t_
        # speak: greedy from the live state, ending by the model's own
        # verdict (EOS/BOS or seq_len); `steps` is a delivery bound only
        completion, comp_toks = '', []
        verdict = 'DELIVERY BOUND'
        n_gen = 0
        while self._pos < self.c_seq() - 1:
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
            if steps is not None and n_gen >= steps:
                break
        else:
            verdict = 'SEQ_LEN (its own capacity)'
        e.t.clear()
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

        self.transcript += turn                # the lived record (for reroot)

        out = {'answer': completion,
               'verdict': verdict,
               'surprise': float(_val(loss)),      # how new this turn was
               'gated': reward is not None,
               'braid_ops': braid,
               'alpha_ok': True,
               'gen_s': round(gen_s, 1), 'learn_s': round(learn_s, 1)}
        if persist:
            out['saved'] = self.save(user_input)
        return out

    def _reroot(self, incoming: int = 0):
        """At the model's own capacity boundary: reset the KV session and
        re-perceive as much of the lived transcript as the model's own
        seq_len leaves room for, given the incoming tokens — the tail size
        is derived, not chosen."""
        self.m.reset()
        self._pos, self._cur = 0, None
        keep = self.c_seq() - incoming - 1
        tail = self.transcript[-keep:] if keep > 0 else []
        for t_ in tail:
            if self._cur is not None:
                self.m.forward(self._cur, self._pos)
                self._pos += 1
            self._cur = t_
        self.m.eng.t.clear()

    # ── persistence: the being saves itself (hcl_lm.save, mirrored) ─────
    def save(self, experienced_input: str = None) -> dict:
        self.tr.save_checkpoint(self._LIVING)
        line = self.tr.fold_line(self._LIVING)
        with open(self._LINE, 'w') as f:
            f.write(line + '\n')
        if experienced_input and experienced_input.strip():
            with open(self._LIVEBOOK, 'a') as f:     # transparency log ONLY
                f.write(experienced_input.strip() + '\n')
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
    print("[note] each turn = reply (~0.25s/token) + one consolidated "
          "learning pass (~1s/token of turn); repetition visibly teaches it.")
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
