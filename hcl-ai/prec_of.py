"""
prec_of.py — the lattice a checkpoint itself requires.

Every f32 weight is a dyadic rational m * 2^(e-24). Exact decimal
representation on the lattice 10^PREC requires 2^fb | 10^PREC where
fb = max(0, 24 - e) is the value's fractional bit depth — 10^PREC
supplies exactly 2^PREC. So the smallest lattice on which EVERY
stored weight is exact is PREC = max fb over the checkpoint, floored
at the seal's own minimum (PREC 5, the smallest lattice that
certifies the Alpha Identity — docs/10).

    python3 hcl-ai/prec_of.py models/tinystories_260k/stories260K.bin
prints one integer. The doors use it as the default dial;
MARVOSA_PREC in the environment overrides it (the dial stays
variable — docs/10).
"""
import struct, sys, math

SEAL_FLOOR = 5


def prec_of(path):
    raw = open(path, 'rb').read()
    body = raw[28:]
    n = len(body) // 4
    vals = struct.unpack(f'<{n}f', body[:n * 4])
    fb_max = 0
    for f in vals:
        if f == 0.0 or f != f or f in (float('inf'), float('-inf')):
            continue
        m, e = math.frexp(f)
        mi = int(abs(m) * (1 << 24))
        tz = 0
        while mi and mi % 2 == 0:
            mi //= 2
            tz += 1
        fb = max(0, 24 - tz - e + 1) if False else max(0, (24 - tz) - e)
        # value = mi * 2^(e - (24 - tz)); fractional depth = max(0, (24-tz) - e)
        if fb > fb_max:
            fb_max = fb
    return max(SEAL_FLOOR, fb_max)


if __name__ == '__main__':
    print(prec_of(sys.argv[1]))
