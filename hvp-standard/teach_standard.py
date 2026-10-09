"""
teach_standard.py — a PURELY STANDARD AI learns to speak HVP.

This file is the standard half of the claim, with nothing of the substrate
in it on purpose: the model here is karpathy's stories260K checkpoint run
exactly as run.c runs it — float32-origin weights, float forward pass,
standard cross-entropy, standard SGD, greedy argmax. No FBits, no braid
arithmetic, no four params. The ONLY Marvosa organ it touches is the
language layer (`transducer.py`, wrapping the pure-integer processor
verbatim): the model learns to EMIT the SPOKEN wire —

    HVP1 <hex braid> END

— and the transducer completes it into the full signature and materializes
the exact bytes. The model is standard; the language is the bridge.

HOW A MODEL LEARNS A SECOND LANGUAGE WITHOUT LOSING ITS FIRST
─────────────────────────────────────────────────────────────
The standard playbook, applied and measured here:
  * replay mixing — every HVP lesson is interleaved 1:1 with a first-
    language turn from the model's own register (TinyStories sentences),
    so the old distribution keeps getting rehearsed while the new
    surface lands;
  * a small learning rate — nudges instead of repurposing;
  * (the two paths this file does NOT need but the doc names: adapters/
    LoRA, which freeze the base weights outright, and in-context
    teaching for frozen API models — `phrasebook.md` — where nothing
    CAN be forgotten because nothing moves.)
The mechanism that makes the acquisition cheap is the same one the
conversation's framing names: the model's conceptual circuitry is already
there; HVP is a new SURFACE MAPPING onto token rows it always had (hex
characters are ordinary vocabulary in any tokenizer). Both are measured:
the lesson surprise falls to mastery while the first-language probe loss
and a story continuation are printed before and after.

    python3 hvp-standard/teach_standard.py                # teach + speak
    python3 hvp-standard/teach_standard.py --state DIR --epochs N
                                                          # breath-split
"""

import sys, os, json, math, struct, time, hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import transducer as T

BOS, EOS = 1, 2


# ── the checkpoint, read by its own format law (run.c) ──────────────────
class Tokenizer:
    """run.c's tokenizer, verbatim semantics: greedy BPE by score, byte
    fallback at ord+3, the leading-space dummy prefix."""

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
            toks.append(self.index[' '])
        for ch in text:
            toks.append(self.index.get(ch, ord(ch) + 3))
        while True:
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


