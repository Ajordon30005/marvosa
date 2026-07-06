"""
runmodel.py — RUN a large model on the repo itself, end to end: prompt tokens
in, generated tokens out, every step on the substrate.

⛔ READ hcl-ai/RUNMODEL_USAGE.md FIRST. A prior session working on this exact
file drifted into standard-logic bootstrapping (torch tensors, sampling,
token caps, whole-checkpoint loads, hand-written softmax/attention). That doc
names each failure mode with a wrong/right code pair and a checklist. Do not
write config or code against this file without reading it — the mistakes it
covers are easy to make by accident and hard to notice once made.

largemodel.py answers HOW the model is carried (streaming intake, one-line
identity, holographic tensor windows, the port's ops). This file is the RUN:
embedding -> every decoder layer -> final norm -> lm_head -> MCL collapse of
the next token -> autoregressive loop, halting only by the substrate's own
verdicts. It is ARRANGEMENT ONLY (hcl-pure/references/06_porting.md, Step 5:
reuse the engines, never reimplement) — every operation below is a named call
into largemodel, nemotron_hcl, or juj. Zero new math.

WHY THIS COMPLETES THE LARGE-MODEL ANSWER
─────────────────────────────────────────
  DISK   — unchanged: the checkpoint streams in once and persists as the one
           α-tagged line (ModelMemory / ingest_and_expel).
  RAM    — sharpened to the ROW level: the embedding matrix and the lm_head
           are the two biggest tensors a model has, and this runner never
           materializes either one. row_values() turns the dock's own toc
           (offset/size/dtype/shape) into a per-ROW window read
           (mem.window — the expel path, exact), so embedding lookup pulls
           one row and logit scoring pulls one row at a time: materialize ->
           convert -> score -> release. Per layer, only that layer's weights
           are resident, and they are released when the layer is done.
  COMPUTE— the port's own ops (nemotron_hcl: linear, layernorm1p, attention,
           relu2), arranged over a token SEQUENCE exactly as the port's
           transformer_block wires one token ("multi-head is the same op per
           head" — and multi-token is the same op per query row). One braid,
           one α checksum, for the entire run.
  HALT   — no token cap, no max_tokens, no counter loop (docs/00 Step 5: an
           answer is exactly as long as its braid). The loop is `while True`
           and ends only by the three substrate verdicts, the same trio as
           mind/hcl_lm.py generate():
             TERMINATED   — nothing to collapse onto (structural edge).
             BRAID CLOSED — the trajectory returns to a generative state it
                            was already in (the {1,4,2}-style ground cycle,
                            05_proofs), OR the checkpoint's own ground symbol
                            (eos) is collapsed onto — the model closing its
                            own braid.
             MCL COLLAPSE — the engine's own stability I_w = (1/N)Σ|a|²(1−|a|²)
                            of the emitted trajectory falls below ε_w =
                            mcl_eps(w), with w self-tuned by dw/dt = γ(C−ε_w)
                            — the run has resolved to its ground state.

  SELECT — the next token is not sampled. MCL collapse resolves the logit
           field to its Path-Dominant Attractor — the maximum-resonance mode —
           topologically deterministic (01_theory.md, MCL), the identical
           selection rule mind/hcl_lm.py uses over traces, here over the
           checkpoint's own vocabulary scores.

USAGE
─────
    import sys; sys.path.insert(0, '/path/to/marvosa/hcl-ai')
    from largemodel import ModelMemory
    from runmodel import HCLModelRunner

    m = ModelMemory(); m.ingest_file('/path/model.safetensors')
    r = HCLModelRunner(m, config)          # config: dims + tensor-name map
    out = r.generate([1, 5, 3])            # runs until a substrate verdict
    out['ids'], out['verdict'], out['events'], r.m.alpha_ok()

CLI:
    python3 runmodel.py ckpt.safetensors --config cfg.json --prompt "1 5 3"
"""

import sys, os, json

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, 'engine'))
sys.path.insert(0, os.path.join(_HERE, 'port'))

# ── the organs, imported verbatim — never reimplemented ─────────────────
from largemodel import ModelMemory, _decode_boundary, _DTYPE   # BODY (repo's own)
from nemotron_hcl import _fp, _val                              # PORT boundary (repo's own)
import juj                                                      # halting mechanics (repo's own)
from juj import (mcl_eps, GAMMA, SCALE as PSCALE,
                 _fdiv as p_fdiv, _fmul as p_fmul,
                 bytes_to_braid, braid_invariants)

