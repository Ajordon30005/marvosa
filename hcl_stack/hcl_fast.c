/*
 * hcl_fast.c — the SAME engine on a compiled host.
 *
 * Every formula below is transcribed from hcl_engine.py (itself verbatim
 * from hcl-pure/references/03_engine.md): same PREC=40 decimal lattice,
 * same series, same term counts, same TINY break, same floor divisions,
 * same Newton control flow. Zero new math — only the host changes:
 * GMP compiled integers instead of interpreted Python ints.
 *
 * The proof of the port is the repo's own (06_porting steps 7-8):
 *   - the C bootstrap must produce the IDENTICAL ALPHA_INV integer
 *   - every primitive and organ must equal the Python engine exactly
 *     on the same inputs (verify_fast.py)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <gmp.h>

#define PREC 40
static mpz_t SCALE, TWO_PI, PI_INT, ETA, LAMBDA, GAMMA_, BETA_, ALPHA, ALPHA_INV;
static mpz_t HALF, QUARTER, THREEQ;          /* SCALE/2, SCALE/4, 3*SCALE/4 */
static int booted = 0;
#define TINY 10

/* ---- fixed-point primitives (floor semantics = Python //) ---- */
static void fmul(mpz_t r, const mpz_t X, const mpz_t Y){
    mpz_mul(r, X, Y); mpz_fdiv_q(r, r, SCALE);
}
static void fdivq(mpz_t r, const mpz_t X, const mpz_t Y){
    mpz_mul(r, X, SCALE); mpz_fdiv_q(r, r, Y);
}
static void fsqrt(mpz_t r, const mpz_t X, int iters){
    if (mpz_sgn(X) == 0){ mpz_set_ui(r, 0); return; }
    mpz_t target, Rg, Rg2, diff;
    mpz_inits(target, Rg, Rg2, diff, NULL);
    mpz_mul(target, X, SCALE);
    size_t bits = mpz_sizeinbase(target, 2);
    mpz_set_ui(Rg, 1); mpz_mul_2exp(Rg, Rg, (bits + 1) / 2);
    if (mpz_sgn(Rg) == 0) mpz_set_ui(Rg, 1);
    for (int i = 0; i < iters; i++){
        mpz_fdiv_q(Rg2, target, Rg);
        mpz_add(Rg2, Rg2, Rg);
        mpz_fdiv_q_ui(Rg2, Rg2, 2);
        mpz_sub(diff, Rg2, Rg);
        if (mpz_cmpabs_ui(diff, 1) <= 0) break;   /* returns pre-update Rg */
        mpz_set(Rg, Rg2);
    }
    mpz_set(r, Rg);
    mpz_clears(target, Rg2, diff, NULL); mpz_clear(Rg); /* keep order safe */
}
static void arctan_int(mpz_t res, const mpz_t X, int terms){
    mpz_t xpow, x2, term, den;
    mpz_inits(xpow, x2, term, den, NULL);
    mpz_set_ui(res, 0);
    mpz_set(xpow, X);
    fmul(x2, X, X);
    for (int k = 0; k < terms; k++){
        mpz_set_ui(den, 2*k + 1); mpz_mul(den, den, SCALE);
        fdivq(term, xpow, den);
        if (k % 2 == 0) mpz_add(res, res, term);
        else            mpz_sub(res, res, term);
        fmul(xpow, xpow, x2);
        if (mpz_cmpabs_ui(term, TINY) < 0) break;
    }
    mpz_clears(xpow, x2, term, den, NULL);
}
static void sin_fp(mpz_t res, const mpz_t X, int terms){
    mpz_t xpow, x2, fact, term, js;
    mpz_inits(xpow, x2, fact, term, js, NULL);
    mpz_set_ui(res, 0);
    mpz_set(xpow, X); fmul(x2, X, X);
    for (int k = 0; k < terms; k++){
        mpz_set(fact, SCALE);
        for (int j = 1; j < 2*k + 2; j++){
            mpz_set_ui(js, j); mpz_mul(js, js, SCALE);
            fmul(fact, fact, js);
        }
        fdivq(term, xpow, fact);
        if (k % 2 == 0) mpz_add(res, res, term);
        else            mpz_sub(res, res, term);
        fmul(xpow, xpow, x2);
        if (mpz_cmpabs_ui(term, TINY) < 0) break;
    }
    mpz_clears(xpow, x2, fact, term, js, NULL);
}
static void cos_fp(mpz_t res, const mpz_t X, int terms){
    mpz_t xpow, x2, fact, term, js;
    mpz_inits(xpow, x2, fact, term, js, NULL);
    mpz_set(res, SCALE);
    fmul(xpow, X, X); fmul(x2, X, X);
    for (int k = 1; k < terms; k++){
        mpz_set(fact, SCALE);
        for (int j = 1; j < 2*k + 1; j++){
            mpz_set_ui(js, j); mpz_mul(js, js, SCALE);
            fmul(fact, fact, js);
        }
        fdivq(term, xpow, fact);
        if (k % 2 == 0) mpz_add(res, res, term);
        else            mpz_sub(res, res, term);
        fmul(xpow, xpow, x2);
        if (mpz_cmpabs_ui(term, TINY) < 0) break;
    }
    mpz_clears(xpow, x2, fact, term, js, NULL);
}
static void exp_fp(mpz_t res, const mpz_t X, int terms){
    mpz_t term;
    mpz_init(term);
    mpz_set(res, SCALE); mpz_set(term, SCALE);
    for (int k = 1; k < terms; k++){
        fmul(term, term, X);
        mpz_fdiv_q_ui(term, term, k);
        mpz_add(res, res, term);
        if (mpz_cmpabs_ui(term, TINY) < 0) break;
    }
    mpz_clear(term);
}
static void ln_fp(mpz_t res, const mpz_t X, int terms){
    mpz_t u, u2, upow, term, num, den;
    mpz_inits(u, u2, upow, term, num, den, NULL);
    mpz_sub(num, X, SCALE); mpz_add(den, X, SCALE);
    fdivq(u, num, den);
    fmul(u2, u, u);
    mpz_set_ui(res, 0); mpz_set(upow, u);
    for (int k = 0; k < terms; k++){
        mpz_set_ui(den, 2*k + 1); mpz_mul(den, den, SCALE);
        fdivq(term, upow, den);
        mpz_add(res, res, term);
        fmul(upow, upow, u2);
        if (mpz_cmpabs_ui(term, TINY) < 0) break;
    }
    mpz_mul_ui(res, res, 2);
    mpz_clears(u, u2, upow, term, num, den, NULL);
}
static void atan2_fp(mpz_t res, const mpz_t Y, const mpz_t X){
    mpz_t at, q;
    mpz_inits(at, q, NULL);
    if (mpz_sgn(X) == 0){
        mpz_fdiv_q_ui(res, PI_INT, 2);
        if (mpz_sgn(Y) < 0) mpz_neg(res, res);
        mpz_clears(at, q, NULL); return;
    }
    if (mpz_cmpabs(Y, X) <= 0){
        fdivq(q, Y, X); arctan_int(at, q, 80);
        if (mpz_sgn(X) < 0){
            if (mpz_sgn(Y) >= 0) mpz_add(at, at, PI_INT);
            else                 mpz_sub(at, at, PI_INT);
        }
    } else {
        fdivq(q, X, Y); arctan_int(at, q, 80);
        mpz_fdiv_q_ui(res, PI_INT, 2);
        if (mpz_sgn(Y) < 0){
            mpz_neg(res, res); mpz_sub(at, res, at);
        } else {
            mpz_sub(at, res, at);
        }
    }
    mpz_set(res, at);
    mpz_clears(at, q, NULL);
}

