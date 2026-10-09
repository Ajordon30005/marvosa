"""
shell.py — loader for the optional compiled shell (shell/marvosa_shell.c).

The shell computes the transcriber's dot verbatim (hcl_engine:424 —
magnitude floor per term, sign after, signed accumulation) over whole
weight matrices in one C call. Division by SCALE is the lambda law
applied 40 times (lambda_w = 10^-w, 01_theory; LAMBDA, hcl_engine:65),
run as three exact short divisions — 10^19, 10^19, 10^2. HCL only. Bit-identical is the contract
(verify_shell.py); the braid counter advances exactly as the pure loop
would (2 generators per element, hcl_engine:434); and when the library
is absent everything runs on the pure path unchanged.

    sh build_shell.sh        # one cc call; optional
"""
import ctypes, os

LIMBS = 5
_HERE = os.path.dirname(os.path.abspath(__file__))
_SO = os.path.join(_HERE, '..', '..', 'shell', 'libmarvosa_shell.so')

_lib = None
if os.path.exists(_SO):
    try:
        _lib = ctypes.CDLL(_SO)
    except OSError:
        _lib = None


def available():
    return _lib is not None


def _pack(vals):
    """Little-endian limbs via int.to_bytes — one C-speed call per value
    (LIMBS*8 = 40 bytes each), read by the shell as uint64 limbs of the
    same layout. Signs ride separately."""
    nb = LIMBS * 8
    buf = b''.join((-v if v < 0 else v).to_bytes(nb, 'little')
                   for v in vals)
    N = bytes(1 if v < 0 else 0 for v in vals)
    return (ctypes.cast(ctypes.create_string_buffer(buf, len(buf)),
                        ctypes.POINTER(ctypes.c_uint64)),
            ctypes.cast(ctypes.create_string_buffer(N, len(N)),
                        ctypes.POINTER(ctypes.c_int8)))


class PackedMatrix:
    """A weight matrix packed once for the shell. rows x n integers."""

    def __init__(self, W):
        self.rows, self.n = len(W), len(W[0])
        flat = [w for row in W for w in row]
        self.Wl, self.Wn = _pack(flat)





def matvec(packed, X, t):
    """out[r] = t.dot(X, W[r]) for every row, one C call. Advances the
    transcriber's braid counter exactly as the pure loops would."""
    Xl, Xn = _pack(X)
    out = (ctypes.c_uint64 * (packed.rows * LIMBS))()
    on = (ctypes.c_int8 * packed.rows)()
    _lib.fixed_dot_rows(packed.Wl, packed.Wn, Xl, Xn,
                        packed.rows, packed.n, out, on)
    t.braid_len += packed.rows * packed.n * 2      # hcl_engine:434
    raw = bytes(ctypes.cast(out, ctypes.POINTER(
        ctypes.c_uint8 * (packed.rows * LIMBS * 8))).contents)
    nb = LIMBS * 8
    res = []
    for r in range(packed.rows):
        m = int.from_bytes(raw[r * nb:(r + 1) * nb], 'little')
        res.append(-m if on[r] else m)
    return res


# ── layer-body ops (fx: 5×u64 magnitude limbs + sign byte) ─────────────
import ctypes as _ct

def _pack1(x, buf, off=0):
    m = abs(x)
    for i in range(5):
        buf[off + i] = m & 0xFFFFFFFFFFFFFFFF
        m >>= 64
    return 1 if x < 0 else 0

def _unpack1(buf, neg, off=0):
    v = 0
    for i in range(4, -1, -1):
        v = (v << 64) | buf[off + i]
    return -v if neg else v

