"""
chatmodel.py — chat with a REAL standard trained model, entirely on the repo.

⛔ READ hcl-ai/RUNMODEL_USAGE.md FIRST — especially failure mode 6, which was
discovered (the hard way) while verifying THIS file against karpathy's run.c.

This is the layer the user talks to: prompt in, answer out, like regular AI.
Underneath, nothing standard remains in the compute path — every arithmetic
operation of the model's forward pass is an HCL primitive, arranged per the
porting law (skills/hcl-pure/references/06_porting.md: compose, never invent):

    multiply        -> AMP_MOD      (eng.mul)
    add/accumulate  -> COMP         (eng.add / eng.dot)
    subtract        -> COMP∘SHIFT   (eng.sub)
    divide          -> AMP_MOD∘INV  (eng.div)
    sqrt (RMSNorm)  -> FISSION      (eng.sqrt)
    exp (softmax,
         SiLU)      -> MOBIUS_GROWTH (eng.exp)
    attention       -> nemotron_hcl.HCLTensorEngine.attention, verbatim

The model is a REAL legacy checkpoint: karpathy's stories260K — a trained
Llama-2-architecture model (dim=64, 5 layers, GQA 8/4 heads, vocab 512,
trained on TinyStories) — pulled from GitHub as committed blobs
(clebert/llama2.zig, models/tinystories_260k). Its bytes arrive through the
BODY (largemodel.ModelMemory: streaming intake, one-line identity,
holographic windows); its own format is docked as a format_dock handler
(the dock's designed extension surface: handlers ARE the format layer);
each tensor is materialized from a window (verify=True expel path),
boundary-decoded ONCE, converted ONCE by to_fp, and lives on the substrate
as fixed-point integers.

Boundary items, per 06_porting Step 3 (convert at the edges, integer between):
  - the checkpoint's 7-int header, its tokenizer (scores/strings/BPE merge
    order), and its stored RoPE cos/sin tables are the SOURCE MODEL'S OWN
    DATA, parsed at the boundary exactly like the safetensors header;
  - dtype decode + to_fp is the one float crossing, at tensor delivery;
  - argmax/temperature-0 sampling and softmax's max-subtraction are
    comparisons — control at the boundary (nemotron_hcl's own precedent);
  - stopping is the MODEL'S OWN: generation ends when the model emits its
    BOS/EOS delimiter (how run.c stops) or hits its own seq_len.

The trace: one HCLTensorEngine carries the pass; each token's braid length is
recorded and the log cleared with the transcriber's own clear() so the trace
stays bounded per pass. alpha_ok() is checked every token.

USAGE
    python3 hcl-ai/chatmodel.py MODEL.bin TOKENIZER.bin --chat
    python3 hcl-ai/chatmodel.py MODEL.bin TOKENIZER.bin -i "Once upon a time"
"""

import sys, os, struct

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from largemodel import ModelMemory, _decode_boundary          # BODY (verbatim)
from format_dock import registry                              # the dock (verbatim)
from nemotron_hcl import _fp, _val                            # PORT boundary (verbatim)

BOS, EOS = 1, 2


# ── llama2.c legacy checkpoint, docked as a format handler ──────────────
# Registered through format_dock.registry.register — the dock's own
# extension surface. detect() reads the 7-int header from the leading
# window; open() maps tensor names to absolute windows per run.c's
# memory_map_weights layout. Parsing is boundary-only; every byte delivered
# comes through the expel path (mem.window -> verify=True).

def _llama2c_detect(head: bytes) -> bool:
    if len(head) < 28:
        return False
    dim, hidden, layers, heads, kv, vocab, seq = struct.unpack('<7i', head[:28])
    return (0 < dim <= 16384 and 0 < layers <= 512 and 0 < heads <= 256
            and 0 < abs(vocab) <= 1_000_000 and 0 < seq <= 1_000_000
            and heads % max(kv, 1) == 0)