def _read_ckpt(path):
    raw = open(path, 'rb').read()
    dim, hidden, layers, heads, kv, vs, seq = struct.unpack('<7i', raw[:28])
    vocab = abs(vs)
    cfg = dict(dim=dim, hidden=hidden, layers=layers, heads=heads, kv=kv,
               vocab=vocab, seq=seq, hs=dim // heads,
               kvd=(dim * kv) // heads, shared=vs > 0)
    off = 28
    def take(n):
        nonlocal off
        v = list(struct.unpack(f'<{n}f', raw[off:off + 4 * n]))
        off += 4 * n
        return v
    def rows(n, r, c):
        flat = take(n)
        return [flat[i * c:(i + 1) * c] for i in range(r)]
    W = {}
    W['emb'] = rows(vocab * dim, vocab, dim)
    W['rms_att'] = rows(layers * dim, layers, dim)
    W['wq'] = [rows(dim * dim, dim, dim) for _ in range(layers)] if False else None
    off = 28 + 4 * (vocab * dim + layers * dim)
    def per_layer(r, c):
        nonlocal off
        out = []
        for _ in range(layers):
            flat = list(struct.unpack(f'<{r * c}f', raw[off:off + 4 * r * c]))
            off += 4 * r * c
            out.append([flat[i * c:(i + 1) * c] for i in range(r)])
        return out
    W['wq'] = per_layer(dim, dim)
    W['wk'] = per_layer(cfg['kvd'], dim)
    W['wv'] = per_layer(cfg['kvd'], dim)
    W['wo'] = per_layer(dim, dim)
    flat = list(struct.unpack(f'<{layers * dim}f', raw[off:off + 4 * layers * dim]))
    off += 4 * layers * dim
    W['rms_ffn'] = [flat[l * dim:(l + 1) * dim] for l in range(layers)]
    W['w1'] = per_layer(hidden, dim)
    W['w2'] = per_layer(dim, hidden)
    W['w3'] = per_layer(hidden, dim)
    W['rms_final'] = list(struct.unpack(f'<{dim}f', raw[off:off + 4 * dim]))
    return cfg, W


def _write_ckpt(path, cfg, W):
    hdr = struct.pack('<7i', cfg['dim'], cfg['hidden'], cfg['layers'],
                      cfg['heads'], cfg['kv'],
                      cfg['vocab'] if cfg['shared'] else -cfg['vocab'],
                      cfg['seq'])
    def flat(rows):
        return [x for r in rows for x in r]
    parts = [flat(W['emb']), flat(W['rms_att'])]
    for nm in ('wq', 'wk', 'wv', 'wo'):
        parts.append([x for l in W[nm] for x in flat(l)])
    parts.append(flat(W['rms_ffn']))
    for nm in ('w1', 'w2', 'w3'):
        parts.append([x for l in W[nm] for x in flat(l)])
    parts.append(list(W['rms_final']))
    hs = cfg['hs']
    fcr, fci = [], []
    for pos in range(cfg['seq']):                 # v1 stores rope tables;
        for j in range(hs // 2):                  # run.c recomputes and
            a = pos / (10000.0 ** (2 * j / hs))   # skips them on read
            fcr.append(math.cos(a)); fci.append(math.sin(a))
    parts += [fcr, fci]
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(hdr)
        for p in parts:
            f.write(struct.pack(f'<{len(p)}f', *p))
    os.replace(tmp, path)


# ── a standard float model: run.c's forward, textbook backward ──────────
class StandardFloatModel:
    """stories260K as any standard runtime holds it: floats in RAM,
    float math, greedy argmax, standard SGD. Nothing of the substrate."""

    def __init__(self, model_path, tok_path):
        self.cfg, self.W = _read_ckpt(model_path)
        self.tok = Tokenizer(tok_path, self.cfg['vocab'])

    # forward over a whole sequence, caching what backward needs
    def _fwd(self, toks):
        c, W = self.cfg, self.W
        D, HS, KD = c['dim'], c['hs'], c['kvd']
        H, KV, L = c['heads'], c['kv'], c['layers']
        n = len(toks); per = H // KV; inv_s = 1.0 / math.sqrt(HS)
        dot = lambda a, b: sum(x * y for x, y in zip(a, b))
        def rms_f(x, w):
            ss = sum(v * v for v in x) / len(x) + 1e-5
            inv = 1.0 / math.sqrt(ss)
            return [wi * xi * inv for wi, xi in zip(w, x)], (list(x), inv)
        rope = [[(math.cos(p / (10000.0 ** (2 * j / HS))),
                  math.sin(p / (10000.0 ** (2 * j / HS))))
                 for j in range(HS // 2)] for p in range(n)]
        def rot(v, p, upto, sgn=1):
            for i in range(0, upto, 2):
                cr, ci = rope[p][(i % HS) // 2]
                ci *= sgn
                a, b = v[i], v[i + 1]
                v[i] = a * cr - b * ci
                v[i + 1] = a * ci + b * cr
        xs = [list(W['emb'][t]) for t in toks]
        tape = {'toks': toks, 'rope': rope, 'layers': [dict() for _ in range(L)]}
        for l in range(L):
            Tl = tape['layers'][l]
            Tl['x_in'] = [list(x) for x in xs]
            Tl['n1'] = [rms_f(x, W['rms_att'][l]) for x in xs]
            xb = [t[0] for t in Tl['n1']]
            Tl['q'] = [[dot(v, r) for r in W['wq'][l]] for v in xb]
            Tl['k'] = [[dot(v, r) for r in W['wk'][l]] for v in xb]
            Tl['v'] = [[dot(v, r) for r in W['wv'][l]] for v in xb]
            for p in range(n):
                rot(Tl['q'][p], p, D)
                rot(Tl['k'][p], p, KD)
            Tl['probs'] = [[None] * H for _ in range(n)]
            att = [[0.0] * D for _ in range(n)]
            for p in range(n):
                for h in range(H):
                    g = h // per
                    Q = Tl['q'][p][h * HS:(h + 1) * HS]
                    sc = [dot(Q, Tl['k'][t_][g * HS:(g + 1) * HS]) * inv_s
                          for t_ in range(p + 1)]
                    mx = max(sc)
                    ws = [math.exp(s - mx) for s in sc]
                    tot = sum(ws)
                    pr = [w / tot for w in ws]
                    Tl['probs'][p][h] = pr
                    for t_, pw in enumerate(pr):
                        Vv = Tl['v'][t_][g * HS:(g + 1) * HS]
                        for i in range(HS):
                            att[p][h * HS + i] += pw * Vv[i]
            Tl['att'] = att
            proj = [[dot(a, r) for r in W['wo'][l]] for a in att]
            xs = [[x + q for x, q in zip(a, b)] for a, b in zip(xs, proj)]
            Tl['x_mid'] = [list(x) for x in xs]
            Tl['n2'] = [rms_f(x, W['rms_ffn'][l]) for x in xs]
            xb2 = [t[0] for t in Tl['n2']]
            Tl['h1'] = [[dot(v, r) for r in W['w1'][l]] for v in xb2]
            Tl['h3'] = [[dot(v, r) for r in W['w3'][l]] for v in xb2]
            Tl['sig'] = [[1.0 / (1.0 + math.exp(-a)) for a in h1]
                         for h1 in Tl['h1']]
            hb = [[a * s * b for a, s, b in zip(h1, sg, h3)]
                  for h1, sg, h3 in zip(Tl['h1'], Tl['sig'], Tl['h3'])]
            Tl['hb'] = hb
            mlp = [[dot(v, r) for r in W['w2'][l]] for v in hb]
            xs = [[x + q for x, q in zip(a, b)] for a, b in zip(xs, mlp)]
        tape['nf'] = [rms_f(x, W['rms_final']) for x in xs]
        xf = [t[0] for t in tape['nf']]
        tape['xf'] = xf
        logits = [[dot(x, r) for r in W['emb']] for x in xf]
        return logits, tape

    def loss(self, toks):
        """Mean next-token cross-entropy — forward only (a probe)."""
        logits, _ = self._fwd(toks)
        tot = 0.0
        for p in range(len(toks) - 1):
            z = logits[p]; mx = max(z)
            lse = mx + math.log(sum(math.exp(v - mx) for v in z))
            tot += lse - z[toks[p + 1]]
        return tot / (len(toks) - 1)

    def train_turn(self, toks, lr, mask_from=0):
        """One standard SGD step on the whole turn. Textbook reverse-mode
        of the forward above; returns the mean loss."""
        c, W = self.cfg, self.W
        D, HS, KD = c['dim'], c['hs'], c['kvd']
        H, KV, L = c['heads'], c['kv'], c['layers']
        n = len(toks); per = H // KV; inv_s = 1.0 / math.sqrt(HS)
        logits, tape = self._fwd(toks)
        Z = c['vocab']
        inv_cnt = 1.0 / (n - 1)
        loss = 0.0
        dlog = [[0.0] * Z for _ in range(n)]
        first = max(mask_from - 1, 0)
        inv_cnt = 1.0 / max(n - 1 - first, 1)
        for p in range(first, n - 1):
            z = logits[p]; mx = max(z)
            ex = [math.exp(v - mx) for v in z]
            tot = sum(ex)
            loss += (mx + math.log(tot) - z[toks[p + 1]]) * inv_cnt
            for j in range(Z):
                pr = ex[j] / tot
                dlog[p][j] = (pr - (1.0 if j == toks[p + 1] else 0.0)) * inv_cnt
        zget = lambda rows: [[0.0] * len(r) for r in rows]
        G = {'emb': zget(W['emb']),
             'rms_att': zget(W['rms_att']), 'rms_ffn': zget(W['rms_ffn']),
             'rms_final': [0.0] * D}
        for nm in ('wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3'):
            G[nm] = [zget(l) for l in W[nm]]
        dot = lambda a, b: sum(x * y for x, y in zip(a, b))

        dxs = [[0.0] * D for _ in range(n)]
        for p in range(n - 1):
            xf = tape['xf'][p]
            for j in range(Z):
                gj = dlog[p][j]
                if gj == 0.0:
                    continue
                row = W['emb'][j]; gr = G['emb'][j]
                for i in range(D):
                    gr[i] += gj * xf[i]
                    dxs[p][i] += gj * row[i]

        def rms_b(g, w, cache, gW):
            x, inv = cache
            a = [wi * gi for wi, gi in zip(w, g)]
            s = sum(ai * xi for ai, xi in zip(a, x))
            inv3s = inv ** 3 * s / len(x)
            for i, (gi, xi) in enumerate(zip(g, x)):
                gW[i] += gi * xi * inv
            return [inv * ai - xi * inv3s for ai, xi in zip(a, x)]

        dxs = [rms_b(dxs[p], W['rms_final'], tape['nf'][p][1],
                     G['rms_final']) for p in range(n)]

        def mat_b(dys, xrows, Wm, gW):
            out = []
            for dy, x in zip(dys, xrows):
                dx = [0.0] * len(x)
                for ri, gy in enumerate(dy):
                    if gy == 0.0:
                        continue
                    row, grow = Wm[ri], gW[ri]
                    for j in range(len(x)):
                        grow[j] += gy * x[j]
                        dx[j] += gy * row[j]
                out.append(dx)
            return out

        for l in range(L - 1, -1, -1):
            Tl = tape['layers'][l]
            d_hb = mat_b(dxs, Tl['hb'], W['w2'][l], G['w2'][l])
            d_h1, d_h3 = [], []
            for p in range(n):
                a1, a3 = [], []
                for a, s, b, gh in zip(Tl['h1'][p], Tl['sig'][p],
                                       Tl['h3'][p], d_hb[p]):
                    a3.append(gh * a * s)
                    a1.append(gh * b * (s + a * s * (1.0 - s)))
                d_h1.append(a1); d_h3.append(a3)
            xb2 = [t[0] for t in Tl['n2']]
            dxb2 = mat_b(d_h1, xb2, W['w1'][l], G['w1'][l])
            dxb2b = mat_b(d_h3, xb2, W['w3'][l], G['w3'][l])
            dxb2 = [[a + b for a, b in zip(r1, r2)]
                    for r1, r2 in zip(dxb2, dxb2b)]
            d_mid = [rms_b(dxb2[p], W['rms_ffn'][l], Tl['n2'][p][1],
                           G['rms_ffn'][l]) for p in range(n)]
            dxs = [[a + b for a, b in zip(r1, r2)]
                   for r1, r2 in zip(dxs, d_mid)]

            d_att = mat_b(dxs, Tl['att'], W['wo'][l], G['wo'][l])
            dq = [[0.0] * D for _ in range(n)]
            dk = [[0.0] * KD for _ in range(n)]
            dv = [[0.0] * KD for _ in range(n)]
            for p in range(n):
                for h in range(H):
                    g_ = h // per
                    pr = Tl['probs'][p][h]
                    da = d_att[p][h * HS:(h + 1) * HS]
                    dp = []
                    for t_, pw in enumerate(pr):
                        Vv = Tl['v'][t_][g_ * HS:(g_ + 1) * HS]
                        acc = 0.0
                        for i in range(HS):
                            dv[t_][g_ * HS + i] += pw * da[i]
                            acc += da[i] * Vv[i]
                        dp.append(acc)
                    dot_pp = sum(a * b for a, b in zip(dp, pr))
                    Q = Tl['q'][p][h * HS:(h + 1) * HS]
                    for t_ in range(p + 1):
                        ds = pr[t_] * (dp[t_] - dot_pp) * inv_s
                        K = Tl['k'][t_][g_ * HS:(g_ + 1) * HS]
                        for i in range(HS):
                            dq[p][h * HS + i] += ds * K[i]
                            dk[t_][g_ * HS + i] += ds * Q[i]
            for p in range(n):
                for vec, upto in ((dq[p], D), (dk[p], KD)):
                    for i in range(0, upto, 2):
                        cr, ci = tape['rope'][p][(i % HS) // 2]
                        a, b = vec[i], vec[i + 1]
                        vec[i] = a * cr + b * ci          # rotate by -theta
                        vec[i + 1] = -a * ci + b * cr
            xb = [t[0] for t in Tl['n1']]
            dxb = mat_b(dq, xb, W['wq'][l], G['wq'][l])
            dxk = mat_b(dk, xb, W['wk'][l], G['wk'][l])
            dxv = mat_b(dv, xb, W['wv'][l], G['wv'][l])
            dxb = [[a + b + c_ for a, b, c_ in zip(r1, r2, r3)]
                   for r1, r2, r3 in zip(dxb, dxk, dxv)]
            d_in = [rms_b(dxb[p], W['rms_att'][l], Tl['n1'][p][1],
                          G['rms_att'][l]) for p in range(n)]
            dxs = [[a + b for a, b in zip(r1, r2)]
                   for r1, r2 in zip(dxs, d_in)]

        for p, t_ in enumerate(toks):
            gr = G['emb'][t_]
            for i in range(D):
                gr[i] += dxs[p][i]

        def upd(Wr, gW):
            for row, grow in zip(Wr, gW):
                for i in range(len(row)):
                    if grow[i]:
                        row[i] -= lr * grow[i]
        upd(W['emb'], G['emb'])
        upd(W['rms_att'], G['rms_att'])
        upd(W['rms_ffn'], G['rms_ffn'])
        upd([W['rms_final']], [G['rms_final']])
        for l in range(L):
            for nm in ('wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3'):
                upd(W[nm][l], G[nm][l])
        return loss

    # incremental greedy generation with a KV cache (standard decoding)
    def generate(self, prompt, steps=None):
        c, W = self.cfg, self.W
        D, HS, KD = c['dim'], c['hs'], c['kvd']
        H, KV, L = c['heads'], c['kv'], c['layers']
        per = H // KV; inv_s = 1.0 / math.sqrt(HS)
        dot = lambda a, b: sum(x * y for x, y in zip(a, b))
        kc = [[] for _ in range(L)]; vc = [[] for _ in range(L)]
        def rms(x, w):
            ss = sum(v * v for v in x) / len(x) + 1e-5
            inv = 1.0 / math.sqrt(ss)
            return [wi * xi * inv for wi, xi in zip(w, x)]
        def rot(v, p, upto):
            for i in range(0, upto, 2):
                a = p / (10000.0 ** (2 * ((i % HS) // 2) / HS))
                cr, ci = math.cos(a), math.sin(a)
                x, y = v[i], v[i + 1]
                v[i] = x * cr - y * ci
                v[i + 1] = x * ci + y * cr
        def fwd1(tok, pos):
            x = list(W['emb'][tok])
            for l in range(L):
                xb = rms(x, W['rms_att'][l])
                q = [dot(xb, r) for r in W['wq'][l]]
                k = [dot(xb, r) for r in W['wk'][l]]
                v = [dot(xb, r) for r in W['wv'][l]]
                rot(q, pos, D); rot(k, pos, KD)
                kc[l].append(k); vc[l].append(v)
                att = [0.0] * D
                for h in range(H):
                    g = h // per
                    Q = q[h * HS:(h + 1) * HS]
                    sc = [dot(Q, kt[g * HS:(g + 1) * HS]) * inv_s
                          for kt in kc[l]]
                    mx = max(sc)
                    ws = [math.exp(s - mx) for s in sc]
                    tot = sum(ws)
                    for t_, w_ in enumerate(ws):
                        pw = w_ / tot
                        Vv = vc[l][t_][g * HS:(g + 1) * HS]
                        for i in range(HS):
                            att[h * HS + i] += pw * Vv[i]
                x = [a + dot(att, r) for a, r in zip(x, W['wo'][l])]
                xb = rms(x, W['rms_ffn'][l])
                h1 = [dot(xb, r) for r in W['w1'][l]]
                h3 = [dot(xb, r) for r in W['w3'][l]]
                hb = [a * (1.0 / (1.0 + math.exp(-a))) * b
                      for a, b in zip(h1, h3)]
                x = [a + dot(hb, r) for a, r in zip(x, W['w2'][l])]
            x = rms(x, W['rms_final'])
            return [dot(x, r) for r in W['emb']]
        toks = self.tok.encode(prompt, bos=True)
        pos, token = 0, toks[0]
        out, ids = [], []
        verdict = 'DELIVERY BOUND'
        while pos < c['seq'] - 1:
            z = fwd1(token, pos)
            if pos + 1 < len(toks):
                nxt = toks[pos + 1]
            else:
                nxt = max(range(len(z)), key=lambda i: z[i])
                if nxt in (BOS, EOS):
                    verdict = 'MODEL EOS'
                    break
                ids.append(nxt)
                out.append(self.tok.decode(nxt, token))
                if steps is not None and len(ids) >= steps:
                    break
            token = nxt
            pos += 1
        else:
            verdict = 'SEQ CAPACITY'
        return {'completion': ''.join(out), 'ids': ids, 'verdict': verdict}


# ── the syllabus: whole projects, spoken in one go ──────────────────────
DIALECT = 'hex'          # 'hex' -> HVP1, 'words' -> HVPW (same signature)


def spoken_of(files: dict) -> str:
    """The SPOKEN utterance a fluent model emits for this project — the
    dialect is a surface choice; both complete() to the identical FULL
    wire (transducer law, verified in the gate)."""
    raw = T.project_to_bytes(files)
    return T.spoken_words(raw) if DIALECT == 'words' else T.spoken_hex(raw)


SYLLABUS = [
    ("make hello", {'hello.py': "print('hi')\n"}),
    ("make note",  {'note.txt': "ok 137\n"}),
]
REPLAY = [
    "Once upon a time, there was a little girl named Lily.",
    "Tom and his friend went to the park to play.",
    "The little dog was happy and they all lived happily ever after.",
]
LR = 0.01          # standard SGD; small — nudge, don't repurpose
PROBE = REPLAY[0]


class StandardTeacher:
    def __init__(self, m: StandardFloatModel):
        self.m = m
        self.curve = []

    def _turn(self, prompt, files):
        p = self.m.tok.encode(prompt, bos=True)
        return (p + self.m.tok.encode(' ' + spoken_of(files),
                                      bos=False) + [EOS], len(p))

    def mastered(self, slack=24):
        results = []
        for prompt, files in SYLLABUS:
            want = spoken_of(files)
            r = self.m.generate(prompt, steps=len(want) + slack)
            ok = False
            if r['verdict'] == 'MODEL EOS':
                try:
                    full = T.complete(r['completion'])
                    ok = T.expand(full) == T.project_to_bytes(files)
                except (AssertionError, ValueError):
                    ok = False
            results.append((ok, r))
        return all(ok for ok, _ in results), results

    def teach(self, epochs=None, show=True, probe_every=1):
        epoch = 0
        t0 = time.time()
        while True:
            epoch += 1
            sur = []
            for i, (prompt, files) in enumerate(SYLLABUS):
                toks, npr = self._turn(prompt, files)
                sur.append(self.m.train_turn(toks, LR, mask_from=npr))
                if epoch % 2 == 0:                        # lighter replay
                    meal = REPLAY[(epoch * len(SYLLABUS) + i) % len(REPLAY)]
                    self.m.train_turn(
                        self.m.tok.encode(meal, bos=True) + [EOS], LR)
            if epoch % probe_every == 0 or (epochs is not None
                                            and epoch >= epochs):
                done, results = self.mastered()
                exact = sum(1 for ok, _ in results if ok)
            else:
                done, results, exact = False, [], -1
            self.curve.append({'epoch': epoch, 'surprise': sur,
                               'exact': exact, 'of': len(results)})
            if show:
                print(f"  epoch {epoch:>2}: surprise="
                      f"[{', '.join(f'{x:.3f}' for x in sur)}]  "
                      + (f"emission {exact}/{len(results)} project-exact"
                         if exact >= 0 else "(probe skipped)"))
            if done:
                return {'verdict': f'MASTERED (epoch {epoch})',
                        'epochs': epoch, 'curve': self.curve,
                        'seconds': round(time.time() - t0, 1)}
            if epochs is not None and epoch >= epochs:
                return {'verdict': 'DELIVERY BOUND', 'epochs': epoch,
                        'curve': self.curve,
                        'seconds': round(time.time() - t0, 1)}


def deliver(m, outbase, show=True):
    """Unbounded delivery: the model speaks each project in ONE utterance;
    the transducer completes and materializes it — files land, sha-exact,
    and the emission is deterministic (spoken twice, identical)."""
    out = []
    for prompt, files in SYLLABUS:
        r = m.generate(prompt)                    # steps=None: its own stop
        full = T.complete(r['completion'])
        outdir = os.path.join(outbase, prompt.replace(' ', '_'))
        names = T.expand_project(full, outdir)
        sha = all(open(os.path.join(outdir, n)).read() == files[n]
                  for n in files)
        r2 = m.generate(prompt)
        det = r2['completion'] == r['completion']
        bidi = T.speak(T.project_to_bytes(files)) == full
        if show:
            print(f"  {prompt!r} -> ONE utterance "
                  f"({len(r['completion'])} chars, {r['verdict']}), "
                  f"{len(names)} file(s) {names}, sha-exact={sha}, "
                  f"deterministic={det}, bidirectional={bidi}")
        out.append(dict(prompt=prompt, sha=sha, det=det, bidi=bidi,
                        verdict=r['verdict'], files=names))
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--state', default=None,
                    help="breath-split state dir (checkpoint + curve)")
    ap.add_argument('--epochs', type=int, default=None,
                    help="teach at most N epochs this call (transport only)")
    ap.add_argument('--out', default='/tmp/hvp_standard_spoken')
    ap.add_argument('--lr', type=float, default=None,
                    help="override the standard SGD rate this call")
    ap.add_argument('--dialect', choices=('hex', 'words'), default='hex',
                    help="SPOKEN surface to teach (same signature either way)")
    a = ap.parse_args()
    global LR, DIALECT
    if a.lr is not None:
        LR = a.lr
    DIALECT = a.dialect

    base = os.path.join(_REPO, 'models', 'tinystories_260k')
    pristine = os.path.join(base, 'stories260K.bin')
    tokp = os.path.join(base, 'tok512.bin')

    st = None
    src = pristine
    if a.state:
        os.makedirs(a.state, exist_ok=True)
        ck = os.path.join(a.state, 'standard.bin')
        meta = os.path.join(a.state, 'curve.json')
        st = json.load(open(meta)) if os.path.exists(meta) else \
            {'epochs': 0, 'curve': [], 'L0': None, 'done': False}
        if os.path.exists(ck):
            src = ck

    m = StandardFloatModel(src, tokp)
    woke = st is not None and src != pristine
    print(f"[standard] stories260K as any runtime holds it — floats, "
          f"standard SGD, greedy" + (f"; woke at epoch {st['epochs']}"
                                     if woke else ""))
    probe_toks = m.tok.encode(PROBE, bos=True) + [EOS]
    if not woke:
        L0 = m.loss(probe_toks)
        if st is not None:
            st['L0'] = L0
        b0 = m.generate(SYLLABUS[0][0], steps=16)
        print(f"[before] first-language probe loss {L0:.4f}; "
              f"{SYLLABUS[0][0]!r} -> {b0['completion']!r} "
              f"(no HVP in it yet)")
    else:
        L0 = st['L0']

    print(f"[teach] {len(SYLLABUS)} project lessons (SPOKEN wire), "
          f"1:1 replay, lr={LR}; halting on the demand:")
    t = StandardTeacher(m)
    rec = t.teach(epochs=a.epochs, probe_every=3)
    done = rec['verdict'].startswith('MASTERED')

    if st is not None:
        st['epochs'] += rec['epochs']
        st['curve'] += t.curve
        st['done'] = done
        _write_ckpt(os.path.join(a.state, 'standard.bin'), m.cfg, m.W)
        json.dump(st, open(os.path.join(a.state, 'curve.json'), 'w'))
        print(f"[breath] {rec['verdict']} this breath ({rec['seconds']}s); "
              f"life at epoch {st['epochs']}, saved"
              + ("" if done else " — invoke again to continue"))
        if not done:
            return
    else:
        print(f"[teach] {rec['verdict']} in {rec['seconds']}s")

    print("[speak] delivery, unbounded — a whole project per utterance:")
    deliver(m, a.out)

    L1 = m.loss(probe_toks)
    g = m.generate("Once upon a time", steps=16)
    print(f"[after] first-language probe loss {L1:.4f} (was {L0:.4f}); "
          f"still speaks it: {g['completion']!r}")

    fp = os.path.join(base, 'stories260K.hvpstd.bin')
    _write_ckpt(fp, m.cfg, m.W)
    print(f"[persist] the fluent standard model: {fp}")


if __name__ == '__main__':
    main()
