"""
Gates -> datapath. Compose the verified HCL gate basis into an adder.

  full_adder(a,b,cin):
      sum  = a XOR b XOR cin
      cout = (a AND b) OR (cin AND (a XOR b))

  byte_adder: 8 full-adders chained, carry rippling LSB->MSB.

Every gate is itself a composition of HCL primitives (COMP/AMP_MOD/SHIFT),
so the whole adder is pure HCL. Bits at the boundary, arithmetic interior.
Verified against Python's + over a sample of byte pairs.
"""
import random
import hcl_engine as h
from hcl_bitwise import AND, OR, XOR, fp, _bit

def full_adder(t, a, b, cin):
    axb  = XOR(t, a, b)
    s    = XOR(t, axb, cin)              # sum bit
    c1   = AND(t, a, b)
    c2   = AND(t, cin, axb)
    cout = OR(t, c1, c2)                 # carry out
    return s, cout

def byte_adder(a, b):
    t = h.HCLTranscriber()
    abits = [(a >> i) & 1 for i in range(8)]   # LSB first
    bbits = [(b >> i) & 1 for i in range(8)]
    carry = fp(0)
    out_bits = []
    for i in range(8):
        s, carry = full_adder(t, fp(abits[i]), fp(bbits[i]), carry)
        out_bits.append(_bit(s))
    result = sum(out_bits[i] << i for i in range(8))   # boundary: bits -> int
    return result, _bit(carry)                          # (sum mod 256, carry out)

print(f"alpha^-1 before: {h.ALPHA_INV/h.SCALE}")

# full-adder truth table
print("\nfull-adder truth table (HCL) vs expected:")
fa_ok = True
t = h.HCLTranscriber()
for a in (0,1):
    for b in (0,1):
        for cin in (0,1):
            s, c = full_adder(t, fp(a), fp(b), fp(cin))
            s, c = _bit(s), _bit(c)
            tot = a + b + cin
            exp_s, exp_c = tot & 1, tot >> 1
            fa_ok &= (s == exp_s and c == exp_c)
            print(f"  a={a} b={b} cin={cin} -> sum={s} carry={c}  (expect {exp_s},{exp_c})")
print(f"  full-adder correct: {fa_ok}")

# 8-bit adder vs Python +
print("\n8-bit byte adder (HCL logic) vs Python + :")
pairs = [(0,0),(255,1),(127,128),(200,100),(15,240),(1,1),(170,85)]
pairs += [(random.randrange(256), random.randrange(256)) for _ in range(13)]
add_ok = True
for a, b in pairs:
    res, cout = byte_adder(a, b)
    exp = a + b
    exp_sum, exp_cout = exp & 0xFF, exp >> 8
    add_ok &= (res == exp_sum and cout == exp_cout)
for a, b in pairs[:7]:
    res, cout = byte_adder(a, b)
    print(f"  {a:3} + {b:3} = {res:3} carry {cout}  (python {(a+b)&0xFF:3} carry {(a+b)>>8})")
print(f"  all {len(pairs)} byte-add cases match: {add_ok}")

print(f"\nalpha^-1 after:  {h.ALPHA_INV/h.SCALE}  (integrity checksum)")
print(f"ADDER CORRECT END TO END: {fa_ok and add_ok}")

print("\n--- braid word: full_adder(1,1,1) ---")
t = h.HCLTranscriber()
full_adder(t, fp(1), fp(1), fp(1))
print(t.braid_word())