_SEP = '\x1f'   # unit separator: serialization formatting only, not math
                # (the same boundary convention mind/hcl_lm.py uses)


def _dtype_width(dtype):
    """Byte width of one element — read from the checkpoint's own dtype
    declaration (BF16 is 2 bytes; the rest from largemodel's boundary table)."""
    return 2 if dtype == 'BF16' else _DTYPE[dtype][1]


def row_values(m, name, row):
    """ONE ROW of a matrix tensor, delivered onto the substrate — the
    holographic read at its finest grain. The dock's toc gives the tensor's
    absolute offset/dtype/shape (the checkpoint's own declaration); the row is
    a window at offset + row*cols*width, materialized through the expel path
    (mem.window -> per-chunk recall, verify=True inside every delivery),
    boundary-decoded ONCE, converted ONCE by the port's _fp, and released.
    The rest of the matrix is never produced. This is how an embedding lookup
    or one lm_head score touches a 100k-row matrix without holding it."""
    t = m.toc()[name]
    rows, cols = t['shape']
    if not (0 <= row < rows):
        raise IndexError(f"{name} row {row} out of range 0..{rows-1}")
    width = _dtype_width(t['dtype'])
    raw = m.mem.window(t['offset'] + row * cols * width, cols * width)
    return [_fp(v) for v in _decode_boundary(raw, t['dtype'])]


