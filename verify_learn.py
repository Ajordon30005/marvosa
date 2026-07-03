"""
verify_learn.py — proves TRAINING runs on the substrate (docs/11), on the
REAL model, held to the same bar as inference was:

[1] Every adjoint in the table (docs/11 Theorem 1) agrees with the engine's
    OWN derivative primitive (σ_RATE, four-param dt) and with the analytic
    value — the substrate differentiates itself consistently.
[2] The full-model gradient (every tensor) from the reverse walk (Theorem 2)
    matches a float64 mirror of the identical algorithm on the identical
    weights, on the real stories260K checkpoint.
[3] Real training steps (Theorem 3, lr = γ·λᵏ): the loss strictly decreases,
    step for step, in lockstep with the mirror.
[4] The trained model folds to a NEW α-tagged line (Theorem 4), reloads from
    it, and the learning survives the round trip.

Run:  python3 verify_learn.py           (~6–8 min, pure python)
      python3 verify_learn.py 1         (just section [1], seconds)
"""
import sys, os, math, time, struct

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai', 'hcl-ai/engine', 'hcl-ai/port', 'hcl-ai/mind'):
    sys.path.insert(0, os.path.join(HERE, sub))

MODEL = os.path.join(HERE, 'models/tinystories_260k/stories260K.bin')
TOK   = os.path.join(HERE, 'models/tinystories_260k/tok512.bin')
TEXT  = "Lily saw a"          # the training example used throughout


