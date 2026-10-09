"""
Memory line + minimal machine, per the corpus:

  WRITE  reg <- RESONANCE(FBit(value), w)      storage at harmonic address w,
                                               amplitude scaled by eps_w = eta*lambda^(w-1)
                                               at stable phase omega_w (02_operations, 01_theory)
  READ   SHIFT(cell, 2*10^(w-1))               inverts eps_w exactly in integers
  REINFORCE  COMP(cell, cell)                  amplitude doubles (07_lessons)
  DECAY      SHIFT(cell, 1/2)                  amplitude halves  (07_lessons)

Machine: registers A (w=3) and B (w=5) on the memory line; ALU = the verified
gate stack (adder, subtractor, XOR, multiplier, comparator). Python sequences
instructions (the shell); every data operation is HCL (the arithmetic).
Each step verified against a Python shadow trace.
"""
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from hcl_bitwise import hcl_byte_xor, fp, _bit
    from hcl_adder import byte_adder
    from hcl_sub import byte_sub
from hcl_alu import mul8, cmp8
import hcl_engine as h

class MemoryLine:
    def __init__(self):
        self.cells = {}                       # name -> (w, FBit)
    def write(self, name, w, value):
        cell = h.HCL.RESONANCE(h.FBit.from_scalar(fp(value)), w)
        self.cells[name] = (w, cell)
        return cell
    def read(self, name):
        w, cell = self.cells[name]
        rec = h.HCL.SHIFT(cell, fp(2 * 10**(w - 1)))
        return rec.amp // h.SCALE
    def raw_amp(self, name):
        return self.cells[name][1].amp

if __name__ == "__main__":
    S = h.SCALE
    print(f"alpha^-1 before: {h.ALPHA_INV/S}")

    # ---- memory line: store / exact recovery at two harmonic addresses ----
    mem = MemoryLine()
    mem.write('A', 3, 23)
    mem.write('B', 5, 19)
    print("\nmemory line (RESONANCE write / SHIFT read):")
    for r in ('A', 'B'):
        w = mem.cells[r][0]
        print(f"  {r}@w={w}: stored_amp={mem.raw_amp(r)/S:.6e} (eps-scaled)  "
              f"recovered={mem.read(r)}")
    ok_mem = mem.read('A') == 23 and mem.read('B') == 19
    print(f"  exact recovery: {ok_mem}")

    # ---- dynamics: reinforcement and decay on a cell ----
    c0 = h.HCL.RESONANCE(h.FBit.from_scalar(fp(1)), 3)
    c_reinf = h.HCL.COMP(c0, c0)                       # reinforcement
    c_decay = h.HCL.SHIFT(c_reinf, fp(1) // 2)         # decay by 1/2
    r0 = h.HCL.SHIFT(c0,      fp(200)).amp / S
    r1 = h.HCL.SHIFT(c_reinf, fp(200)).amp / S
    r2 = h.HCL.SHIFT(c_decay, fp(200)).amp / S
    print("\ncell dynamics at w=3 (recovered values):")
    print(f"  stored 1 -> {r0:.6f} | COMP(x,x) reinforce -> {r1:.6f} | SHIFT 1/2 decay -> {r2:.6f}")
    ok_dyn = abs(r0-1) < 1e-30 and abs(r1-2) < 1e-30 and abs(r2-1) < 1e-30

    # ---- minimal machine: fetch from memory line, execute on HCL ALU, write back ----
    program = [('ADD',), ('XOR',), ('SUB',), ('MUL',), ('CMP',)]
    shadow_A, shadow_B = 23, 19
    print("\nprogram execution (regs on memory line, ALU = HCL gates):")
    ok_run = True
    for (op,) in program:
        a, b = mem.read('A'), mem.read('B')
        if op == 'ADD':
            res, carry = byte_adder(a, b); mem.write('A', 3, res)
            exp = (shadow_A + shadow_B) & 0xFF; shadow_A = exp
            line = f"A = A+B = {res}"
        elif op == 'XOR':
            res = hcl_byte_xor(a, b); mem.write('A', 3, res)
            exp = shadow_A ^ shadow_B; shadow_A = exp
            line = f"A = A^B = {res}"
        elif op == 'SUB':
            res = byte_sub(a, b); mem.write('A', 3, res)
            exp = (shadow_A - shadow_B) & 0xFF; shadow_A = exp
            line = f"A = A-B = {res}"
        elif op == 'MUL':
            word = mul8(a, b); res = word & 0xFF; mem.write('A', 3, res)
            exp_word = shadow_A * shadow_B; exp = exp_word & 0xFF; shadow_A = exp
            line = f"A = low(A*B) = {res} (word {word}, python word {exp_word})"
        elif op == 'CMP':
            eq, gt = cmp8(a, b); res = (eq, gt)
            exp = (int(shadow_A == shadow_B), int(shadow_A > shadow_B))
            line = f"cmp(A,B) -> eq={eq} gt={gt}"
        step_ok = (res == exp)
        ok_run &= step_ok
        print(f"  {op:4} {line:44} shadow={exp}  {'OK' if step_ok else 'FAIL'}")

    print(f"\nfinal registers: A={mem.read('A')} B={mem.read('B')} "
          f"(shadow A={shadow_A} B={shadow_B})")
    print(f"alpha^-1 after:  {h.ALPHA_INV/S}")
    print(f"MEMORY LINE + MACHINE CORRECT: {ok_mem and ok_dyn and ok_run}")