class _FxOps:
    """ctypes surface over the compiled layer body. All semantics are the
    engine's own (t.mul magnitude-floor, t.div reciprocal form, module
    signed-floor inside series) — proven bit-identical in verify_shell."""
    def __init__(self, lib, SCALE):
        self.lib = lib
        prec = len(str(SCALE)) - 1
        lib.fx_set_prec(prec)
        self.S  = (_ct.c_uint64 * 5)()
        self.S2 = (_ct.c_uint64 * 10)()      # S^2 spans 2*LIMBS
        _pack1(SCALE, self.S)
        s2 = SCALE * SCALE
        for i in range(10):
            self.S2[i] = s2 & 0xFFFFFFFFFFFFFFFF; s2 >>= 64
        for nm in ('fxv_add','fxv_sub','fxv_mul','fxv_scale','fxv_axpy',
                   'fx_exp1','fx_sin1','fx_cos1','fx_sqrt1','fx_tdiv1'):
            setattr(self, nm, getattr(lib, nm))
        self._o  = (_ct.c_uint64 * 5)()
        self._on = _ct.c_int8(0)

    def _vec_in(self, xs):
        n = len(xs)
        m = (_ct.c_uint64 * (5 * n))()
        g = (_ct.c_int8 * n)()
        for i, x in enumerate(xs):
            g[i] = _pack1(x, m, 5 * i)
        return m, g, n

    def _vec_out(self, m, g, n):
        return [_unpack1(m, g[i], 5 * i) for i in range(n)]

    def vadd(self, X, Y):
        a, an, n = self._vec_in(X); b, bn, _ = self._vec_in(Y)
        o = (_ct.c_uint64 * (5 * n))(); on = (_ct.c_int8 * n)()
        self.fxv_add(a, an, b, bn, n, o, on)
        return self._vec_out(o, on, n)

    def vsub(self, X, Y):
        a, an, n = self._vec_in(X); b, bn, _ = self._vec_in(Y)
        o = (_ct.c_uint64 * (5 * n))(); on = (_ct.c_int8 * n)()
        self.fxv_sub(a, an, b, bn, n, o, on)
        return self._vec_out(o, on, n)

    def vmul(self, X, Y):
        a, an, n = self._vec_in(X); b, bn, _ = self._vec_in(Y)
        o = (_ct.c_uint64 * (5 * n))(); on = (_ct.c_int8 * n)()
        self.fxv_mul(a, an, b, bn, n, o, on)
        return self._vec_out(o, on, n)

    def vscale(self, X, K):
        a, an, n = self._vec_in(X)
        k = (_ct.c_uint64 * 5)(); kn = _pack1(K, k)
        o = (_ct.c_uint64 * (5 * n))(); on = (_ct.c_int8 * n)()
        self.fxv_scale(a, an, k, kn, n, o, on)
        return self._vec_out(o, on, n)

    def axpy(self, ACC, K, X):
        a, an, n = self._vec_in(ACC); x, xn, _ = self._vec_in(X)
        k = (_ct.c_uint64 * 5)(); kn = _pack1(K, k)
        self.fxv_axpy(a, an, k, kn, x, xn, n)
        out = self._vec_out(a, an, n)
        ACC[:] = out
        return ACC

    def exp(self, X):
        x = (_ct.c_uint64 * 5)(); xn = _pack1(X, x)
        self.fx_exp1(x, xn, self.S, self._o, _ct.byref(self._on))
        return _unpack1(self._o, self._on.value)

    def sin_rad(self, ANG):
        x = (_ct.c_uint64 * 5)(); xn = _pack1(ANG, x)
        self.fx_sin1(x, xn, self.S, self._o, _ct.byref(self._on))
        return _unpack1(self._o, self._on.value)

    def cos_rad(self, ANG):
        x = (_ct.c_uint64 * 5)(); xn = _pack1(ANG, x)
        self.fx_cos1(x, xn, self.S, self._o, _ct.byref(self._on))
        return _unpack1(self._o, self._on.value)

    def sqrt_mag(self, AMP):
        x = (_ct.c_uint64 * 5)(); _pack1(AMP, x)
        self.fx_sqrt1(x, self.S, self._o)
        return _unpack1(self._o, 0)

    def tdiv(self, X, Y):
        x = (_ct.c_uint64 * 5)(); xn = _pack1(X, x)
        y = (_ct.c_uint64 * 5)(); yn = _pack1(Y, y)
        self.fx_tdiv1(x, xn, y, yn, self.S2, self._o, _ct.byref(self._on))
        return _unpack1(self._o, self._on.value)


    def softmax(self, Z):
        a, an, n = self._vec_in(Z)
        o = (_ct.c_uint64 * (5 * n))(); on = (_ct.c_int8 * n)()
        self.lib.fx_softmax(a, an, n, self.S, self.S2, o, on)
        return self._vec_out(o, on, n)

    def silu_mul(self, H1, H3):
        a, an, n = self._vec_in(H1); b, bn, _ = self._vec_in(H3)
        o = (_ct.c_uint64 * (5 * n))(); on = (_ct.c_int8 * n)()
        self.lib.fx_silu_mul(a, an, b, bn, n, self.S, self.S2, o, on)
        return self._vec_out(o, on, n)

    def rope(self, V, upto, head_size, POSF, INVF, TWO_PI):
        v, vn, n = self._vec_in(V)
        pf = (_ct.c_uint64 * 5)(); _pack1(POSF, pf)
        iv, ivn, _ = self._vec_in(INVF)
        tp = (_ct.c_uint64 * 5)(); _pack1(TWO_PI, tp)
        self.lib.fx_rope(v, vn, upto, head_size, pf, iv, ivn, tp, self.S, self.S2)
        return self._vec_out(v, vn, n)