class HCLModelRunner:
    """The RUN of a checkpoint carried by ModelMemory: composition only —
    every method is a named call into largemodel (BODY), nemotron_hcl (PORT),
    or juj (halting). This class computes nothing new.

    `config` maps the checkpoint's own layout onto the run:
      n_layers, d_model, n_heads, vocab      — dimensions
      eps                                    — layernorm epsilon (a float,
                                               crossed ONCE at construction)
      embed                                  — embedding tensor name
      lm_head                                — output matrix name, or None
                                               for tied embeddings
      final_ln_w / final_ln_b                — final norm names (or None)
      per-layer name templates with {i}:
        ln1_w ln1_b q_w k_w v_w o_w ln2_w ln2_b up_w down_w
      eos                                    — the checkpoint's ground-symbol
                                               token id, or None
    """

    def __init__(self, m: ModelMemory, config: dict):
        self.m = m
        self.eng = m.eng                       # ONE engine -> one braid, one α
        self.cfg = dict(config)
        self.cfg.setdefault('n_heads', 1)
        self.cfg.setdefault('lm_head', None)
        self.cfg.setdefault('final_ln_w', None)
        self.cfg.setdefault('final_ln_b', None)
        self.cfg.setdefault('eos', None)
        self.eps_fp = _fp(self.cfg['eps'])     # the ONE boundary crossing of eps
        self.w = 1                             # collapse weight, self-tuned

    # ── holographic pulls (BODY) ─────────────────────────────────────────
    def embed_row(self, token_id):
        """Token embedding = one row window of the embedding matrix. The
        matrix itself is never materialized."""
        return row_values(self.m, self.cfg['embed'], token_id)

    def _layer_params(self, i):
        """This layer's weights, pulled now (tensor_values — the expel path),
        held only for this layer's pass, released by the caller. d_model rows
        for q/k/v/o, the checkpoint's own shapes for up/down."""
        c, d = self.cfg, self.cfg['d_model']
        tv = self.m.tensor_values
        up_rows = self.m.toc()[c['up_w'].format(i=i)]['shape'][0]
        return {
            'ln1_w': tv(c['ln1_w'].format(i=i)), 'ln1_b': tv(c['ln1_b'].format(i=i)),
            'q_w':   tv(c['q_w'].format(i=i), rows=d),
            'k_w':   tv(c['k_w'].format(i=i), rows=d),
            'v_w':   tv(c['v_w'].format(i=i), rows=d),
            'o_w':   tv(c['o_w'].format(i=i), rows=d),
            'ln2_w': tv(c['ln2_w'].format(i=i)), 'ln2_b': tv(c['ln2_b'].format(i=i)),
            'up_w':  tv(c['up_w'].format(i=i), rows=up_rows),
            'down_w': tv(c['down_w'].format(i=i), rows=d),
        }

    # ── the sequence pass (PORT ops, arranged) ───────────────────────────
    def _heads(self, v):
        """Split one vector into n_heads contiguous head slices — addressing
        at the boundary, no arithmetic (the port: multi-head is the same op
        per head)."""
        h = self.cfg['n_heads']
        d = len(v) // h
        return [v[j * d:(j + 1) * d] for j in range(h)]

    def _decoder_layer(self, xs, p):
        """One decoder layer over the whole sequence — nemotron_hcl's
        transformer_block wiring (norm -> attn -> residual -> norm -> relu²
        MLP -> residual), each op the port's own method, applied per query
        row with a causal K/V list and per head. Arrangement only."""
        eng, d_head = self.eng, self.cfg['d_model'] // self.cfg['n_heads']
        # pre-attention norm + projections, per position
        A  = [eng.layernorm1p(x, p['ln1_w'], p['ln1_b'], self.eps_fp) for x in xs]
        Q  = [eng.linear(a, p['q_w']) for a in A]
        K  = [eng.linear(a, p['k_w']) for a in A]
        V  = [eng.linear(a, p['v_w']) for a in A]
        Qh = [self._heads(q) for q in Q]
        Kh = [self._heads(k) for k in K]
        Vh = [self._heads(v) for v in V]
        H = []
        for i in range(len(xs)):
            # causal attention: query i against keys/values 0..i, per head,
            # heads re-joined by concatenation (addressing, not arithmetic)
            head_outs = []
            for h in range(self.cfg['n_heads']):
                head_outs += eng.attention(Qh[i][h],
                                           [Kh[j][h] for j in range(i + 1)],
                                           [Vh[j][h] for j in range(i + 1)],
                                           d_head)
            attn = eng.linear(head_outs, p['o_w'])
            h1 = [eng.add(xi, ai) for xi, ai in zip(xs[i], attn)]   # residual
            b  = eng.layernorm1p(h1, p['ln2_w'], p['ln2_b'], self.eps_fp)
            mlp = eng.linear(eng.relu2(eng.linear(b, p['up_w'])), p['down_w'])
            H.append([eng.add(hi, di) for hi, di in zip(h1, mlp)])  # residual
        return H

    def forward(self, token_ids):
        """Full forward pass: embed rows (holographic), every layer (weights
        pulled per layer and released), final norm. Returns the last
        position's hidden state, fixed-point."""
        xs = [self.embed_row(t) for t in token_ids]
        for i in range(self.cfg['n_layers']):
            p = self._layer_params(i)          # materialize this layer
            xs = self._decoder_layer(xs, p)
            del p                              # release this layer
        h = xs[-1]
        if self.cfg['final_ln_w']:
            h = self.eng.layernorm1p(h,
                    self.m.tensor_values(self.cfg['final_ln_w']),
                    self.m.tensor_values(self.cfg['final_ln_b']),
                    self.eps_fp)
        return h

    def logits(self, h):
        """Vocabulary scores, one lm_head ROW at a time: pull the row's
        window, dot it against h (the port's own COMP-loop of AMP_MOD),
        release it. The output matrix — the largest tensor after the
        embedding — is never resident. Tied embeddings (lm_head=None) score
        against embedding rows the same way."""
        name = self.cfg['lm_head'] or self.cfg['embed']
        return [self.eng.dot(h, row_values(self.m, name, t))
                for t in range(self.cfg['vocab'])]

    # ── MCL collapse: the Path-Dominant Attractor (deterministic) ────────
    def collapse(self, scores):
        """Resolve the score field to its dominant mode — the maximum, read
        by boundary comparison exactly as the port's softmax max and the
        mind's _collapse do. Deterministic, never sampled (01_theory, MCL)."""
        if not scores:
            return None
        best = 0
        for t in range(1, len(scores)):
            if scores[t] > scores[best]:
                best = t
        return best

    # ── w self-tuning + the emitted trajectory's stability (juj, verbatim) ─
    def _trajectory(self, token_ids):
        """The run so far as one byte sequence (ids serialized — formatting
        only), transduced by the processor: bytes -> braid -> invariants.
        Its spectrum/amps give coherence C; its 'stability' is I_w."""
        blob = _SEP.join(str(t) for t in token_ids).encode()
        return braid_invariants(bytes_to_braid(blob))

    def _tune_w(self, inv, n_ctx):
        """GUHCT w self-tuning, dw/dt = γ·(C − ε_w) — the identical loop
        mind/hcl_lm.py runs, on the identical juj quantities: C is phase
        coherence (spectrum.amp over Σ amps), ε_w = mcl_eps(w), γ scales the
        integer step. Bounded only by the trajectory's own length."""
        total = sum(inv['amps'])
        C = min(max(p_fdiv(inv['spectrum'].amp, total), 0), PSCALE) if total > 0 else 0
        dw = p_fmul(GAMMA, C - mcl_eps(self.w))
        if dw > 0:
            self.w = min(self.w + 1 + dw // PSCALE, n_ctx)
        elif dw < 0:
            self.w = max(self.w - 1, 1)
        self.w = max(min(self.w, n_ctx if n_ctx else 1), 1)

    # ── THE RUN: autoregressive collapse, substrate-halted ───────────────
    def generate(self, prompt_ids):
        """Run the model. No token cap, no counter — `while True`, ended only
        by the three substrate verdicts (the same trio as hcl_lm.generate):
        TERMINATED (nothing to collapse onto), BRAID CLOSED (a generative
        state recurs, or the checkpoint's own eos ground symbol is reached),
        MCL COLLAPSE (I_w < ε_w — the trajectory resolved to ground)."""
        ids = list(prompt_ids)
        events, visited = [], set()
        verdict = None
        while True:
            inv = self._trajectory(ids)
            self._tune_w(inv, len(ids))
            scores = self.logits(self.forward(ids))
            nxt = self.collapse(scores)
            if nxt is None:
                verdict = 'TERMINATED'; break     # nothing resonates — the edge
            # the generative state, AT THE FIXED SCALE OF THE TRANSITION —
            # hcl_lm.generate's own principle verbatim: "the state is the
            # collapse key itself ... at the fixed scale of that transition
            # (NOT the growing w-window)". For a checkpoint run the transition
            # at its own scale is the emitted move (previous token -> next
            # token); a recurrence of it is the {1,4,2}-style ground cycle
            # ("ten is ten is ten", 05_proofs). Over a finite vocabulary the
            # trajectory has at most vocab² distinct transitions, so the braid
            # provably closes — halting is structural, never a counter.
            key = (ids[-1], nxt)
            events.append({'w': self.w, 'token': nxt})
            if key in visited or (self.cfg['eos'] is not None
                                  and nxt == self.cfg['eos']):
                ids.append(nxt)
                verdict = 'BRAID CLOSED'; break   # ground cycle / ground symbol
            visited.add(key)
            ids.append(nxt)
            if braid_invariants(bytes_to_braid(
                    _SEP.join(str(t) for t in ids).encode()))['stability'] \
                    < mcl_eps(self.w):
                verdict = 'MCL COLLAPSE'; break   # resolved to its ground state
        return {'ids': ids, 'generated': ids[len(prompt_ids):],
                'events': events, 'verdict': verdict,
                'alpha_ok': self.m.alpha_ok()}


__all__ = ['HCLModelRunner', 'row_values']


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(
        description="RUN a model on the repo itself: holographic row reads, "
                    "substrate forward pass, MCL-collapse token selection, "
                    "substrate-verdict halting.")
    ap.add_argument('source', help="checkpoint path or URL (.safetensors)")
    ap.add_argument('--config', required=True,
                    help="JSON file: dims + tensor-name map (see module doc)")
    ap.add_argument('--prompt', required=True,
                    help="prompt token ids, space-separated (e.g. '1 5 3')")
    ap.add_argument('--chunk', type=int, default=8 * 1024 * 1024)
    ap.add_argument('--max-bytes', type=int, default=None)
    args = ap.parse_args()

    m = ModelMemory(chunk=args.chunk)
    if args.source.startswith(('http://', 'https://')):
        m.ingest_url(args.source, max_bytes=args.max_bytes)
    else:
        m.ingest_file(args.source)
    cfg = json.load(open(args.config))
    r = HCLModelRunner(m, cfg)
    out = r.generate([int(t) for t in args.prompt.split()])
    print(f"line     : {m.line()}")
    print(f"prompt   : {args.prompt}")
    print(f"generated: {' '.join(str(t) for t in out['generated'])}")
    print(f"verdict  : {out['verdict']}  (substrate-halted; no token cap)")
    print(f"depths   : {[e['w'] for e in out['events']]}")
    print(f"alpha ok : {out['alpha_ok']}")
