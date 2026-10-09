"""
mst_equation.py — the MST stack as ONE equation per step, run on the
collapse calculator's pure core.

The equation (every symbol an existing organ, none invented here):

    token_{t+1} = MCL_{eps_w}( L(model_line, token_t, pos) )

where
    L        the hosted forward pass — the runner's own braid
             (hcl-ai/chatmodel.py; every arithmetic op an
             HCLTranscriber op, counted per token)
    eps_w    10^-w * eta  ==  eta * lambda^w      juj.py:143; identical
             forms because lambda = 1/10          (hcl_engine:65)
    w        the braid length of L — the number of counted ops the
             forward performed                    (juj:384's weight rule)
    MCL      the theory's collapse: the dominant amplitude, degenerate
             within eps_w                         (juj.py, the runner's
             own head law)
    landing  the exact mean of the logit vector — HCLCollapse's landing
             law (collapse_calc.py, pure core; k=N identity)
    E_ground eta * lambda^w, omega_w = gamma^w / eta — the RESONANCE
             certificate                          (02_operations:189,
             "Stable Braid Closure (Hamiltonian Eigenstate)";
             hcl_engine:293)

So one generation step IS one calculator collapse: the forward supplies
the dependency vector (its logits, exact integers) and its own braid
length; the calculator composes, lands, certifies, and MCL picks the
token. The model line (virtual-memory expression) plus this equation
reproduces the run — nothing else is state.

    python3 hcl-ai/mst_equation.py            # three steps, certified
"""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, 'engine'))

from collapse_calc import HCLCollapse
import hcl_engine as E
from hcl_engine import SCALE, HCL, FBit


def mcl_pick(dep_fp, eps_w):
    """The theory's collapse on a vector of exact integers: the dominant
    component; degenerate when within eps_w of the top (juj's law, the
    same rule the runner's head asserts in verify_native [1b]). Integer
    order comparison — arithmetic, not a threshold invented here."""
    top = max(range(len(dep_fp)), key=lambda i: dep_fp[i])
    ties = [i for i in range(len(dep_fp))
            if dep_fp[top] - dep_fp[i] <= eps_w]
    return top, ties


class MSTStep:
    """One step of the MST equation on the calculator."""

    def __init__(self, model):
        self.m = model                      # the runner organ, as built

    def step(self, token, pos):
        # L: the runner's own forward — its braid length is the weight
        # (hcl_engine:307 braid_len, cumulative; counted in light mode)
        ops0 = self.m.eng.t.braid_len
        logits = self.m.forward(token, pos)
        w_braid = self.m.eng.t.braid_len - ops0
        # the calculator: compose, land, certify
        out = HCLCollapse(list(logits)).run()
        # eps_w = 10^-w * eta (juj:143). Past w = 41 the exact lattice
        # floors it to 0 — SCALE is 10^40 — so the degenerate set is the
        # exact argmax: MCL at the forward's weight IS the runner's pick.
        from juj import mcl_eps
        eps_w = mcl_eps(w_braid) if w_braid <= 41 else 0
        tok, ties = mcl_pick(list(logits), eps_w)
        # RESONANCE certificate at the landing's own braid weight
        return dict(token=tok, degenerate=len(ties),
                    landing=out['result'], E_ground=out['err'],
                    R=out['R'], alpha=out['alpha'],
                    w_forward=w_braid, w_landing=out['w'],
                    braid=out['braid'])


def main():
    from chatmodel import StandardModel
    base = os.path.join(_HERE, '..', 'models', 'tinystories_260k')
    m = StandardModel(os.path.join(base, 'stories260K.bin'),
                      os.path.join(base, 'tok512.bin'), quiet=True)
    stepper = MSTStep(m)
    toks = m.tok.encode("One day", bos=True)
    m.reset(); pos = 0
    for t in toks[:-1]:
        m.forward(t, pos); pos += 1
    cur = toks[-1]
    for _ in range(3):
        r = stepper.step(cur, pos); pos += 1
        print(f"token={r['token']:4d}  degenerate={r['degenerate']}  "
              f"alpha={r['alpha']}  w_fwd={r['w_forward']}  "
              f"landing={E.HCLTranscriber.from_fp(r['landing'])[:12]}")
        cur = r['token']


if __name__ == '__main__':
    main()