/* ---- bootstrap: identical to the Python engine ---- */
static void boot(void){
    if (booted) return;
    mpz_inits(SCALE, TWO_PI, PI_INT, ETA, LAMBDA, GAMMA_, BETA_, ALPHA,
              ALPHA_INV, HALF, QUARTER, THREEQ, NULL);
    mpz_ui_pow_ui(SCALE, 10, PREC);
    mpz_fdiv_q_ui(HALF, SCALE, 2);
    mpz_fdiv_q_ui(QUARTER, SCALE, 4);
    mpz_mul_ui(THREEQ, QUARTER, 3);
    mpz_t one5, one239, a1, a2, t;
    mpz_inits(one5, one239, a1, a2, t, NULL);
    mpz_mul_ui(t, SCALE, 5);   fdivq(one5, SCALE, t);
    mpz_mul_ui(t, SCALE, 239); fdivq(one239, SCALE, t);
    arctan_int(a1, one5, 80); arctan_int(a2, one239, 80);
    mpz_mul_ui(a1, a1, 4); mpz_sub(a1, a1, a2); mpz_mul_ui(PI_INT, a1, 4);
    mpz_mul_ui(TWO_PI, PI_INT, 2);
    mpz_fdiv_q_ui(ETA, SCALE, 2);
    mpz_fdiv_q_ui(LAMBDA, SCALE, 10);
    mpz_t gnum, gden, gsq;
    mpz_inits(gnum, gden, gsq, NULL);
    mpz_mul_ui(gnum, SCALE, 90);
    mpz_mul_ui(t, SCALE, 137); fmul(gden, t, PI_INT);
    fdivq(gsq, gnum, gden);
    fsqrt(GAMMA_, gsq, 80);
    mpz_fdiv_q_ui(BETA_, GAMMA_, 9);
    fmul(ALPHA, TWO_PI, ETA); fmul(ALPHA, ALPHA, LAMBDA);
    fmul(ALPHA, ALPHA, GAMMA_); fmul(ALPHA, ALPHA, BETA_);
    fdivq(ALPHA_INV, SCALE, ALPHA);
    mpz_clears(one5, one239, a1, a2, t, gnum, gden, gsq, NULL);
    booted = 1;
}

