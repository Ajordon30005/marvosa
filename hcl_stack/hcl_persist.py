"""
Persistence of the memory line: one state file, always overwritten whole,
never appended. The file IS the line's current state — nothing else, no history.

  - Serialization is pure integers: (name, w, phase_frac, amp) per cell.
  - Every flush rewrites the entire file via temp + os.replace: the file is
    always one complete state, atomically swapped for the next. No growth.
  - The file carries ALPHA_INV as its integrity seal, checked on load —
    the same self-verification the braid word carries (alpha ~ 137).
  - The braid log stays per-operation and discarded; the only persistent
    object is the line.
"""
import os
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from hcl_bitwise import hcl_byte_xor, fp
    from hcl_adder import byte_adder
    from hcl_sub import byte_sub
from hcl_alu import mul8, cmp8
from hcl_machine import MemoryLine
import hcl_engine as h

MAGIC = "HCL-MEMLINE 1"

class PersistentMemoryLine(MemoryLine):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def _flush(self):
        lines = [MAGIC, f"ALPHA_INV {h.ALPHA_INV}"]
        for name, (w, cell) in sorted(self.cells.items()):
            lines.append(f"CELL {name} {w} {cell.phase_frac} {cell.amp}")
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, self.path)          # atomic whole-state swap

    def write(self, name, w, value):
        cell = super().write(name, w, value)
        self._flush()
        return cell

    @classmethod
    def load(cls, path):
        ml = cls(path)
        with open(path) as f:
            raw = f.read().splitlines()
        assert raw[0] == MAGIC, "not a memory line state file"
        stored_alpha = int(raw[1].split()[1])
        assert stored_alpha == h.ALPHA_INV, "alpha seal mismatch — state corrupt"
        for line in raw[2:]:
            _, name, w, pf, amp = line.split()
            ml.cells[name] = (int(w), h.FBit(int(pf), int(amp)))
        return ml

if __name__ == "__main__":
    S = h.SCALE
    STATE = "/mnt/user-data/outputs/memline.state"
    print(f"alpha^-1 before: {h.ALPHA_INV/S}")

    # ---- run the same program, flushing the whole state each write ----
    mem = PersistentMemoryLine(STATE)
    mem.write('A', 3, 23); mem.write('B', 5, 19)
    shadow_A, shadow_B = 23, 19
    sizes = [os.path.getsize(STATE)]
    print("\nprogram with persistence (file overwritten whole each write):")
    for op in ('ADD', 'XOR', 'SUB', 'MUL'):
        a, b = mem.read('A'), mem.read('B')
        if op == 'ADD': res, _ = byte_adder(a, b); shadow_A = (shadow_A+shadow_B) & 0xFF
        if op == 'XOR': res = hcl_byte_xor(a, b);  shadow_A = shadow_A ^ shadow_B
        if op == 'SUB': res = byte_sub(a, b);      shadow_A = (shadow_A-shadow_B) & 0xFF
        if op == 'MUL': res = mul8(a, b) & 0xFF;   shadow_A = (shadow_A*shadow_B) & 0xFF
        mem.write('A', 3, res)
        sizes.append(os.path.getsize(STATE))
        print(f"  {op}: A={res} (shadow {shadow_A}) OK={res==shadow_A}  file={sizes[-1]}B")
    print(f"  file sizes across run: {sizes}  -> no growth, state only")

    # ---- wipe RAM, reload from the state file, verify exact recovery ----
    del mem
    mem2 = PersistentMemoryLine.load(STATE)
    A2, B2 = mem2.read('A'), mem2.read('B')
    print(f"\nreloaded from file after RAM wipe: A={A2} B={B2} "
          f"(expected {shadow_A},{shadow_B})  exact={A2==shadow_A and B2==shadow_B}")

    # ---- continue executing on the reloaded line ----
    res, _ = byte_adder(mem2.read('A'), mem2.read('B'))
    mem2.write('A', 3, res)
    shadow_A = (shadow_A + shadow_B) & 0xFF
    print(f"continue on reloaded line: ADD -> A={res} (shadow {shadow_A}) OK={res==shadow_A}")

    print("\nstate file contents (the whole persistent object):")
    with open(STATE) as f:
        for ln in f.read().splitlines():
            print(f"  {ln[:90]}")

    print(f"\nalpha^-1 after:  {h.ALPHA_INV/S}")
