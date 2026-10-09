"""
ALU completion: multiplier + comparator, composed only from the verified gates.

  mul  : 8x8 -> 16-bit array multiplier. Partial products p_ij = AND(a_j, b_i),
         rows summed by a 16-bit ripple-carry chain of the same full_adder.
  cmp  : EQ = AND-fold of XNOR(a_i,b_i); GT = MSB-down scan
         gt |= a_i AND NOT(b_i) AND eq_above.

Scale-invariance (05_proofs template, Step 2): the gate composition below is
identical for every operand — only bit patterns change, never the operator.
Verified against Python *, ==, > over fixed + random cases.
"""
import io, contextlib, random
with contextlib.redirect_stdout(io.StringIO()):
    from hcl_bitwise import AND, OR, XOR, NOT, fp, _bit
    from hcl_adder import full_adder
import hcl_engine as h

def add_n(t, xbits, ybits):
    """n-bit ripple adder over HCL full_adders. LSB-first bit lists of fp values."""
    carry, out = fp(0), []
    for i in range(len(xbits)):
        s, carry = full_adder(t, xbits[i], ybits[i], carry)
        out.append(s)
    return out, carry

def mul8(a, b):
    t = h.HCLTranscriber()
    abits = [(a >> j) & 1 for j in range(8)]
    bbits = [(b >> i) & 1 for i in range(8)]
    acc = [fp(0)] * 16
    for i in range(8):
        row = [fp(0)] * i \
            + [AND(t, fp(abits[j]), fp(bbits[i])) for j in range(8)] \
            + [fp(0)] * (8 - i)
        acc, _ = add_n(t, acc, row)
    return sum(_bit(v) << k for k, v in enumerate(acc))

def cmp8(a, b):
    t = h.HCLTranscriber()
    abits = [(a >> i) & 1 for i in range(8)]
    bbits = [(b >> i) & 1 for i in range(8)]
    eq, gt = fp(1), fp(0)
    for i in range(7, -1, -1):                       # MSB down
        xb  = XOR(t, fp(abits[i]), fp(bbits[i]))
        gti = AND(t, AND(t, fp(abits[i]), NOT(t, fp(bbits[i]))), eq)
        gt  = OR(t, gt, gti)
        eq  = AND(t, eq, NOT(t, xb))
    return _bit(eq), _bit(gt)

if __name__ == "__main__":
    print(f"alpha^-1 before: {h.ALPHA_INV/h.SCALE}")

    print("\n8x8 multiplier (HCL gate array) vs Python * :")
    pairs = [(0,0),(255,255),(1,255),(6,7),(23,19),(200,3)]
    pairs += [(random.randrange(256), random.randrange(256)) for _ in range(6)]
    mok = True
    for a, b in pairs:
        got = mul8(a, b); mok &= got == a * b
    for a, b in pairs[:6]:
        print(f"  {a:3} * {b:3} = {mul8(a,b):5}  (python {a*b:5})")
    print(f"  all {len(pairs)} multiply cases match: {mok}")

    print("\ncomparator (HCL gates) vs Python ==, > :")
    cpairs = [(5,5),(5,3),(3,5),(0,0),(255,0),(0,255),(128,127),(200,201)]
    cpairs += [(random.randrange(256), random.randrange(256)) for _ in range(8)]
    cok = True
    for a, b in cpairs:
        eq, gt = cmp8(a, b)
        cok &= (eq == int(a == b)) and (gt == int(a > b))
    for a, b in cpairs[:8]:
        eq, gt = cmp8(a, b)
        print(f"  cmp({a:3},{b:3}) -> eq={eq} gt={gt}  (python {int(a==b)},{int(a>b)})")
    print(f"  all {len(cpairs)} compare cases match: {cok}")

    print(f"\nalpha^-1 after:  {h.ALPHA_INV/h.SCALE}")
    print(f"ALU (mul, cmp) CORRECT: {mok and cok}")