/* ---- FBit ---- */
typedef struct { mpz_t pf, amp; } fbit;
static void fb_init(fbit *f){ mpz_inits(f->pf, f->amp, NULL); }
static void fb_clear(fbit *f){ mpz_clears(f->pf, f->amp, NULL); }
static void fb_set(fbit *f, const mpz_t pf, const mpz_t amp){
    mpz_fdiv_r(f->pf, pf, SCALE); mpz_set(f->amp, amp);
}
static void fb_from_scalar(fbit *f, const mpz_t X){
    if (mpz_sgn(X) == 0){ mpz_set_ui(f->pf, 0); mpz_set_ui(f->amp, 0); return; }
    if (mpz_sgn(X) > 0) mpz_set_ui(f->pf, 0); else mpz_set(f->pf, HALF);
    mpz_abs(f->amp, X);
}
static void fb_to_scalar(mpz_t r, const fbit *f){
    if (mpz_cmp(f->pf, QUARTER) < 0 || mpz_cmp(f->pf, THREEQ) > 0)
        mpz_set(r, f->amp);
    else { mpz_neg(r, f->amp); }
}
static void fb_re(mpz_t r, const fbit *f){
    if (mpz_sgn(f->pf) == 0){ mpz_set(r, f->amp); return; }
    if (mpz_cmp(f->pf, HALF) == 0){ mpz_neg(r, f->amp); return; }
    if (mpz_cmp(f->pf, QUARTER) == 0 || mpz_cmp(f->pf, THREEQ) == 0){
        mpz_set_ui(r, 0); return; }
    mpz_t angle, c; mpz_inits(angle, c, NULL);
    fmul(angle, f->pf, TWO_PI); fdivq(angle, angle, SCALE);
    cos_fp(c, angle, 40); fmul(r, c, f->amp);
    mpz_clears(angle, c, NULL);
}
static void fb_im(mpz_t r, const fbit *f){
    if (mpz_sgn(f->pf) == 0 || mpz_cmp(f->pf, HALF) == 0){ mpz_set_ui(r,0); return; }
    if (mpz_cmp(f->pf, QUARTER) == 0){ mpz_set(r, f->amp); return; }
    if (mpz_cmp(f->pf, THREEQ) == 0){ mpz_neg(r, f->amp); return; }
    mpz_t angle, s; mpz_inits(angle, s, NULL);
    fmul(angle, f->pf, TWO_PI); fdivq(angle, angle, SCALE);
    sin_fp(s, angle, 40); fmul(r, s, f->amp);
    mpz_clears(angle, s, NULL);
}

