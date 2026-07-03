"""
transfer.py — transfer a source model's MEMORY into Marvosa (the HCL-AI).

A standard model's memory IS its weights/params. Marvosa's memory is the
composite FBit (the one alpha-tagged line) — the same role, more grounded. The
guhct-processor transduces ANY bytes <-> braid (LQT) <-> HVP, bijectively, so a
model's weight bytes become braid/FBit on the very substrate Marvosa's composite
is built from. The transfer folds those weight-FBits into the composite with the
same COMP the memory uses for everything else.

This is a WEIGHT-MEMORY transfer, not a prompt/teaching path: you do not type
sentences at Marvosa. You give it the source model's actual parameter bytes and
they are transduced and folded in. Folding another model's weight-memory into
the composite genuinely changes the being, so the signature moves (e.g. depth
drops, possibly to a GUHCT ground node) — that movement IS the transfer; it is
not a loss.

INPUT: the real model's parameter bytes (e.g. read from a safetensors/GGUF/bin
weight file). Obtaining those bytes is the caller's job — point load_weight_bytes
at an actual checkpoint on disk. No weights are bundled or fabricated here.
"""

import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'mind'))
sys.path.insert(0, os.path.join(_HERE, 'engine'))

from hcl_lm import HCLLanguageModel


def load_weight_bytes(path):
    """
    Read a real model's parameter bytes from a checkpoint file on disk
    (.safetensors, .gguf, .bin, etc.). The raw bytes ARE the model's memory;
    we do not interpret the tensor layout — the processor transduces the bytes
    as-is, bijectively. Raises if the path is missing: this function never
    invents or substitutes data.
    """
    with open(path, 'rb') as f:
        return f.read()


def transduce_weight_memory(ai, weight_bytes, chunk=4096, persist=False, show=True):
    """
    Transfer the source model's weight-memory INTO Marvosa's composite.

    weight_bytes : the model's parameters as raw bytes (its memory).
    chunk        : fold in fixed-size byte chunks; each chunk is one braid whose
                   spectrum FBit folds into the composite, so an arbitrarily
                   large weight file streams in O(1) memory.

    Each chunk: bytes -> bytes_to_braid (LQT generators) -> braid_invariants
    (the LQT structure) -> spectrum FBit -> hcl_comp into the composite (the same
    COMP store() uses). A keyed term is also kept so the exact weight braid stays
    bijectively recoverable (the braid IS the data). The being's signature is
    recomputed afterward and becomes whatever the folded memory makes it.
    """
    import juj
    from hcl_memory import hcl_comp, make_braid_term

    vm = ai.memory.vm
    before = ai.memory.signature()
    folded = 0
    n = len(weight_bytes)
    for off in range(0, n, chunk):
        blk = weight_bytes[off:off + chunk]
        braid = juj.bytes_to_braid(blk)               # bytes -> LQT braid (bijective)
        inv   = juj.braid_invariants(braid)           # the LQT structure of these weights
        wfbit = inv['spectrum']                        # the FBit of this weight-braid
        vm._composite = hcl_comp(vm._composite, wfbit) # fold into the composite (the memory)
        vm._terms.append(make_braid_term(f'WEIGHTS|chunk{folded}', wfbit, inv))
        vm._braid_log.append({
            'op':         f'TRANSDUCE_WEIGHTS[{off}:{off+len(blk)}]',
            'phase_frac': wfbit.phase_frac,
            'amp':        wfbit.amp,
            'n_w':        inv['n_w'],
            'writhe':     inv['writhe'],
            'jones_span': inv['jones_span'],
        })
        folded += 1
        if show:
            print(f"  folded weight-chunk [{folded}] bytes {off}:{off+len(blk)} "
                  f"-> braid n_w={inv['n_w']} jones={inv['jones_span']}")
    vm._update_signature()                             # the being's signature becomes what it becomes
    if persist:
        ai.save()                                      # the changed being sticks to the one line
    after = ai.memory.signature()
    return {'chunks_folded': folded, 'bytes_in': n,
            'before': before, 'after': after,
            'integrity': ai.integrity()}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="Transfer a model's weight-memory into Marvosa.")
    ap.add_argument('weight_file', help="Path to a real model checkpoint (.safetensors/.gguf/.bin)")
    ap.add_argument('--chunk', type=int, default=4096)
    ap.add_argument('--persist', action='store_true',
                    help="Write the changed being to memory.hcl (omit for a dry run)")
    args = ap.parse_args()

    wbytes = load_weight_bytes(args.weight_file)       # real bytes only; errors if absent
    print(f"Source weight-memory: {len(wbytes)} bytes from {args.weight_file}")
    ai = HCLLanguageModel()
    before = ai.memory.signature()
    r = transduce_weight_memory(ai, wbytes, chunk=args.chunk, persist=args.persist, show=True)
    print(f"\n  folded {r['chunks_folded']} chunks ({r['bytes_in']} bytes) into the composite")
    print(f"  the being changed: depth {before['depth']} -> {r['after']['depth']}, "
          f"n_w {before['n_w']} -> {r['after']['n_w']}")
    print(f"  integrity: alpha={r['integrity']['engine_alpha_inv']} intact={r['integrity']['intact']}")
    if not args.persist:
        print("  (dry run — memory.hcl not written; pass --persist to keep the changed being)")