def _llama2c_open(mem, tensor=None, config=False, **_):
    dim, hidden, layers, heads, kv, vocab_signed, seq = struct.unpack(
        '<7i', mem.window(0, 28))
    vocab = abs(vocab_signed)
    shared = vocab_signed > 0
    head_size = dim // heads
    kv_dim = (dim * kv) // heads
    cfg = {'dim': dim, 'hidden_dim': hidden, 'n_layers': layers,
           'n_heads': heads, 'n_kv_heads': kv, 'vocab_size': vocab,
           'seq_len': seq, 'head_size': head_size, 'kv_dim': kv_dim,
           'shared_classifier': shared}
    if config:
        return cfg
    # run.c memory_map_weights order, all F32
    order = [
        ('token_embedding', vocab * dim),
        ('rms_att',         layers * dim),
        ('wq',              layers * dim * dim),
        ('wk',              layers * dim * kv_dim),
        ('wv',              layers * dim * kv_dim),
        ('wo',              layers * dim * dim),
        ('rms_ffn',         layers * dim),
        ('w1',              layers * hidden * dim),
        ('w2',              layers * dim * hidden),
        ('w3',              layers * hidden * dim),
        ('rms_final',       dim),
        ('freq_cis_real',   seq * (head_size // 2)),
        ('freq_cis_imag',   seq * (head_size // 2)),
    ]
    toc, off = {}, 28
    for name, count in order:
        toc[name] = {'offset': off, 'size': count * 4, 'dtype': 'F32'}
        off += count * 4
    toc['wcls'] = toc['token_embedding'] if shared else \
        {'offset': off, 'size': vocab * dim * 4, 'dtype': 'F32'}
    if tensor is None:
        return toc
    t = toc[tensor]
    return mem.window(t['offset'], t['size'])

registry.register('llama2c', _llama2c_detect, _llama2c_open,
                  "llama2.c legacy checkpoint — config=True, toc, or tensor='name'")


# ── the model's own tokenizer (boundary transcription, per run.c) ───────
class Tokenizer:
    def __init__(self, path, vocab_size):
        raw = open(path, 'rb').read()
        self.max_len = struct.unpack('<i', raw[:4])[0]
        self.vocab, self.scores, off = [], [], 4
        for _ in range(vocab_size):
            score, ln = struct.unpack('<fi', raw[off:off + 8]); off += 8
            self.vocab.append(raw[off:off + ln].decode('utf-8', 'replace'))
            self.scores.append(score); off += ln
        self.index = {s: i for i, s in enumerate(self.vocab)}

    def encode(self, text, bos=True):
        toks = [BOS] if bos else []
        if text:
            toks.append(self.index[' '])            # run.c dummy prefix
        for ch in text:
            toks.append(self.index.get(ch, ord(ch) + 3))   # byte fallback +3
        while True:                                  # BPE greedy merge, per run.c
            best, bi = None, -1
            for i in range(len(toks) - 1):
                pair = self.vocab[toks[i]] + self.vocab[toks[i + 1]]
                j = self.index.get(pair)
                if j is not None and (best is None or self.scores[j] > best[1]):
                    best, bi = (j, self.scores[j]), i
            if best is None:
                break
            toks[bi:bi + 2] = [best[0]]
        return toks

    def decode(self, tok, prev):
        piece = self.vocab[tok]
        if prev == BOS and piece.startswith(' '):
            piece = piece[1:]
        if piece.startswith('<0x') and piece.endswith('>'):
            return chr(int(piece[3:-1], 16))
        return piece


# ── the standard model, standing on the substrate ───────────────────────
class StandardModel:
    """A real trained checkpoint running with the repo's HCL logic.
    All weights are fixed-point integers delivered through holographic
    windows; the forward pass is arrangement of the port's ops; the KV cache
    holds substrate integers the way run.c holds floats."""

    def __init__(self, model_path, tokenizer_path, chunk=256 * 1024, quiet=False):
        self.m = ModelMemory(chunk=chunk)
        st = self.m.ingest_file(model_path)
        self.fmt = self.m.format()
        assert self.fmt == 'llama2c', f"dock detected {self.fmt!r}"
        self.cfg = registry.open_with(self.m.mem, 'llama2c', config=True)
        c = self.cfg
        self.tok = Tokenizer(tokenizer_path, c['vocab_size'])
        if not quiet:
            print(f"[body] streamed {st['bytes_folded']} bytes in {st['chunks']} chunks; "
                  f"format={self.fmt}")
            print(f"[body] identity line ({len(self.m.line())} chars): {self.m.line()}")
            print(f"[cfg ] {c}")

        # deliver every tensor onto the substrate: window -> decode ONCE -> to_fp ONCE
        def rows(name, r, cols):
            raw = registry.open_with(self.m.mem, 'llama2c', tensor=name)
            vals = _decode_boundary(raw, 'F32')
            fp = [_fp(v) for v in vals]
            return [fp[i * cols:(i + 1) * cols] for i in range(r)]
        def flat(name):
            raw = registry.open_with(self.m.mem, 'llama2c', tensor=name)
            return [_fp(v) for v in _decode_boundary(raw, 'F32')]

        L, D, H, KD, HS = c['n_layers'], c['dim'], c['hidden_dim'], c['kv_dim'], c['head_size']
        emb = rows('token_embedding', c['vocab_size'], D)
        self.emb = emb
        att = flat('rms_att');  ffn = flat('rms_ffn')
        self.rms_att = [att[l * D:(l + 1) * D] for l in range(L)]
        self.rms_ffn = [ffn[l * D:(l + 1) * D] for l in range(L)]
        def per_layer(name, r, cols):
            all_rows = rows(name, L * r, cols)
            return [all_rows[l * r:(l + 1) * r] for l in range(L)]
        self.wq = per_layer('wq', D, D)
        self.wk = per_layer('wk', KD, D)
        self.wv = per_layer('wv', KD, D)
        self.wo = per_layer('wo', D, D)
        self.w1 = per_layer('w1', H, D)
        self.w2 = per_layer('w2', D, H)
        self.w3 = per_layer('w3', H, D)
        self.rms_final = flat('rms_final')
        self.wcls = self.emb if c['shared_classifier'] else rows('wcls', c['vocab_size'], D)

        from nemotron_hcl import HCLTensorEngine
        import hcl_engine as _E
        self._E = _E
        self.eng = HCLTensorEngine()
        self.eng.t.light()          # counting mode: every generator counted,
                                    # the per-op dict skipped (the word remains
                                    # available via full(); see hcl_engine)
        self.ONE = _fp(1.0)
        self.EPS = _fp(1e-5)
        self.inv_dim = self.eng.div(self.ONE, _fp(float(D)))
        # RoPE inverse frequencies: this checkpoint is the on-the-fly v1 format
        # (run.c computes freq = 1/10000^(i/head_size) per pair, no stored
        # tables — see run.c line 137 "used to be freq_cis"). These are the
        # model's OWN positional constants; like its stored tables would have
        # been, they cross the float boundary ONCE (06_porting Step 3), exactly
        # as to_fp converts any model constant. Everything after — pos*inv_freq,
        # the rotation — is integer on the substrate.
        self.inv_freq = [_fp(1.0 / (10000.0 ** (2 * j / HS))) for j in range(HS // 2)]
        self.reset()

    def reset(self):
        c = self.cfg
        self.k_cache = [[] for _ in range(c['n_layers'])]   # per layer: list of [kv_dim] fp
        self.v_cache = [[] for _ in range(c['n_layers'])]

    # ── ops composed from the port's engine (nothing new) ───────────────
    def _rmsnorm(self, x, w):
        e = self.eng
        ss = 0
        for xi in x:
            ss = e.add(ss, e.mul(xi, xi))
        ss = e.add(e.mul(ss, self.inv_dim), self.EPS)
        inv = e.div(self.ONE, e.sqrt(ss))
        return [e.mul(e.mul(wi, xi), inv) for wi, xi in zip(w, x)]

    def _rope(self, vec, pos, upto):
        """Rotate adjacent pairs by angle = pos * inv_freq[head_dim/2], with the
        angle -> cos/sin done through the engine's PHASE_COS/PHASE_SIN (which
        take phase_frac = angle/2π). run.c v1 formula, on the substrate."""
        e, HS = self.eng, self.cfg['head_size']
        TWO_PI = 2 * self._E.PI_INT
        for i in range(0, upto, 2):
            j = (i % HS) // 2
            val = e.mul(_fp(float(pos)), self.inv_freq[j])   # pos * inv_freq  (fixed-point radians)
            pf = e.div(val, TWO_PI) % self._E.SCALE          # radians -> phase_frac
            fcr = e.t.cos(pf); fci = e.t.sin(pf)             # PHASE_COS / PHASE_SIN
            v0, v1 = vec[i], vec[i + 1]
            vec[i]     = e.sub(e.mul(v0, fcr), e.mul(v1, fci))
            vec[i + 1] = e.add(e.mul(v0, fci), e.mul(v1, fcr))

    def _silu_mul(self, h1, h3):
        """SwiGLU: h1 * sigmoid(h1) * h3 — exp/add/div/mul, per element."""
        e = self.eng
        out = []
        for a, b in zip(h1, h3):
            sig = e.div(self.ONE, e.add(self.ONE, e.exp(e.sub(0, a))))
            out.append(e.mul(e.mul(a, sig), b))
        return out

    def forward(self, token, pos):
        """One position through every layer, entirely on the substrate.
        Mirrors run.c's forward() op for op; returns fixed-point logits."""
        e, c = self.eng, self.cfg
        D, HS, KD = c['dim'], c['head_size'], c['kv_dim']
        H, KV = c['n_heads'], c['n_kv_heads']
        x = list(self.emb[token])
        for l in range(c['n_layers']):
            xb = self._rmsnorm(x, self.rms_att[l])
            q = [e.dot(xb, row) for row in self.wq[l]]
            k = [e.dot(xb, row) for row in self.wk[l]]
            v = [e.dot(xb, row) for row in self.wv[l]]
            self._rope(q, pos, D)
            self._rope(k, pos, KD)
            self.k_cache[l].append(k)
            self.v_cache[l].append(v)
            # GQA attention: the port's own attention per head
            attn_out = [0] * D
            per_kv = H // KV
            for h in range(H):
                g = h // per_kv
                Q = q[h * HS:(h + 1) * HS]
                K = [kt[g * HS:(g + 1) * HS] for kt in self.k_cache[l]]
                V = [vt[g * HS:(g + 1) * HS] for vt in self.v_cache[l]]
                oh = e.attention(Q, K, V, HS)          # nemotron_hcl, verbatim
                attn_out[h * HS:(h + 1) * HS] = oh
            xb2 = [e.dot(attn_out, row) for row in self.wo[l]]
            x = [e.add(xi, yi) for xi, yi in zip(x, xb2)]          # residual
            xb = self._rmsnorm(x, self.rms_ffn[l])
            h1 = [e.dot(xb, row) for row in self.w1[l]]
            h3 = [e.dot(xb, row) for row in self.w3[l]]
            hb = self._silu_mul(h1, h3)
            mlp = [e.dot(hb, row) for row in self.w2[l]]
            x = [e.add(xi, yi) for xi, yi in zip(x, mlp)]          # residual
        x = self._rmsnorm(x, self.rms_final)
        return [e.dot(x, row) for row in self.wcls]                # logits

    def generate(self, prompt, steps=None, stream=None):
        """Prompt in, answer out — like regular AI, automatically.
        Greedy (temperature 0): argmax is a boundary comparison on the
        fixed-point integers themselves. Stops when the MODEL emits its own
        BOS/EOS delimiter (run.c's own condition) or reaches its seq_len;
        `steps` is the runner's delivery bound (run.c's -n)."""
        self.reset()
        toks = self.tok.encode(prompt, bos=True)
        out_text, braids = [], []
        pos, token = 0, toks[0]
        _mark = self.eng.t.braid_len
        limit = self.cfg['seq_len'] if steps is None else min(
            self.cfg['seq_len'], len(toks) + steps)
        while pos < limit:
            logits = self.forward(token, pos)
            braids.append(self.eng.t.braid_len - _mark)
            _mark = self.eng.t.braid_len
            self.eng.t.clear()                        # the transcriber's own clear()
            assert self.eng.alpha_ok()                # checksum every token
            if pos + 1 < len(toks):
                nxt = toks[pos + 1]                   # teacher-forced prompt
            else:
                best, nxt = None, 0
                for i, lg in enumerate(logits):       # argmax: boundary comparison
                    if best is None or lg > best:
                        best, nxt = lg, i
            if pos + 1 >= len(toks) and nxt in (BOS, EOS):
                break                                 # the model's own stop
            piece = self.tok.decode(nxt, token)
            if pos + 1 >= len(toks):
                out_text.append(piece)
                if stream:
                    stream(piece)
            token = nxt
            pos += 1
        return {'text': prompt + ''.join(out_text),
                'completion': ''.join(out_text),
                'tokens': pos + 1,
                'braid_ops_per_token': braids[:3] + (['...'] if len(braids) > 3 else []),
                'alpha_ok': self.eng.alpha_ok()}


if __name__ == '__main__':
    import argparse, time
    _REPO = os.path.dirname(_HERE)
    _DEF_MODEL = os.path.join(_REPO, 'models/tinystories_260k/stories260K.bin')
    _DEF_TOK   = os.path.join(_REPO, 'models/tinystories_260k/tok512.bin')
    ap = argparse.ArgumentParser(
        description="Chat with a standard trained model running entirely on "
                    "the HCL substrate. With no arguments: a chat REPL on the "
                    "bundled stories260K model. Point it at any llama2.c "
                    "checkpoint to run that instead.")
    ap.add_argument('model', nargs='?', default=_DEF_MODEL)
    ap.add_argument('tokenizer', nargs='?', default=_DEF_TOK)
    ap.add_argument('-i', '--prompt', default=None,
                    help="one-shot: generate from this prompt and exit")
    ap.add_argument('--steps', type=int, default=None,
                    help="delivery bound (like run.c -n); default: model's own stop")
    ap.add_argument('--chat', action='store_true',
                    help="chat REPL (already the default when -i is not given)")
    args = ap.parse_args()

    if not os.path.exists(args.model):
        sys.exit(f"model not found: {args.model}\n"
                 f"(the bundled one lives at models/tinystories_260k/ — "
                 f"run from the repo, or pass paths: chatmodel.py MODEL.bin TOK.bin)")

    print("waking the model onto the substrate (~1 min, pure integer)…")
    model = StandardModel(args.model, args.tokenizer)
    print(f"[port] every op on the substrate; alpha_ok={model.eng.alpha_ok()}")
    print("[note] exact ≠ fast: ~0.25s/token on this checkpoint — every token is "
          "~531K counted braid generators with an α checksum.\n")

    def run_once(prompt):
        t0 = time.time()
        sys.stdout.write(prompt); sys.stdout.flush()
        r = model.generate(prompt, steps=args.steps,
                           stream=lambda p: (sys.stdout.write(p), sys.stdout.flush()))
        dt = time.time() - t0
        print(f"\n[{r['tokens']} tokens, {dt:.1f}s, "
              f"~{r['braid_ops_per_token'][0]} braid ops/token, alpha_ok={r['alpha_ok']}]")

    if args.prompt is not None:
        run_once(args.prompt)
    else:
        print("chat — type a story opening, the model continues it to its own "
              "stop (empty line or Ctrl-D to quit)")
        while True:
            try:
                prompt = input("\nyou> ").strip()
            except EOFError:
                print()
                break
            if not prompt:
                break
            run_once(prompt)