/* ---- HCL operations (verbatim structure) ---- */
static void op_comp(fbit *out, const fbit *a, const fbit *b){
    mpz_t re, im, t1, t2, ampsq, amp, at, pf;
    mpz_inits(re, im, t1, t2, ampsq, amp, at, pf, NULL);
    fb_re(t1, a); fb_re(t2, b); mpz_add(re, t1, t2);
    fb_im(t1, a); fb_im(t2, b); mpz_add(im, t1, t2);
    fmul(t1, re, re); fmul(t2, im, im); mpz_add(ampsq, t1, t2);
    if (mpz_sgn(ampsq) > 0) fsqrt(amp, ampsq, 60); else mpz_set_ui(amp, 0);
    if (mpz_sgn(amp) == 0){ mpz_set_ui(out->pf, 0); mpz_set_ui(out->amp, 0); }
    else {
        atan2_fp(at, im, re);
        fdivq(pf, at, TWO_PI); mpz_fdiv_r(pf, pf, SCALE);
        fb_set(out, pf, amp);
    }
    mpz_clears(re, im, t1, t2, ampsq, amp, at, pf, NULL);
}
static void op_shift(fbit *out, const fbit *a, const mpz_t C){
    mpz_t am, pf, ac; mpz_inits(am, pf, ac, NULL);
    if (mpz_sgn(C) >= 0){
        fmul(am, a->amp, C); fb_set(out, a->pf, am);
    } else {
        mpz_add(pf, a->pf, HALF);
        mpz_abs(ac, C); fmul(am, a->amp, ac);
        fb_set(out, pf, am);
    }
    mpz_clears(am, pf, ac, NULL);
}
static void op_ampmod(fbit *out, const fbit *a, const fbit *b){
    mpz_t pf, am; mpz_inits(pf, am, NULL);
    mpz_add(pf, a->pf, b->pf);
    fmul(am, a->amp, b->amp);
    fb_set(out, pf, am);
    mpz_clears(pf, am, NULL);
}
static void op_inv(fbit *out, const fbit *a){
    mpz_t pf, am; mpz_inits(pf, am, NULL);
    mpz_sub(pf, SCALE, a->pf);
    fdivq(am, SCALE, a->amp);
    fb_set(out, pf, am);
    mpz_clears(pf, am, NULL);
}
static void op_fission1(fbit *out, const fbit *a){
    mpz_t sa, hp; mpz_inits(sa, hp, NULL);
    fsqrt(sa, a->amp, 60);
    mpz_fdiv_q_ui(hp, a->pf, 2);
    fb_set(out, hp, sa);
    mpz_clears(sa, hp, NULL);
}
static void op_mobius(fbit *out, const fbit *a){
    mpz_t x, am; mpz_inits(x, am, NULL);
    fb_to_scalar(x, a);
    exp_fp(am, x, 70);
    mpz_set_ui(out->pf, 0); mpz_set(out->amp, am);
    mpz_clears(x, am, NULL);
}
static void op_logx(fbit *out, const fbit *a){
    mpz_t v; mpz_init(v);
    ln_fp(v, a->amp, 160);
    fb_from_scalar(out, v);
    mpz_clear(v);
}
static void op_psin(mpz_t r, const mpz_t pf){
    if (mpz_sgn(pf)==0 || mpz_cmp(pf,HALF)==0){ mpz_set_ui(r,0); return; }
    if (mpz_cmp(pf,QUARTER)==0){ mpz_set(r,SCALE); return; }
    if (mpz_cmp(pf,THREEQ)==0){ mpz_neg(r,SCALE); return; }
    mpz_t angle; mpz_init(angle);
    fmul(angle, pf, TWO_PI); fdivq(angle, angle, SCALE);
    sin_fp(r, angle, 40); mpz_clear(angle);
}
static void op_pcos(mpz_t r, const mpz_t pf){
    if (mpz_sgn(pf)==0){ mpz_set(r,SCALE); return; }
    if (mpz_cmp(pf,HALF)==0){ mpz_neg(r,SCALE); return; }
    if (mpz_cmp(pf,QUARTER)==0 || mpz_cmp(pf,THREEQ)==0){ mpz_set_ui(r,0); return; }
    mpz_t angle; mpz_init(angle);
    fmul(angle, pf, TWO_PI); fdivq(angle, angle, SCALE);
    cos_fp(r, angle, 40); mpz_clear(angle);
}
static void op_resonance(fbit *out, const fbit *a, long w){
    mpz_t eps, omega, ps, am; mpz_inits(eps, omega, ps, am, NULL);
    mpz_set(eps, ETA);
    for (long i = 0; i < w - 1; i++) fmul(eps, eps, LAMBDA);
    fdivq(omega, SCALE, ETA);
    for (long i = 0; i < w - 1; i++) fmul(omega, omega, GAMMA_);
    mpz_fdiv_r(ps, omega, SCALE);
    fmul(am, eps, a->amp);
    fb_set(out, ps, am);
    mpz_clears(eps, omega, ps, am, NULL);
}