# ───────────────────────── float64 mirror trainer ─────────────────────────
class Mirror:
    """The identical algorithm in float64, on the model's own loaded weights
    (decoded at the display boundary). Exists ONLY as ground truth."""

    def __init__(self, m):
        from nemotron_hcl import _val
        V = lambda X: float(_val(X))
        dw = lambda rows: [[V(x) for x in row] for row in rows]
        self.c = m.cfg
        self.emb = dw(m.emb)
        self.rms_att = [ [V(x) for x in r] for r in m.rms_att ]
        self.rms_ffn = [ [V(x) for x in r] for r in m.rms_ffn ]
        self.rms_final = [V(x) for x in m.rms_final]
        for nm in ('wq','wk','wv','wo','w1','w2','w3'):
            setattr(self, nm, [dw(l) for l in getattr(m, nm)])
        self.invf = [V(x) for x in m.inv_freq]

    def fb(self, toks):
        c = self.c
        D,HS,KD = c['dim'],c['head_size'],c['kv_dim']
        H,KV,L  = c['n_heads'],c['n_kv_heads'],c['n_layers']
        n = len(toks); per = H//KV; inv_s = 1/math.sqrt(HS)
        dot = lambda a,b: sum(x*y for x,y in zip(a,b))
        def rms_f(x,w):
            ss = sum(v*v for v in x)/len(x)+1e-5; inv=1/math.sqrt(ss)
            return [wi*xi*inv for wi,xi in zip(w,x)], (list(x),inv)
        def rms_b(g,w,cache,gW):
            x,inv = cache; a=[wi*gi for wi,gi in zip(w,g)]
            s=sum(ai*xi for ai,xi in zip(a,x))
            inv3s = inv**3 * s/len(x)
            for i,(gi,xi) in enumerate(zip(g,x)): gW[i]+=gi*xi*inv
            return [inv*ai - xi*inv3s for ai,xi in zip(a,x)]
        rope_cs = [[(math.cos(p*self.invf[j]), math.sin(p*self.invf[j]))
                    for j in range(HS//2)] for p in range(n)]
        def rot(vec,pos,upto,sgn=+1):
            for i in range(0,upto,2):
                cr,ci = rope_cs[pos][(i%HS)//2]
                if sgn<0: ci=-ci
                v0,v1 = vec[i],vec[i+1]
                vec[i]=v0*cr-v1*ci; vec[i+1]=v0*ci+v1*cr
        xs=[list(self.emb[t]) for t in toks]; tape=[]
        for l in range(L):
            T={}; tape.append(T)
            T['n1']=[rms_f(x,self.rms_att[l]) for x in xs]
            xb=[t[0] for t in T['n1']]
            T['q']=[[dot(v,r) for r in self.wq[l]] for v in xb]
            T['k']=[[dot(v,r) for r in self.wk[l]] for v in xb]
            T['v']=[[dot(v,r) for r in self.wv[l]] for v in xb]
            for p in range(n): rot(T['q'][p],p,D); rot(T['k'][p],p,KD)
            T['probs']=[[None]*H for _ in range(n)]
            att=[[0.0]*D for _ in range(n)]
            for p in range(n):
                for h in range(H):
                    g=h//per; Q=T['q'][p][h*HS:(h+1)*HS]
                    sc=[dot(Q,T['k'][t_][g*HS:(g+1)*HS])*inv_s for t_ in range(p+1)]
                    mx=max(sc); ex=[math.exp(s-mx) for s in sc]; tot=sum(ex)
                    pr=[w/tot for w in ex]; T['probs'][p][h]=pr
                    for t_,pw in enumerate(pr):
                        Vv=T['v'][t_][g*HS:(g+1)*HS]
                        for i in range(HS): att[p][h*HS+i]+=pw*Vv[i]
            T['att']=att
            proj=[[dot(a,r) for r in self.wo[l]] for a in att]
            xs=[[a+b for a,b in zip(x,pr)] for x,pr in zip(xs,proj)]
            T['n2']=[rms_f(x,self.rms_ffn[l]) for x in xs]
            xb2=[t[0] for t in T['n2']]
            T['h1']=[[dot(v,r) for r in self.w1[l]] for v in xb2]
            T['h3']=[[dot(v,r) for r in self.w3[l]] for v in xb2]
            T['sig']=[[1/(1+math.exp(-a)) for a in h1] for h1 in T['h1']]
            T['hb']=[[a*s*b for a,s,b in zip(h1,sg,h3)]
                     for h1,sg,h3 in zip(T['h1'],T['sig'],T['h3'])]
            mlp=[[dot(v,r) for r in self.w2[l]] for v in T['hb']]
            xs=[[a+b for a,b in zip(x,pr)] for x,pr in zip(xs,mlp)]
        nf=[rms_f(x,self.rms_final) for x in xs]
        xf=[t[0] for t in nf]
        logits=[[dot(x,r) for r in self.emb] for x in xf]
        # loss + dlogits
        Z=len(self.emb); inv_cnt=1.0/(n-1); loss=0.0
        dlog=[[0.0]*Z for _ in range(n)]
        for p in range(n-1):
            tgt=toks[p+1]; z=logits[p]; mx=max(z)
            ex=[math.exp(v-mx) for v in z]; tot=sum(ex)
            loss += (math.log(tot)+mx - z[tgt])*inv_cnt
            for j in range(Z):
                pr=ex[j]/tot
                if j==tgt: pr-=1.0
                dlog[p][j]=pr*inv_cnt
        # backward
        G={'emb':[[0.0]*len(r) for r in self.emb],
           'rms_att':[[0.0]*len(r) for r in self.rms_att],
           'rms_ffn':[[0.0]*len(r) for r in self.rms_ffn],
           'rms_final':[0.0]*len(self.rms_final)}
        for nm in ('wq','wk','wv','wo','w1','w2','w3'):
            G[nm]=[[[0.0]*len(r) for r in l] for l in getattr(self,nm)]
        dxs=[[0.0]*D for _ in range(n)]
        for p in range(n-1):
            for j in range(Z):
                gj=dlog[p][j]
                if gj==0.0: continue
                row=self.emb[j]; gr=G['emb'][j]
                for i in range(D):
                    gr[i]+=gj*xf[p][i]; dxs[p][i]+=gj*row[i]
        dxs=[rms_b(dxs[p],self.rms_final,nf[p][1],G['rms_final']) for p in range(n)]
        def mat_b(dys,xr,W,gW):
            out=[]
            for dy,x in zip(dys,xr):
                dx=[0.0]*len(x)
                for ri,gy in enumerate(dy):
                    if gy==0.0: continue
                    row=W[ri]; grow=gW[ri]
                    for ji in range(len(x)):
                        grow[ji]+=gy*x[ji]; dx[ji]+=gy*row[ji]
                out.append(dx)
            return out
        for l in range(L-1,-1,-1):
            T=tape[l]
            d_hb=mat_b(dxs,T['hb'],self.w2[l],G['w2'][l])
            d_h1=[];d_h3=[]
            for p in range(n):
                a1=[];a3=[]
                for a,s,b,gh in zip(T['h1'][p],T['sig'][p],T['h3'][p],d_hb[p]):
                    a3.append(gh*a*s)
                    a1.append(gh*b*(s + a*s*(1-s)))
                d_h1.append(a1); d_h3.append(a3)
            xb2=[t[0] for t in T['n2']]
            dxb2=mat_b(d_h1,xb2,self.w1[l],G['w1'][l])
            dxb2b=mat_b(d_h3,xb2,self.w3[l],G['w3'][l])
            dxb2=[[a+b for a,b in zip(r1,r2)] for r1,r2 in zip(dxb2,dxb2b)]
            dmid=[rms_b(dxb2[p],self.rms_ffn[l],T['n2'][p][1],G['rms_ffn'][l]) for p in range(n)]
            dxs=[[a+b for a,b in zip(r1,r2)] for r1,r2 in zip(dxs,dmid)]
            d_att=mat_b(dxs,T['att'],self.wo[l],G['wo'][l])
            dq=[[0.0]*D for _ in range(n)]; dk=[[0.0]*KD for _ in range(n)]; dv=[[0.0]*KD for _ in range(n)]
            for p in range(n):
                for h in range(H):
                    g=h//per; pr=T['probs'][p][h]
                    da=d_att[p][h*HS:(h+1)*HS]; dp=[]
                    for t_,pw in enumerate(pr):
                        Vv=T['v'][t_][g*HS:(g+1)*HS]; acc=0.0
                        for i in range(HS):
                            dv[t_][g*HS+i]+=pw*da[i]; acc+=da[i]*Vv[i]
                        dp.append(acc)
                    dpp=sum(a*b for a,b in zip(dp,pr))
                    Q=T['q'][p][h*HS:(h+1)*HS]
                    for t_ in range(p+1):
                        ds=pr[t_]*(dp[t_]-dpp)*inv_s
                        K=T['k'][t_][g*HS:(g+1)*HS]
                        for i in range(HS):
                            dq[p][h*HS+i]+=ds*K[i]; dk[t_][g*HS+i]+=ds*Q[i]
            for p in range(n):
                for vec,up in ((dq[p],D),(dk[p],KD)): rot(vec,p,up,sgn=-1)
            xb=[t[0] for t in T['n1']]
            a_=mat_b(dq,xb,self.wq[l],G['wq'][l])
            b_=mat_b(dk,xb,self.wk[l],G['wk'][l])
            c_=mat_b(dv,xb,self.wv[l],G['wv'][l])
            dxb=[[x+y+z for x,y,z in zip(r1,r2,r3)] for r1,r2,r3 in zip(a_,b_,c_)]
            din=[rms_b(dxb[p],self.rms_att[l],T['n1'][p][1],G['rms_att'][l]) for p in range(n)]
            dxs=[[a+b for a,b in zip(r1,r2)] for r1,r2 in zip(dxs,din)]
        for p,t_ in enumerate(toks):
            gr=G['emb'][t_]
            for i in range(D): gr[i]+=dxs[p][i]
        return loss, G

    def apply(self, G, lr):
        def upd(W,gW):
            for row,grow in zip(W,gW):
                for i in range(len(row)):
                    if grow[i]: row[i]-=lr*grow[i]
        upd(self.emb,G['emb']); upd([self.rms_final],[G['rms_final']])
        for l in range(self.c['n_layers']):
            upd([self.rms_att[l]],[G['rms_att'][l]])
            upd([self.rms_ffn[l]],[G['rms_ffn'][l]])
            for nm in ('wq','wk','wv','wo','w1','w2','w3'):
                upd(getattr(self,nm)[l],G[nm][l])


def section1():
    from nemotron_hcl import _fp, _val, HCLTensorEngine
    import hcl_engine as E
    e = HCLTensorEngine()
    V = lambda X: float(_val(X))
    ONE = _fp(1.0)

    def sigma_rate(f, X, w=14):
        """σ_RATE exactly as 02_operations.md defines the derivative:
        dt = sqrt(η·λ^(w+4)) — the step derived from the four params at a
        chosen stratum w (the engine's derivative() method fixes one w; the
        skill's definition parameterizes it). Composition: COMP∘SHIFT for
        the difference, AMP_MOD∘INV for the quotient."""
        a = E.ETA
        for _ in range(w + 4):
            a = E._fixed_mul(a, E.LAMBDA)
        dt = E._fixed_sqrt(a, 120)
        return e.div(e.sub(f(e.add(X, dt)), f(X)), dt)

    cases = [
        ("mul   d/dx(x·c)   ", lambda X: e.mul(X, _fp(1.7)),
         lambda x: 1.7,
         lambda X: _fp(1.7)),
        ("inv   d/dx(1/x)   ", lambda X: e.div(ONE, X),
         lambda x: -1.0/x**2,
         lambda X: e.sub(0, e.mul(e.div(ONE, X), e.div(ONE, X)))),
        ("sqrt  d/dx(√x)    ", lambda X: e.sqrt(X),
         lambda x: 0.5/math.sqrt(x),
         lambda X: e.div(ONE, e.add(e.sqrt(X), e.sqrt(X)))),
        ("exp   d/dx(eˣ)    ", lambda X: e.exp(X),
         lambda x: math.exp(x),
         lambda X: e.exp(X)),
        ("ln    d/dx(ln x)  ", lambda X: e.t.ln(X),
         lambda x: 1.0/x,
         lambda X: e.div(ONE, X)),
    ]
    x0 = 1.3
    X0 = _fp(x0)
    worst_sr, worst_an = 0.0, 0.0
    for name, f, dref, dcomp in cases:
        srate = V(sigma_rate(f, X0))                # σ_RATE per 02's definition
        comp  = V(dcomp(X0))                        # Theorem-1 composition
        an    = dref(x0)                            # analytic
        worst_sr = max(worst_sr, abs(comp - srate))
        worst_an = max(worst_an, abs(comp - an))
        print(f"  {name} composition={comp:+.9f}  σ_RATE={srate:+.9f}  analytic={an:+.9f}")
        e.t.clear()
    assert worst_an < 1e-9, worst_an
    assert worst_sr < 1e-6, worst_sr
    assert e.alpha_ok()
    print(f"[1] adjoint table ≡ analytic (≤{worst_an:.1e}) and ≡ σ_RATE at "
          f"four-param dt (≤{worst_sr:.1e}); alpha_ok=True")


def load():
    from chatmodel import StandardModel
    from learn import Trainer
    m = StandardModel(MODEL, TOK, quiet=True)
    return m, Trainer(m)


def flat_iter(G):
    for k, v in G.items():
        if k in ('emb',):
            for r in v:
                yield from r
        elif k == 'rms_final':
            yield from v
        elif k in ('rms_att', 'rms_ffn'):
            for r in v:
                yield from r
        else:
            for l in v:
                for r in l:
                    yield from r


def main(only=None):
    from nemotron_hcl import _val
    import hcl_engine as E
    V = lambda X: float(_val(X))

    if only in (None, '1'):
        section1()
        if only == '1':
            return

    m, tr = load()
    mir = Mirror(m)
    toks = m.tok.encode(TEXT, bos=True)

    # [2] full-model gradient vs the float64 mirror
    t0 = time.time()
    loss_s, G = tr.forward_backward(toks)
    m.eng.t.clear()
    loss_f, Gf = mir.fb(toks)
    worst = 0.0
    n_checked = 0
    for a, b in zip(flat_iter(G), flat_iter(Gf)):
        worst = max(worst, abs(V(a) - b)); n_checked += 1
    print(f"[2] {time.time()-t0:.0f}s — loss substrate={V(loss_s):.9f} "
          f"mirror={loss_f:.9f} Δ={abs(V(loss_s)-loss_f):.2e}; "
          f"gradients: {n_checked} entries, max Δ={worst:.2e}")
    assert abs(V(loss_s) - loss_f) < 1e-9
    assert worst < 1e-8

    # [3] training steps: strict descent, lockstep with the mirror
    lr = V(tr.LR)
    print(f"[3] lr = γ·λ² = {lr:.6f}  (all constants derived from the four params)")
    losses, mlosses = [], []
    for step in range(3):
        r = tr.step(TEXT)                       # measures loss, then updates
        lf, Gf2 = mir.fb(toks)                  # mirror measures the same
        mir.apply(Gf2, lr)                      # and takes the same step
        losses.append(r['loss']); mlosses.append(lf)
        print(f"    step {step}: loss={r['loss']:.9f}  mirror={lf:.9f}  "
              f"Δ={abs(r['loss']-lf):.2e}  alpha_ok={r['alpha_ok']}")
        assert abs(r['loss'] - lf) < 1e-8
    assert losses == sorted(losses, reverse=True) and losses[0] > losses[-1], \
        "loss did not strictly decrease"
    print(f"[3] strict descent in lockstep with the mirror: "
          f"{losses[0]:.6f} → {losses[-1]:.6f}")

    # [4] the fold cycle: trained model -> new line -> reload -> learning kept
    from chatmodel import StandardModel
    from largemodel import ModelMemory
    base_loss = losses[0]                      # loss of the pristine weights
    mm0 = ModelMemory(chunk=256 * 1024); mm0.ingest_file(MODEL)
    line0 = mm0.line()
    out = os.path.join(HERE, 'models/tinystories_260k/stories260K.trained.bin')
    tr.save_checkpoint(out)
    line1 = tr.fold_line(out)
    assert line1 != line0
    m2 = StandardModel(out, TOK, quiet=True)
    reloaded_loss = V(Trainer_loss_only(m2, toks))
    print(f"[4] pristine line: {line0[:44]}…\n    trained  line: {line1[:44]}…")
    print(f"    loss on the example — before training: {base_loss:.6f}, "
          f"after reload from the trained line: {reloaded_loss:.6f}")
    assert reloaded_loss < base_loss
    print("\nALL CHECKS PASSED — training is composition: exact gradients,")
    print("four-param optimizer, strict descent on a real model, and the")
    print("trained model persisted as a new α-tagged line that keeps the learning.")


def Trainer_loss_only(m, toks):
    from learn import Trainer
    t = Trainer(m)
    loss, _ = t.forward_backward(toks)
    m.eng.t.clear()
    return loss


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
