"""
Datapath, continued: subtraction from the same adder.
  a - b = a + (~b) + 1   (two's complement)
Reuses full_adder and the NOT gate — both already pure HCL.
"""
import random
import hcl_engine as h
from hcl_bitwise import NOT, fp, _bit
from hcl_adder import full_adder

def byte_sub(a, b):
    t = h.HCLTranscriber()
    abits = [(a >> i) & 1 for i in range(8)]
    bbits = [(b >> i) & 1 for i in range(8)]
    carry = fp(1)                                  # the +1 of two's complement
    out_bits = []
    for i in range(8):
        nb = NOT(t, fp(bbits[i]))                  # invert b bit (HCL)
        s, carry = full_adder(t, fp(abits[i]), nb, carry)
        out_bits.append(_bit(s))
    return sum(out_bits[i] << i for i in range(8)) # result mod 256

print(f"alpha^-1 before: {h.ALPHA_INV/h.SCALE}")
print("\n8-bit subtract (HCL two's complement) vs Python (a-b) mod 256:")
pairs = [(5,3),(0,1),(255,255),(100,200),(128,1),(10,10),(200,57)]
pairs += [(random.randrange(256), random.randrange(256)) for _ in range(13)]
ok = True
for a, b in pairs:
    got = byte_sub(a, b); exp = (a - b) & 0xFF
    ok &= got == exp
for a, b in pairs[:7]:
    print(f"  {a:3} - {b:3} = {byte_sub(a,b):3}  (python {(a-b)&0xFF:3})")
print(f"  all {len(pairs)} subtract cases match: {ok}")
print(f"\nalpha^-1 after:  {h.ALPHA_INV/h.SCALE}")
print(f"SUBTRACTOR CORRECT: {ok}")