/* ---- string ABI ---- */
static char OUT1[512], OUT2[512];
static void put(char *dst, const mpz_t v){ mpz_get_str(dst, 10, v); }

const char* hf_const(const char *name){
    boot();
    if (!strcmp(name,"ALPHA_INV")) put(OUT1, ALPHA_INV);
    else if (!strcmp(name,"PI"))    put(OUT1, PI_INT);
    else if (!strcmp(name,"GAMMA")) put(OUT1, GAMMA_);
    else if (!strcmp(name,"BETA"))  put(OUT1, BETA_);
    else if (!strcmp(name,"ETA"))   put(OUT1, ETA);
    else if (!strcmp(name,"LAMBDA"))put(OUT1, LAMBDA);
    else if (!strcmp(name,"ALPHA")) put(OUT1, ALPHA);
    else strcpy(OUT1, "?");
    return OUT1;
}
const char* hf_prim(const char *op, const char *xs, const char *ys){
    boot();
    mpz_t X, Y, R; mpz_inits(X, Y, R, NULL);
    mpz_set_str(X, xs, 10); mpz_set_str(Y, ys, 10);
    if (!strcmp(op,"mul")) fmul(R, X, Y);
    else if (!strcmp(op,"div")) fdivq(R, X, Y);
    else if (!strcmp(op,"sqrt")) fsqrt(R, X, 80);
    else if (!strcmp(op,"arctan")) arctan_int(R, X, 80);
    else if (!strcmp(op,"sin")) sin_fp(R, X, 40);
    else if (!strcmp(op,"cos")) cos_fp(R, X, 40);
    else if (!strcmp(op,"exp")) exp_fp(R, X, 60);
    else if (!strcmp(op,"ln"))  ln_fp(R, X, 150);
    else mpz_set_ui(R, 0);
    put(OUT1, R);
    mpz_clears(X, Y, R, NULL);
    return OUT1;
}
/* organ ops: inputs/outputs as (phase, amp) decimal strings */
const char* hf_op(const char *op, const char *pa, const char *aa,
                  const char *pb, const char *ab, long aux,
                  const char **amp_out){
    boot();
    fbit A, B, O; fb_init(&A); fb_init(&B); fb_init(&O);
    mpz_t t; mpz_init(t);
    mpz_set_str(A.pf, pa, 10); mpz_set_str(A.amp, aa, 10);
    mpz_set_str(B.pf, pb, 10); mpz_set_str(B.amp, ab, 10);
    if (!strcmp(op,"COMP")) op_comp(&O, &A, &B);
    else if (!strcmp(op,"AMP_MOD")) op_ampmod(&O, &A, &B);
    else if (!strcmp(op,"SHIFT")) { mpz_set_str(t, pb, 10); op_shift(&O,&A,t); }
    else if (!strcmp(op,"INV")) op_inv(&O, &A);
    else if (!strcmp(op,"FISSION")) op_fission1(&O, &A);
    else if (!strcmp(op,"MOB")) op_mobius(&O, &A);
    else if (!strcmp(op,"LOG")) op_logx(&O, &A);
    else if (!strcmp(op,"RES")) op_resonance(&O, &A, aux);
    else if (!strcmp(op,"PSIN")) { op_psin(t, A.pf); fb_from_scalar(&O, t); }
    else if (!strcmp(op,"PCOS")) { op_pcos(t, A.pf); fb_from_scalar(&O, t); }
    put(OUT1, O.pf); put(OUT2, O.amp);
    *amp_out = OUT2;
    fb_clear(&A); fb_clear(&B); fb_clear(&O); mpz_clear(t);
    return OUT1;
}

