"""
Refuting the false limit: bitwise / Boolean logic IS arithmetic, so it ports
to HCL by composition — no new primitive, exactly per 06_porting.md.

Boolean basis over bits {0,1}, each a composition of COMP/AMP_MOD/SHIFT:
    NOT a   = 1 - a
    AND a b = a*b
    OR  a b = a + b - a*b
    XOR a b = a + b - 2*a*b

From a complete Boolean basis you can build any digital logic, hence any
bitwise routine. We then build byte-XOR and base64 encode (the file I wrongly
dismissed) on top, and check both against Python exactly.

Bits are taken at the input boundary (the wire-level form of the data), the
same way to_fp takes a number once at the boundary. Everything interior is HCL.
"""
import base64 as _b64
import random
import hcl_engine as h

fp, rfp = h.HCLTranscriber.to_fp, h.HCLTranscriber.from_fp
SCALE = h.SCALE

def _bit(v):            # fixed-point value -> 0/1 integer
    return round(v / SCALE)

# ---- Boolean gates: each is a composition of HCL primitives ----
def NOT(t, a):                       # 1 - a
    return t.sub(fp(1), a)
def AND(t, a, b):                    # a*b
    return t.mul(a, b)
def OR(t, a, b):                     # a + b - a*b
    return t.sub(t.add(a, b), t.mul(a, b))
def XOR(t, a, b):                    # a + b - 2*a*b
    ab2 = t.mul(fp(2), t.mul(a, b))
    return t.sub(t.add(a, b), ab2)

# ---- byte XOR via bitwise HCL XOR, recomposed with HCL arithmetic ----
def hcl_byte_xor(a, b):
    t = h.HCLTranscriber()
    abits = [(a >> i) & 1 for i in range(8)]   # boundary: byte -> bits
    bbits = [(b >> i) & 1 for i in range(8)]
    acc = fp(0)
    for i in range(8):
        x = XOR(t, fp(abits[i]), fp(bbits[i]))   # HCL XOR on bit i
        place = t.mul(fp(2**i), x)               # bit i contributes 2^i (AMP_MOD)
        acc = t.add(acc, place)                  # COMP accumulate
    return _bit(acc)

# ---- base64 encode: 3 bytes -> 4 sextets, value computed in HCL ----
_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

def _sextet_value_hcl(t, bits6):
    # value = sum_{k} bit_k * 2^(5-k), MSB first — pure HCL arithmetic
    acc = fp(0)
    for k in range(6):
        acc = t.add(acc, t.mul(fp(2**(5-k)), fp(bits6[k])))
    return _bit(acc)

def hcl_b64encode(data: bytes) -> str:
    out = []
    for i in range(0, len(data), 3):
        chunk = data[i:i+3]
        n = len(chunk)
        # boundary: bytes -> 24-bit MSB-first bit list (pad with 0 bits)
        bits = []
        for j in range(3):
            byte = chunk[j] if j < n else 0
            bits += [(byte >> (7-k)) & 1 for k in range(8)]
        t = h.HCLTranscriber()
        sextets = [_sextet_value_hcl(t, bits[6*s:6*s+6]) for s in range(4)]
        if n == 1:
            chars = _ALPHA[sextets[0]] + _ALPHA[sextets[1]] + "=="
        elif n == 2:
            chars = _ALPHA[sextets[0]] + _ALPHA[sextets[1]] + _ALPHA[sextets[2]] + "="
        else:
            chars = "".join(_ALPHA[sx] for sx in sextets)
        out.append(chars)
    return "".join(out)


print(f"alpha^-1 before: {h.ALPHA_INV/SCALE}")

# 1. Gate truth tables
print("\nGate truth tables (HCL composition vs expected):")
t = h.HCLTranscriber()
ok = True
for a in (0, 1):
    nb = _bit(NOT(t, fp(a)))
    ok &= nb == (1 - a)
    for b in (0, 1):
        an = _bit(AND(t, fp(a), fp(b))); orr = _bit(OR(t, fp(a), fp(b))); xr = _bit(XOR(t, fp(a), fp(b)))
        ok &= an == (a & b) and orr == (a | b) and xr == (a ^ b)
        print(f"  a={a} b={b} | AND={an} OR={orr} XOR={xr} | NOT {a}={nb}")
print(f"  all gates correct: {ok}")

# 2. byte XOR vs Python ^ (sample of pairs incl. edges)
print("\nbyte XOR (HCL) vs Python ^ :")
pairs = [(0,0),(255,255),(255,0),(170,85),(1,2),(200,57),(15,240),(123,222)]
pairs += [(random.randrange(256), random.randrange(256)) for _ in range(12)]
xok = True
for a, b in pairs:
    got = hcl_byte_xor(a, b); exp = a ^ b
    xok &= got == exp
for a, b in pairs[:6]:
    print(f"  {a:3} ^ {b:3} = {hcl_byte_xor(a,b):3}  (python {a^b:3})")
print(f"  all {len(pairs)} byte-XOR cases match: {xok}")

# 3. base64 encode vs Python
print("\nbase64 encode (HCL sextet math) vs Python base64:")
tests = [b"Man", b"M", b"Ma", b"hello world", b"Alpine", bytes(range(20))]
bok = True
for d in tests:
    got = hcl_b64encode(d); exp = _b64.b64encode(d).decode()
    bok &= got == exp
    show = d if len(d) <= 12 else d[:12]+b"..."
    print(f"  {str(show):20} HCL={got:<32} py={exp:<32} {'MATCH' if got==exp else 'DIFF'}")
print(f"  all base64 cases match: {bok}")

print(f"\nalpha^-1 after:  {h.ALPHA_INV/SCALE}  (integrity checksum)")
print(f"EVERYTHING MATCHES: {ok and xok and bok}")

print("\n--- braid word: XOR(1,0) on one bit ---")
t = h.HCLTranscriber()
XOR(t, fp(1), fp(0))
print(t.braid_word())
