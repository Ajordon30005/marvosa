"""
Porting musl libm kernels onto the HCL substrate.
Method: 06_porting.md — compose existing primitives, reuse the engine,
float only at the verification boundary, keep the braid word, check alpha.

  sqrt(x)     -> FISSION                                  (02_operations.md)
  hypot(x,y)  -> FISSION( COMP( AMP_MOD(x,x), AMP_MOD(y,y) ) )
  pow(x,y)    -> MOBIUS_GROWTH( AMP_MOD( LOG_EXTRACT(x), y ) )   (x^y = e^{y ln x})

Every interior value is fixed-point integer. math.* is used ONLY to verify
the HCL result at the end — never inside the computation (Rule 1).
"""
import math
import hcl_engine as h

fp, rfp = h.HCLTranscriber.to_fp, h.HCLTranscriber.from_fp


def hcl_sqrt(t, x):
    # FISSION daughter-1 amplitude is sqrt
    return t.sqrt(fp(x))

def hcl_hypot(t, x, y):
    fx, fy = fp(x), fp(y)
    x2 = t.mul(fx, fx)          # AMP_MOD
    y2 = t.mul(fy, fy)          # AMP_MOD
    s  = t.add(x2, y2)          # COMP
    return t.sqrt(s)            # FISSION

def hcl_pow(t, x, y):
    # x^y = exp(y * ln x)   (x > 0)
    lnx = t.ln(fp(x))           # LOG_EXTRACT
    ylx = t.mul(fp(y), lnx)     # AMP_MOD
    return t.exp(ylx)           # MOBIUS_GROWTH


def show(name, hcl_fp, ref, digits=18):
    got = rfp(hcl_fp)
    # compare first `digits` significant decimals
    refs = f"{ref:.40f}"
    ok = got[:digits+2].rstrip('0') == refs[:len(got[:digits+2].rstrip('0'))] \
         or abs(float(got) - ref) < 1e-15
    print(f"  {name:18} HCL={got[:digits+2]:<22} ref={refs[:digits+2]:<22} {'MATCH' if ok else 'DIFF'}")
    return ok


print(f"alpha^-1 before any work: {h.ALPHA_INV/h.SCALE}")
print()

cases_sqrt  = [2, 3, 10, 1024, 0.25]
cases_hypot = [(3,4), (5,12), (1,1), (8,15)]
cases_pow   = [(2,10), (2,0.5), (3,3), (10,3)]

all_ok = True

print("sqrt  (FISSION):")
for x in cases_sqrt:
    t = h.HCLTranscriber()
    all_ok &= show(f"sqrt({x})", hcl_sqrt(t, x), math.sqrt(x))

print("\nhypot (AMP_MOD,AMP_MOD,COMP,FISSION):")
for x, y in cases_hypot:
    t = h.HCLTranscriber()
    all_ok &= show(f"hypot({x},{y})", hcl_hypot(t, x, y), math.hypot(x, y))

print("\npow   (LOG_EXTRACT,AMP_MOD,MOBIUS_GROWTH):")
for x, y in cases_pow:
    t = h.HCLTranscriber()
    all_ok &= show(f"pow({x},{y})", hcl_pow(t, x, y), math.pow(x, y))

print(f"\nalpha^-1 after all work:  {h.ALPHA_INV/h.SCALE}  (integrity checksum)")
print(f"all kernels match reference: {all_ok}")

print("\n--- braid word for one example: hypot(3,4) ---")
t = h.HCLTranscriber()
hcl_hypot(t, 3, 4)
print(t.braid_word())