/* ---- benchmarks: whole loops inside C ---- */
static double now_(){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
    return t.tv_sec + 1e-9*t.tv_nsec; }

double hf_bench_prim(int D, long reps){       /* _fixed_mul + add dot */
    boot();
    mpz_t *W = malloc(D*sizeof(mpz_t)), *x = malloc(D*sizeof(mpz_t));
    mpz_t acc, p; mpz_inits(acc, p, NULL);
    gmp_randstate_t st; gmp_randinit_default(st); gmp_randseed_ui(st, 137);
    for (int j = 0; j < D; j++){
        mpz_inits(W[j], x[j], NULL);
        mpz_urandomm(W[j], st, SCALE); mpz_urandomm(x[j], st, SCALE);
        if (j % 2) mpz_neg(W[j], W[j]);
    }
    double t0 = now_();
    for (long r = 0; r < reps; r++){
        mpz_set_ui(acc, 0);
        for (int j = 0; j < D; j++){ fmul(p, W[j], x[j]); mpz_add(acc, acc, p); }
    }
    double dt = now_() - t0;
    for (int j = 0; j < D; j++) mpz_clears(W[j], x[j], NULL);
    free(W); free(x); mpz_clears(acc, p, NULL);
    return (double)D * reps / dt;             /* ops per second */
}
double hf_bench_organ(long reps){             /* COMP+AMP_MOD pair on scalars */
    boot();
    fbit a, b, m, o; fb_init(&a); fb_init(&b); fb_init(&m); fb_init(&o);
    mpz_t va, vb; mpz_inits(va, vb, NULL);
    gmp_randstate_t st; gmp_randinit_default(st); gmp_randseed_ui(st, 137);
    mpz_urandomm(va, st, SCALE); mpz_urandomm(vb, st, SCALE); mpz_neg(vb, vb);
    fb_from_scalar(&a, va); fb_from_scalar(&b, vb);
    double t0 = now_();
    for (long r = 0; r < reps; r++){
        op_ampmod(&m, &a, &b);
        op_comp(&o, &m, &a);
    }
    double dt = now_() - t0;
    fb_clear(&a); fb_clear(&b); fb_clear(&m); fb_clear(&o);
    mpz_clears(va, vb, NULL);
    return 2.0 * reps / dt;
}
double hf_bench_memline(long reps){           /* RESONANCE write + SHIFT read */
    boot();
    fbit v, cell, rec; fb_init(&v); fb_init(&cell); fb_init(&rec);
    mpz_t val, C; mpz_inits(val, C, NULL);
    mpz_mul_ui(val, SCALE, 23); fb_from_scalar(&v, val);
    mpz_mul_ui(C, SCALE, 200);                /* 2*10^(w-1), w=3 */
    double t0 = now_();
    for (long r = 0; r < reps; r++){
        op_resonance(&cell, &v, 3);
        op_shift(&rec, &cell, C);
    }
    double dt = now_() - t0;
    fb_clear(&v); fb_clear(&cell); fb_clear(&rec); mpz_clears(val, C, NULL);
    return reps / dt;
}
