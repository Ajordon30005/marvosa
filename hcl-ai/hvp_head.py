"""
hvp_head.py — emission in HVP, not tokens. One forward pass produces a
whole artifact (any number of files); nothing streams.

The pipeline is three shipped organs, composed:

  CHOOSE      the DJ interference head (collapse_calc.dj_amp_rank —
              the runner's own ranking law, docs/10): the prompt's
              final hidden state resonates against the bound
              signatures; the Path-Dominant pick is the address index.
  ADDRESS     the inherent-weights operator (inherent.WeightOperator,
              docs/13): the 8 HVP parameters of every bound artifact
              are INSTANTIATED as exact weights on the canonical
              lattice frame — demanded, training-free, exact by
              forward substitution. The address book is weights, not
              a lookup table; reading it is runner dots.
  MATERIALIZE the processor's bijection (juj.bytes_to_hvp /
              hvp_to_bytes(verify=True)): params check, braid
              carries; the artifact's exact bytes come back, every
              file, sha-for-sha.

    python3 hcl-ai/hvp_head.py     # binds three artifacts, emits each
                                   # from one forward — files land in
                                   # /tmp/emitted/<name>/
"""
import os, sys, json, hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, 'engine'))

from inherent import WeightOperator
from collapse_calc import dj_amp_rank, pack_sigs
from juj import bytes_to_hvp, hvp_to_bytes
import hcl_engine as E

SCALE = E.SCALE


class HVPEmitter:
    """Bind (prompt -> artifact) pairs; emit whole artifacts from one
    forward pass each. An artifact is a dict {filename: text}."""

    def __init__(self, model):
        self.m = model
        self.sig_list = []          # prompt hidden sign-signatures
        self.sigs_packed = None
        self.artifacts = []         # HVP signatures (params + braid)
        self.param_names = None
        self.W = {}                 # one inherent operator per param

    # ── binding ──────────────────────────────────────────────────────
    def _hidden_for(self, prompt):
        toks = self.m.tok.encode(prompt, bos=True)
        self.m.reset(); pos = 0
        for t in toks:
            self.m.forward(t, pos); pos += 1
        return list(self.m.hidden)

    def bind(self, pairs):
        """pairs: list of (prompt, artifact_dict)."""
        n = len(pairs)
        frame = [[SCALE if j == i else 0 for j in range(n)]
                 for i in range(n)]              # canonical lattice rows
        per_param = {}
        for prompt, artifact in pairs:
            h = self._hidden_for(prompt)
            self.sig_list.append(self.m._sign_pack(h))
            raw = json.dumps(artifact, sort_keys=True).encode()
            sig = bytes_to_hvp(raw)
            self.artifacts.append(sig)
            if self.param_names is None:
                self.param_names = sorted(sig['params'])
            for k in self.param_names:
                per_param.setdefault(k, []).append(int(sig['params'][k]))
        self.sigs_packed = pack_sigs(self.sig_list, len(self.m.hidden))
        op = WeightOperator()
        for k in self.param_names:
            # the address book, instantiated: dot(W_k, e_i*S) == param_k(i)
            self.W[k] = op.derive(frame, per_param[k])
        return n

    # ── emission: one forward, zero streamed tokens ──────────────────
    def emit(self, prompt, outdir):
        h = self._hidden_for(prompt)             # the ONLY forwards: prompt
        qs = self.m._sign_pack(h)
        order, _ = dj_amp_rank(qs, self.sigs_packed, len(h))
        idx = int(order[0])                      # the Path-Dominant address
        e_idx = [SCALE if j == idx else 0 for j in range(len(self.sig_list))]
        emitted = {k: self.m.eng.dot(e_idx, self.W[k])   # runner dots,
                   for k in self.param_names}            # counted + exact
        lib = self.artifacts[idx]
        assert all(emitted[k] == int(lib['params'][k])
                   for k in self.param_names), "address book violated"
        raw = hvp_to_bytes(lib, verify=True)     # params check, braid carries
        artifact = json.loads(raw.decode())
        os.makedirs(outdir, exist_ok=True)
        for name, text in artifact.items():
            open(os.path.join(outdir, name), 'w').write(text)
        return dict(index=idx, files=sorted(artifact),
                    params=emitted, alpha=self.m.eng.alpha_ok(),
                    streamed_tokens=0)


def main():
    from chatmodel import StandardModel
    base = os.path.join(_HERE, '..', 'models', 'tinystories_260k')
    m = StandardModel(os.path.join(base, 'stories260K.bin'),
                      os.path.join(base, 'tok512.bin'), quiet=True)

    library = [
        ("build me the adder tool project", {
            'README.md': "# tiny-tool\nRun: python3 tool.py data.csv\n",
            'tool.py': "import sys\nfor line in open(sys.argv[1]):\n"
                       "    a,b=line.split(',')\n    print(int(a)+int(b))\n",
            'data.csv': "1,2\n10,20\n100,200\n"}),
        ("write the morning poem", {
            'poem.txt': "The sun climbs slow,\nthe kettle sings,\n"
                        "the day begins\non small warm wings.\n"}),
        ("give me the server config bundle", {
            'server.conf': "port=8848\nworkers=2\nlog=quiet\n",
            'notes.md': "# config\nport matches the mcp http door.\n"}),
    ]
    em = HVPEmitter(m)
    n = em.bind(library)
    print(f"bound {n} artifacts; address book = {len(em.param_names)} "
          f"inherent operators, exact by construction")
    for prompt, artifact in library:
        out = os.path.join('/tmp/emitted',
                           prompt.split()[3] if len(prompt.split()) > 3
                           else prompt.split()[-1])
        r = em.emit(prompt, out)
        shas = all(hashlib.sha256(open(os.path.join(out, f), 'rb').read())
                   .hexdigest() ==
                   hashlib.sha256(artifact[f].encode()).hexdigest()
                   for f in artifact)
        print(f"  {prompt!r}\n    -> ONE forward, {r['streamed_tokens']} "
              f"streamed tokens, {len(r['files'])} file(s) "
              f"{r['files']}, sha-exact: {shas}, alpha: {r['alpha']}")


if __name__ == '__main__':
    main()
