"""
gen_codebook.py — derive the HVPW numeral set from the model's OWN tokenizer.

Rule (deterministic): vocab pieces that begin with a single space and whose
remainder is purely lowercase ascii letters, length >= 2; deduplicated on
the remainder; sorted by the tokenizer's own BPE score descending (ties by
word); the first 16 remainders are the numerals. Base-16 over the model's
most-practiced word tokens: generator index k renders as numeral[k>>4],
numeral[k&15]. Bijective, whitespace-delimited, and each rendered " word"
re-tokenizes as the single piece the model has trained on all its life.

    python3 hvp-standard/gen_codebook.py [tok512.bin] > codebook.txt
"""
import struct, sys, os

def derive(tok_path):
    raw = open(tok_path, 'rb').read()
    vocab, scores, off = [], [], 4
    n = 0
    while off < len(raw):
        sc, ln = struct.unpack('<fi', raw[off:off + 8]); off += 8
        vocab.append(raw[off:off + ln].decode('utf-8', 'replace'))
        scores.append(sc); off += ln
        n += 1
    cands, seen = [], set()
    for v, sc in zip(vocab, scores):
        if v.startswith(' '):
            w = v[1:]
            if len(w) >= 2 and w.isascii() and w.isalpha() and w.islower() \
                    and w not in seen:
                seen.add(w)
                cands.append((sc, w))
    cands.sort(key=lambda t: (-t[0], t[1]))
    return [w for _, w in cands[:16]]

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    tok = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        here, '..', 'models', 'tinystories_260k', 'tok512.bin')
    book = derive(tok)
    assert len(book) == 16 and len(set(book)) == 16, book
    print("# HVPW numerals v1 — 16 words, one per line; digit = line number.")
    print("# Derived from the model's own tokenizer; rule and regeneration:")
    print("#     python3 gen_codebook.py  (see its docstring)")
    for w in book:
        print(w)