def fx_ops(SCALE):
    if not available():
        return None
    return _FxOps(_lib, SCALE)


# ── training kernels: the reverse walk's two hot patterns ──────────────
def dot_cols(packed, Y, t):
    """dx[j] = Σ_r ±((|Y_r|·|W[r][j]|)//S) — Wᵀ·dy with the transcriber's
    mul law, zero rows skipped exactly as the pure loop's `gy == 0:
    continue`. Braid parity: the pure loop spends 2 generators per
    (nonzero row, column) on this half — counted here identically."""
    Yl, Yn = _pack(Y)
    out = (ctypes.c_uint64 * (packed.n * LIMBS))()
    on = (ctypes.c_int8 * packed.n)()
    _lib.fixed_dot_cols(packed.Wl, packed.Wn, Yl, Yn,
                        packed.rows, packed.n, out, on)
    nz = sum(1 for v in Y if v != 0)
    t.braid_len += nz * packed.n * 2
    raw = bytes(ctypes.cast(out, ctypes.POINTER(
        ctypes.c_uint8 * (packed.n * LIMBS * 8))).contents)
    nb = LIMBS * 8
    res = []
    for j in range(packed.n):
        m = int.from_bytes(raw[j * nb:(j + 1) * nb], 'little')
        res.append(-m if on[j] else m)
    return res


class PackedAccum:
    """A gradient matrix held packed across many outer_acc calls, unpacked
    once at the end of the walk. Starts at exact zero."""

    def __init__(self, rows, n):
        self.rows, self.n = rows, n
        self.Gl = (ctypes.c_uint64 * (rows * n * LIMBS))()
        self.Gn = (ctypes.c_int8 * (rows * n))()

    def outer_acc(self, Y, X, t):
        """G[r][j] += ±((|Y_r|·|X_j|)//S); zero Y rows skipped; braid
        parity 2 generators per (nonzero row, column), as the pure loop."""
        Yl, Yn = _pack(Y)
        Xl, Xn = _pack(X)
        nz = _lib.fixed_outer_acc(self.Gl, self.Gn, Yl, Yn, Xl, Xn,
                                  self.rows, self.n)
        t.braid_len += nz * self.n * 2
        return nz

    def unpack_into(self, G):
        """Add the packed totals into a Python grad matrix G (which the
        pure walk would have accumulated element by element). G rows must
        currently hold the values accumulated by any remaining pure steps
        (normally zero for the tensors routed here)."""
        raw = bytes(ctypes.cast(self.Gl, ctypes.POINTER(
            ctypes.c_uint8 * (self.rows * self.n * LIMBS * 8))).contents)
        nb = LIMBS * 8
        k = 0
        for r in range(self.rows):
            row = G[r]
            for j in range(self.n):
                m = int.from_bytes(raw[k * nb:(k + 1) * nb], 'little')
                if m:
                    row[j] += -m if self.Gn[k] else m
                k += 1
        return G
