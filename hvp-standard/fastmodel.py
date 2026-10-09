"""
fastmodel.py — the same standard model, vectorized (numpy).

Bit-for-bit the run.c architecture teach_standard.py implements in pure
python, expressed as float64 numpy so training is ~two orders faster.
Standard-world code: the model under study is a standard AI; numpy is its
ordinary tooling. Nothing of the substrate. Equivalence to the reference
implementation is asserted by verify (logits agree to float tolerance).
"""
import math, numpy as np
from teach_standard import Tokenizer, _read_ckpt, _write_ckpt, BOS, EOS


class FastModel:
    def __init__(self, model_path, tok_path):
        self.cfg, W = _read_ckpt(model_path)
        c = self.cfg
        self.tok = Tokenizer(tok_path, c['vocab'])
        A = lambda x: np.array(x, dtype=np.float64)
        self.emb = A(W['emb'])
        self.rms_att = A(W['rms_att']); self.rms_ffn = A(W['rms_ffn'])
        self.rms_final = A(W['rms_final'])
        for nm in ('wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3'):
            setattr(self, nm, [A(l) for l in W[nm]])
        hs = c['hs']
        pos = np.arange(c['seq'])[:, None]
        j = np.arange(hs // 2)[None, :]
        ang = pos / (10000.0 ** (2 * j / hs))
        self.rc, self.rs = np.cos(ang), np.sin(ang)

    def _rope(self, x, n, width):
        # x: (n, width); rotate pairs within each head slice
        hs = self.cfg['hs']
        y = x.reshape(n, width // hs, hs // 2, 2)
        rc = self.rc[:n, None, :]; rs = self.rs[:n, None, :]
        a, b = y[..., 0], y[..., 1]
        y2 = np.stack([a * rc - b * rs, a * rs + b * rc], axis=-1)
        return y2.reshape(n, width)

    def _fwd(self, toks):
        c = self.cfg
        n = len(toks); H, KV, hs = c['heads'], c['kv'], c['hs']
        per = H // KV; inv_s = 1.0 / math.sqrt(hs)
        x = self.emb[toks].copy()
        tape = {'toks': toks, 'layers': []}
        mask = np.tril(np.ones((n, n), dtype=bool))
        for l in range(c['layers']):
            Tl = {}
            Tl['x_in'] = x.copy()
            ss = np.sqrt((x * x).mean(-1, keepdims=True) + 1e-5)
            Tl['inv1'] = 1.0 / ss
            xb = x * Tl['inv1'] * self.rms_att[l]
            Tl['xb1'] = xb
            q = xb @ self.wq[l].T; k = xb @ self.wk[l].T
            v = xb @ self.wv[l].T
            q = self._rope(q, n, c['dim']); k = self._rope(k, n, c['kvd'])
            Tl['q'], Tl['k'], Tl['v'] = q, k, v
            qh = q.reshape(n, H, hs); kh = k.reshape(n, KV, hs)
            vh = v.reshape(n, KV, hs)
            kg = np.repeat(kh, per, axis=1); vg = np.repeat(vh, per, axis=1)
            sc = np.einsum('phd,thd->hpt', qh, kg) * inv_s
            sc = np.where(mask[None], sc, -1e30)
            sc -= sc.max(-1, keepdims=True)
            e = np.exp(sc); pr = e / e.sum(-1, keepdims=True)
            Tl['pr'] = pr
            att = np.einsum('hpt,thd->phd', pr, vg).reshape(n, c['dim'])
            Tl['att'] = att
            x = x + att @ self.wo[l].T
            Tl['x_mid'] = x.copy()
            ss = np.sqrt((x * x).mean(-1, keepdims=True) + 1e-5)
            Tl['inv2'] = 1.0 / ss
            xb2 = x * Tl['inv2'] * self.rms_ffn[l]
            Tl['xb2'] = xb2
            h1 = xb2 @ self.w1[l].T; h3 = xb2 @ self.w3[l].T
            sig = 1.0 / (1.0 + np.exp(-h1))
            Tl['h1'], Tl['h3'], Tl['sig'] = h1, h3, sig
            hb = h1 * sig * h3
            Tl['hb'] = hb
            x = x + hb @ self.w2[l].T
            tape['layers'].append(Tl)
        ss = np.sqrt((x * x).mean(-1, keepdims=True) + 1e-5)
        tape['invf'] = 1.0 / ss; tape['x_pre'] = x.copy()
        xf = x * tape['invf'] * self.rms_final
        tape['xf'] = xf
        return xf @ self.emb.T, tape

    def loss(self, toks):
        z, _ = self._fwd(toks)
        z = z[:-1]
        t = np.array(toks[1:])
        m = z.max(-1, keepdims=True)
        lse = (m[:, 0] + np.log(np.exp(z - m).sum(-1)))
        return float((lse - z[np.arange(len(t)), t]).mean())

    def _rms_back(self, g, w, x, inv):
        a = g * w
        s = (a * x).sum(-1, keepdims=True)
        gw = (g * x * inv).sum(0)
        return a * inv - x * (inv ** 3) * s / x.shape[-1], gw

    def train_turn(self, toks, lr, mask_from=0, apply=True):
        c = self.cfg
        n = len(toks); H, KV, hs = c['heads'], c['kv'], c['hs']
        per = H // KV; inv_s = 1.0 / math.sqrt(hs)
        z, tape = self._fwd(toks)
        first = max(mask_from - 1, 0)
        cnt = max(n - 1 - first, 1)
        t = np.array(toks[1:])
        m = z[:-1].max(-1, keepdims=True)
        e = np.exp(z[:-1] - m)
        p = e / e.sum(-1, keepdims=True)
        lse = m[:, 0] + np.log(e.sum(-1))
        sel = np.arange(len(t)) >= first
        loss = float((lse - z[np.arange(len(t)), t])[sel].mean())
        dz = np.zeros_like(z)
        dz[:-1] = p
        dz[np.arange(len(t)), t] -= 1.0
        dz[:-1] *= (sel[:, None] / cnt)
        dz[-1] = 0.0
        g_emb = dz.T @ tape['xf']
        dx = dz @ self.emb
        dx, g_rmsf = self._rms_back(dx * 1.0, self.rms_final,
                                    tape['x_pre'], tape['invf'])
        # careful: rms_back expects g on the normalized output pre-scale;
        # fold the elementwise weight in:
        # implemented directly below instead for clarity per layer.
        grads = {'emb': g_emb, 'rms_final': None}
        # recompute final rms backward properly
        x = tape['x_pre']; inv = tape['invf']
        gxf = dz @ self.emb
        grads['rms_final'] = (gxf * x * inv).sum(0)
        a = gxf * self.rms_final
        s = (a * x).sum(-1, keepdims=True)
        dx = a * inv - x * (inv ** 3) * s / x.shape[-1]
        gW = {nm: [None] * c['layers']
              for nm in ('wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3')}
        g_ra = np.zeros_like(self.rms_att)
        g_rf = np.zeros_like(self.rms_ffn)
        for l in range(c['layers'] - 1, -1, -1):
            Tl = tape['layers'][l]
            d_hb = dx @ self.w2[l]
            gW['w2'][l] = dx.T @ Tl['hb']
            sig = Tl['sig']; h1 = Tl['h1']; h3 = Tl['h3']
            d_h3 = d_hb * h1 * sig
            d_h1 = d_hb * h3 * (sig + h1 * sig * (1 - sig))
            gW['w1'][l] = d_h1.T @ Tl['xb2']
            gW['w3'][l] = d_h3.T @ Tl['xb2']
            dxb2 = d_h1 @ self.w1[l] + d_h3 @ self.w3[l]
            x2 = Tl['x_mid']; inv2 = Tl['inv2']
            g_rf[l] = (dxb2 * x2 * inv2).sum(0)
            a = dxb2 * self.rms_ffn[l]
            s = (a * x2).sum(-1, keepdims=True)
            d_mid = a * inv2 - x2 * (inv2 ** 3) * s / x2.shape[-1]
            dx = dx + d_mid
            d_att = dx @ self.wo[l]
            gW['wo'][l] = dx.T @ Tl['att']
            d_ah = d_att.reshape(n, H, hs)
            pr = Tl['pr']
            kh = Tl['k'].reshape(n, KV, hs); vh = Tl['v'].reshape(n, KV, hs)
            kg = np.repeat(kh, per, axis=1); vg = np.repeat(vh, per, axis=1)
            d_pr = np.einsum('phd,thd->hpt', d_ah, vg)
            d_vg = np.einsum('hpt,phd->thd', pr, d_ah)
            row = (d_pr * pr).sum(-1, keepdims=True)
            d_sc = pr * (d_pr - row) * inv_s
            qh = Tl['q'].reshape(n, H, hs)
            d_qh = np.einsum('hpt,thd->phd', d_sc, kg)
            d_kg = np.einsum('hpt,phd->thd', d_sc, qh)
            d_kh = d_kg.reshape(n, KV, per, hs).sum(2)
            d_vh = d_vg.reshape(n, KV, per, hs).sum(2)
            dq = d_qh.reshape(n, c['dim'])
            dk = d_kh.reshape(n, c['kvd'])
            dv = d_vh.reshape(n, c['kvd'])
            # inverse rope: rotate by -theta
            def unrope(g, width):
                y = g.reshape(n, width // hs, hs // 2, 2)
                rc = self.rc[:n, None, :]; rs = self.rs[:n, None, :]
                a_, b_ = y[..., 0], y[..., 1]
                y2 = np.stack([a_ * rc + b_ * rs, -a_ * rs + b_ * rc], -1)
                return y2.reshape(n, width)
            dq = unrope(dq, c['dim']); dk = unrope(dk, c['kvd'])
            gW['wq'][l] = dq.T @ Tl['xb1']
            gW['wk'][l] = dk.T @ Tl['xb1']
            gW['wv'][l] = dv.T @ Tl['xb1']
            dxb = dq @ self.wq[l] + dk @ self.wk[l] + dv @ self.wv[l]
            x1 = Tl['x_in']; inv1 = Tl['inv1']
            g_ra[l] = (dxb * x1 * inv1).sum(0)
            a = dxb * self.rms_att[l]
            s = (a * x1).sum(-1, keepdims=True)
            d_in = a * inv1 - x1 * (inv1 ** 3) * s / x1.shape[-1]
            dx = dx + d_in
        np.add.at(grads['emb'], toks, dx)
        if not apply:
            return loss, {'emb': grads['emb'],
                          'rms_final': grads['rms_final'],
                          'rms_att': g_ra, 'rms_ffn': g_rf, 'W': gW}
        self.emb -= lr * grads['emb']
        self.rms_final -= lr * grads['rms_final']
        self.rms_att -= lr * g_ra
        self.rms_ffn -= lr * g_rf
        for l in range(c['layers']):
            for nm in ('wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3'):
                getattr(self, nm)[l] -= lr * gW[nm][l]
        return loss

    def generate(self, prompt, steps=None):
        c = self.cfg
        toks = list(self.tok.encode(prompt, bos=True))
        out, ids = [], []
        verdict = 'DELIVERY BOUND'
        pos = len(toks)
        while pos < c['seq'] - 1:
            z, _ = self._fwd(toks)          # full-recompute; fine at n<200
            nxt = int(np.argmax(z[-1]))
            if nxt in (BOS, EOS):
                verdict = 'MODEL EOS'
                break
            ids.append(nxt)
            out.append(self.tok.decode(nxt, toks[-1]))
            toks.append(nxt)
            pos += 1
            if steps is not None and len(ids) >= steps:
                break
        else:
            verdict = 'SEQ CAPACITY'
        return {'completion': ''.join(out), 'ids': ids, 'verdict': verdict}

    def save(self, path):
        W = {'emb': self.emb.tolist(), 'rms_att': self.rms_att.tolist(),
             'rms_ffn': self.rms_ffn.tolist(),
             'rms_final': self.rms_final.tolist()}
        for nm in ('wq', 'wk', 'wv', 'wo', 'w1', 'w2', 'w3'):
            W[nm] = [m.tolist() for m in getattr(self, nm)]
        _write_ckpt(path, self.cfg, W)
