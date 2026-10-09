/* marvosa_shell.c — the compiled shell for the substrate's hot loop.
#include <stdlib.h>
 *
 * Fixed-point 40-decimal-digit integers (SCALE = 10^40, ~133 bits)
 * carried as sign + 5 x 64-bit limbs (little-endian). Products of two
 * values reach ~2^267; a 64-term dot accumulates to < 2^274 — both
 * inside the 320-bit accumulator. The only operations here are the
 * ones the layers grind: multiply, accumulate, divide by SCALE.
 * Same integers as the Python big-int path — bit-identical is the
 * contract, proven by verify_shell.py, and the pure path remains the
 * fallback when this library is absent.
 *
 * build:  sh build_shell.sh          (cc -O2 -shared -fPIC)
 */
#include <stdint.h>
#include <string.h>

#define LIMBS 5

/* r += a * b, all little-endian limb arrays; r has LIMBS*2 limbs */
static void mul_acc(const uint64_t *a, const uint64_t *b, uint64_t *r)
{
    for (int i = 0; i < LIMBS; i++) {
        __uint128_t carry = 0;
        for (int j = 0; j < LIMBS; j++) {
            __uint128_t cur = (__uint128_t)a[i] * b[j]
                            + r[i + j] + (uint64_t)carry;
            r[i + j] = (uint64_t)cur;
            carry = cur >> 64;
        }
        int k = i + LIMBS;
        while (carry) {
            __uint128_t cur = (__uint128_t)r[k] + (uint64_t)carry;
            r[k] = (uint64_t)cur;
            carry = cur >> 64;
            k++;
        }
    }
}

/* wide (2*LIMBS) += / -= wide */
static void wide_add(uint64_t *r, const uint64_t *x)
{
    __uint128_t carry = 0;
    for (int i = 0; i < 2 * LIMBS; i++) {
        __uint128_t cur = (__uint128_t)r[i] + x[i] + (uint64_t)carry;
        r[i] = (uint64_t)cur;
        carry = cur >> 64;
    }
}
static int wide_cmp(const uint64_t *a, const uint64_t *b)
{
    for (int i = 2 * LIMBS - 1; i >= 0; i--) {
        if (a[i] != b[i]) return a[i] > b[i] ? 1 : -1;
    }
    return 0;
}
static void wide_sub(uint64_t *r, const uint64_t *x)   /* r -= x, r>=x */
{
    __int128 borrow = 0;
    for (int i = 0; i < 2 * LIMBS; i++) {
        __int128 cur = (__int128)r[i] - x[i] - (int64_t)borrow;
        borrow = cur < 0;
        r[i] = (uint64_t)(cur < 0 ? cur + ((__int128)1 << 64) : cur);
    }
}

/* q = num / SCALE (floor), num 2*LIMBS wide, q LIMBS wide.
 * HCL form only: SCALE = 10^40 and lambda = 1/10 is the fourth
 * parameter's weight-scale law (lambda_w = 10^-w, 01_theory;
 * LAMBDA = SCALE/10, hcl_engine:65). Division by SCALE IS the
 * lambda operator applied 40 times; 40 = 19 + 19 + 2, and 10^19
 * fits one limb, so the application runs as three short divisions
 * by lambda-composed constants. Exact at every step. */
static const uint64_t LAMBDA19 = 10000000000000000000ULL;  /* 10^19 */
static const uint64_t LAMBDA2  = 100ULL;                   /* 10^2  */

/* literal-divisor forms over 32-bit digits: the source law is the
 * lambda cascade — SCALE = 10^40 = (10^9)^4 * 10^4, five exact short
 * divisions. 10^9 and 10^4 fit 32 bits, so every step is u64/u32:
 * hardware-fast, and the compiler realizes each constant division in
 * its own codegen. No u128 division anywhere. */
#define SHORT_DIV32_BY(NAME, D) \
static void NAME(uint32_t *num, int dwords) \
{ \
    uint64_t rem = 0; \
    for (int i = dwords - 1; i >= 0; i--) { \
        uint64_t cur = (rem << 32) | num[i]; \
        num[i] = (uint32_t)(cur / (D)); \
        rem = cur % (D); \
    } \
}
SHORT_DIV32_BY(short_div_l9, 1000000000u)   /* lambda^9 */
SHORT_DIV32_BY(short_div_l4, 10000u)        /* lambda^4 */

static int g_prec = 40;                       /* the dial, mirrored in C */
void fx_set_prec(int p){ g_prec = p; }
static void short_div_pow10(uint32_t *d, int n, uint32_t p10)
{
    uint64_t rem = 0;
    for (int i = n - 1; i >= 0; i--) {
        uint64_t cur = (rem << 32) | d[i];
        d[i] = (uint32_t)(cur / p10);
        rem  = cur % p10;
    }
}
static void div_by_scale(const uint64_t *num, uint64_t *q)
{
    /* lambda^PREC, exact, as 10^p = 2^p * 5^p (Weight-Scale
       Correspondence: lambda_w = 10^-w): one p-bit shift, then 5^p in
       single-limb chunks 5^k (k <= 27, since 5^27 < 2^63). Floor
       composition on nonnegative magnitudes is exact, so the result is
       bit-identical to the decimal cascade it replaces — re-proven by
       verify_shell.py and verify_train_fast.py on every build. */
    uint64_t w[2 * LIMBS];
    memcpy(w, num, sizeof w);
    int p = g_prec;
    /* shift right by p bits across limbs */
    int limb_sh = p / 64, bit_sh = p % 64;
    if (limb_sh) {
        for (int i = 0; i < 2 * LIMBS; i++)
            w[i] = (i + limb_sh < 2 * LIMBS) ? w[i + limb_sh] : 0;
    }
    if (bit_sh) {
        for (int i = 0; i < 2 * LIMBS; i++) {
            uint64_t hi = (i + 1 < 2 * LIMBS) ? w[i + 1] : 0;
            w[i] = (w[i] >> bit_sh) | (hi << (64 - bit_sh));
        }
    }
    /* divide by 5^p in exact single-limb chunks */
    static const uint64_t P5[28] = {1ULL,5ULL,25ULL,125ULL,625ULL,3125ULL,
        15625ULL,78125ULL,390625ULL,1953125ULL,9765625ULL,48828125ULL,
        244140625ULL,1220703125ULL,6103515625ULL,30517578125ULL,
        152587890625ULL,762939453125ULL,3814697265625ULL,19073486328125ULL,
        95367431640625ULL,476837158203125ULL,2384185791015625ULL,
        11920928955078125ULL,59604644775390625ULL,298023223876953125ULL,
        1490116119384765625ULL,7450580596923828125ULL};
    while (p > 0) {
        int k = p > 27 ? 27 : p;
        uint64_t d = P5[k];
        __uint128_t r = 0;
        for (int i = 2 * LIMBS - 1; i >= 0; i--) {
            __uint128_t cur = (r << 64) | w[i];
            w[i] = (uint64_t)(cur / d);
            r = cur % d;
        }
        p -= k;
    }
    memcpy(q, w, LIMBS * sizeof(uint64_t));
}

/* out[row] = Σ_j ±((|W[row][j]|*|x[j]|)//S) — the transcriber's dot
 * verbatim (hcl_engine:424): magnitude floor per term, sign after,
 * signed accumulation. Bit-identical to the engine is the contract. */
void fixed_dot_rows(const uint64_t *W, const int8_t *Wneg,
                    const uint64_t *X, const int8_t *Xneg,
                    int rows, int n,
                    uint64_t *out, int8_t *outneg)
{
    for (int r = 0; r < rows; r++) {
        /* signed accumulator as magnitude+sign over LIMBS+1 headroom */
        uint64_t accpos[2 * LIMBS]; memset(accpos, 0, sizeof accpos);
        uint64_t accneg[2 * LIMBS]; memset(accneg, 0, sizeof accneg);
        for (int j = 0; j < n; j++) {
            const uint64_t *w = W + (size_t)(r * n + j) * LIMBS;
            const uint64_t *x = X + (size_t)j * LIMBS;
            uint64_t prod[2 * LIMBS]; memset(prod, 0, sizeof prod);
            mul_acc(w, x, prod);
            uint64_t q[LIMBS];
            div_by_scale(prod, q);          /* lambda^40: |a*b| -> //S */
            int neg = Wneg[r * n + j] ^ Xneg[j];
            /* engine semantics (hcl_engine:424): p = (|x|*|w|)//S — the
             * magnitude floor, sign applied AFTER. wide_div already
             * gives exactly that; no signed-floor adjustment exists. */
            uint64_t wideq[2 * LIMBS]; memset(wideq, 0, sizeof wideq);
            memcpy(wideq, q, LIMBS * sizeof(uint64_t));
            wide_add(neg ? accneg : accpos, wideq);
        }
        /* out = accpos - accneg (signed) */
        if (wide_cmp(accpos, accneg) >= 0) {
            wide_sub(accpos, accneg);
            memcpy(out + (size_t)r * LIMBS, accpos, LIMBS * sizeof(uint64_t));
            outneg[r] = 0;
        } else {
            wide_sub(accneg, accpos);
            memcpy(out + (size_t)r * LIMBS, accneg, LIMBS * sizeof(uint64_t));
            outneg[r] = 1;
        }
    }
}

/* ═══ THE LAYER BODY — every transcendental and vector op, compiled ═══
 * Each function is the engine's body verbatim (hcl_engine.py), which is
 * itself the skill's law (03_engine "Transcendental Series"; 01_theory:
 * "The Taylor series IS the operator"). Two multiply semantics coexist
 * exactly as shipped: t.mul is magnitude-floor (sign after); the module
 * _fixed_mul inside the series is Python signed-floor. TINY = 10.     */

typedef struct { uint64_t m[LIMBS]; int8_t neg; } fx;   /* |value| + sign */

static void fx_zero(fx *a){ memset(a->m,0,sizeof a->m); a->neg=0; }
static int  fx_is0(const fx *a){ for(int i=0;i<LIMBS;i++) if(a->m[i]) return 0; return 1; }
static int  mag_cmp(const uint64_t *a,const uint64_t *b){
    for(int i=LIMBS-1;i>=0;i--){ if(a[i]!=b[i]) return a[i]>b[i]?1:-1; } return 0; }
static void mag_add(uint64_t *r,const uint64_t *x){
    __uint128_t c=0; for(int i=0;i<LIMBS;i++){ __uint128_t cur=(__uint128_t)r[i]+x[i]+(uint64_t)c; r[i]=(uint64_t)cur; c=cur>>64; } }
static void mag_sub(uint64_t *r,const uint64_t *x){          /* r>=x */
    __int128 b=0; for(int i=0;i<LIMBS;i++){ __int128 cur=(__int128)r[i]-x[i]-(int64_t)b; b=cur<0; r[i]=(uint64_t)(cur<0?cur+((__int128)1<<64):cur); } }
static void fx_add(const fx *a,const fx *b,fx *r){            /* signed a+b */
    if(a->neg==b->neg){ memcpy(r->m,a->m,sizeof r->m); mag_add(r->m,b->m); r->neg=a->neg; }
    else { int c=mag_cmp(a->m,b->m);
        if(c>=0){ memcpy(r->m,a->m,sizeof r->m); mag_sub(r->m,b->m); r->neg=a->neg; }
        else    { memcpy(r->m,b->m,sizeof r->m); mag_sub(r->m,a->m); r->neg=b->neg; } }
    if(fx_is0(r)) r->neg=0; }
static void fx_sub(const fx *a,const fx *b,fx *r){ fx nb=*b; nb.neg=!nb.neg; fx_add(a,&nb,r); }

/* |a|*|b| -> 2*LIMBS, then lambda-cascade /S; sign by xor: t.mul law */
static void mag_mul_divS(const uint64_t *a,const uint64_t *b,uint64_t *q){
    uint64_t prod[2*LIMBS]; memset(prod,0,sizeof prod);
    mul_acc(a,b,prod); div_by_scale(prod,q); }
static void fx_tmul(const fx *a,const fx *b,fx *r){
    mag_mul_divS(a->m,b->m,r->m); r->neg=(a->neg!=b->neg)&&!fx_is0(r); }

/* remainder != 0 test after /S: prod != q*S */
static int rem_nonzero(const uint64_t *prod,const uint64_t *q,const uint64_t *S){
    uint64_t back[2*LIMBS]; memset(back,0,sizeof back);
    mul_acc(q,S,back);
    for(int i=0;i<2*LIMBS;i++) if(back[i]!=prod[i]) return 1;
    return 0; }

/* module _fixed_mul: SIGNED floor (toward -inf): magnitude then, when
 * signs differ and a remainder was truncated, magnitude += 1           */
static void fx_smul(const fx *a,const fx *b,const uint64_t *S,fx *r){
    uint64_t prod[2*LIMBS]; memset(prod,0,sizeof prod);
    mul_acc(a->m,b->m,prod); div_by_scale(prod,r->m);
    r->neg=(a->neg!=b->neg);
    if(r->neg && rem_nonzero(prod,r->m,S)){
        __uint128_t c=1; for(int i=0;i<LIMBS&&c;i++){ __uint128_t cur=(__uint128_t)r->m[i]+(uint64_t)c; r->m[i]=(uint64_t)cur; c=cur>>64; } }
    if(fx_is0(r)) r->neg=0; }


/* ── Knuth Algorithm D: limb-wise division, base 2^64 ─────────────────
 * num[2n] // den[n] -> q[n_q<=2n], rem[n]. ~n^2 mul64 instead of the
 * bit-serial loop's 128n shifts — this is why C wins here at all.     */
static void knuth_div(const uint64_t*num,int nn,const uint64_t*den,int dn,
                      uint64_t*q,int qn,uint64_t*rem){
    while(dn>1 && den[dn-1]==0) dn--;
    int un=nn; while(un>1 && num[un-1]==0) un--;
    memset(q,0,(size_t)qn*sizeof(uint64_t));
    if(dn==1){
        __uint128_t r=0; uint64_t d=den[0];
        for(int i=un-1;i>=0;i--){ __uint128_t cur=(r<<64)|num[i];
            uint64_t qi=(uint64_t)(cur/d); r=cur%d;
            if(i<qn) q[i]=qi; }
        if(rem){ memset(rem,0,(size_t)dn*sizeof(uint64_t)); rem[0]=(uint64_t)r; }
        return; }
    int sh=__builtin_clzll(den[dn-1]);
    uint64_t dnorm[32]; uint64_t unorm[65];
    for(int i=dn-1;i>0;i--) dnorm[i]=(den[i]<<sh)|(sh?(den[i-1]>>(64-sh)):0);
    dnorm[0]=den[0]<<sh;
    unorm[un]= sh?(num[un-1]>>(64-sh)):0;
    for(int i=un-1;i>0;i--) unorm[i]=(num[i]<<sh)|(sh?(num[i-1]>>(64-sh)):0);
    unorm[0]=num[0]<<sh;
    for(int j=un-dn;j>=0;j--){
        __uint128_t top=((__uint128_t)unorm[j+dn]<<64)|unorm[j+dn-1];
        uint64_t qh=(uint64_t)(top/dnorm[dn-1]);
        uint64_t rh=(uint64_t)(top%dnorm[dn-1]);
        if(top/dnorm[dn-1]>>64) qh=~0ULL;
        while((__uint128_t)qh*dnorm[dn-2] > (((__uint128_t)rh<<64)|unorm[j+dn-2])){
            qh--; rh+=dnorm[dn-1]; if(rh<dnorm[dn-1]) break; }
        __int128 borrow=0; __uint128_t carry=0;
        for(int i=0;i<dn;i++){
            __uint128_t p=(__uint128_t)qh*dnorm[i]+carry;
            carry=p>>64;
            __int128 sub=(__int128)unorm[i+j]-(uint64_t)p-borrow;
            borrow=sub<0; unorm[i+j]=(uint64_t)(sub<0?sub+((__int128)1<<64):sub); }
        __int128 subl=(__int128)unorm[j+dn]-(uint64_t)carry-borrow;
        unorm[j+dn]=(uint64_t)(subl<0?subl+((__int128)1<<64):subl);
        if(subl<0){
            qh--; __uint128_t c2=0;
            for(int i=0;i<dn;i++){ __uint128_t cur=(__uint128_t)unorm[i+j]+dnorm[i]+(uint64_t)c2;
                unorm[i+j]=(uint64_t)cur; c2=cur>>64; }
            unorm[j+dn]+= (uint64_t)c2; }
        if(j<qn) q[j]=qh; }
    if(rem){ for(int i=0;i<dn;i++) rem[i]= (unorm[i]>>sh)|((sh&&i+1<dn)?(unorm[i+1]<<(64-sh)):((sh&&i+1==dn)?(unorm[dn]<<(64-sh)):0));
        for(int i=dn;i<32&&i<dn;i++) rem[i]=0; }
}
/* general |num| // |den|: binary long division, num 2*LIMBS, den LIMBS */
static void mag_divl(const uint64_t *num,const uint64_t *den,uint64_t *q,uint64_t *rem_out){
    knuth_div(num,2*LIMBS,den,LIMBS,q,LIMBS,rem_out); }

/* t.div law verbatim: (|X| * (S^2 // |Y|)) // S, sign after            */
static void fx_tdiv(const fx *X,const fx *Y,const uint64_t *S2,fx *r){
    uint64_t recip[LIMBS], wide[2*LIMBS];
    mag_divl(S2,Y->m,recip,0);
    memset(wide,0,sizeof wide); mul_acc(X->m,recip,wide);
    div_by_scale(wide,r->m);
    r->neg=(X->neg!=Y->neg)&&!fx_is0(r); if(fx_is0(r)) r->neg=0; }

/* module _fixed_div: SIGNED (X*S)//Y with pole and sub-quantum clamp   */
static void fx_sdiv(const fx *X,const fx *Y,const uint64_t *S,fx *r){
    if(fx_is0(Y)){ memcpy(r->m,S,LIMBS*sizeof(uint64_t)); r->neg=X->neg; return; }
    uint64_t num[2*LIMBS]; memset(num,0,sizeof num);
    mul_acc(X->m,S,num);
    uint64_t rem[LIMBS];
    mag_divl(num,Y->m,r->m,rem);
    int rnz=0; for(int i=0;i<LIMBS;i++) if(rem[i]) { rnz=1; break; }
    r->neg=(X->neg!=Y->neg);
    if(r->neg && rnz){ __uint128_t c=1; for(int i=0;i<LIMBS&&c;i++){ __uint128_t cur=(__uint128_t)r->m[i]+(uint64_t)c; r->m[i]=(uint64_t)cur; c=cur>>64; } }
    if(fx_is0(r)){
        if(!fx_is0(X)){ r->m[0]=1; r->neg=(X->neg!=Y->neg); }
        else r->neg=0; }
}

static void fx_half_floor(fx *X){        /* Python X//2 on signed value */
    int odd = X->m[0]&1;
    for(int i=0;i<LIMBS-1;i++) X->m[i]=(X->m[i]>>1)|(X->m[i+1]<<63);
    X->m[LIMBS-1]>>=1;
    if(X->neg && odd){ __uint128_t c=1; for(int i=0;i<LIMBS&&c;i++){ __uint128_t cur=(__uint128_t)X->m[i]+(uint64_t)c; X->m[i]=(uint64_t)cur; c=cur>>64; } }
    if(fx_is0(X)) X->neg=0; }
static void fx_sdiv_smallpos(fx *X,uint32_t d){   /* signed X//d, d>0 small */
    uint64_t rem=0;
    uint32_t *dw=(uint32_t*)X->m;
    for(int i=2*LIMBS-1;i>=0;i--){ uint64_t cur=(rem<<32)|dw[i]; dw[i]=(uint32_t)(cur/d); rem=cur%d; }
    if(X->neg && rem){ __uint128_t c=1; for(int i=0;i<LIMBS&&c;i++){ __uint128_t cur=(__uint128_t)X->m[i]+(uint64_t)c; X->m[i]=(uint64_t)cur; c=cur>>64; } }
    if(fx_is0(X)) X->neg=0; }

/* _exp_fp verbatim: halve to |x|<=1, series with signed-floor terms,
 * TINY break, k squarings                                              */
static void fx_exp(const fx *Xin,const uint64_t *S,fx *r){
    fx X=*Xin; int k=0;
    while(mag_cmp(X.m,S)>0){ fx_half_floor(&X); k++; }
    fx res, term;
    memcpy(res.m,S,LIMBS*sizeof(uint64_t)); res.neg=0;
    term=res;
    for(int i=1;i<70;i++){
        fx t2; fx_smul(&term,&X,S,&t2); term=t2;
        fx_sdiv_smallpos(&term,(uint32_t)i);
        fx r2; fx_add(&res,&term,&r2); res=r2;
        if(!term.neg||1){ if(term.m[4]==0&&term.m[3]==0&&term.m[2]==0&&term.m[1]==0&&term.m[0]<10) break; }
    }
    for(int j=0;j<k;j++){ fx r2; fx_smul(&res,&res,S,&r2); res=r2; }
    *r=res; }


static void small_times_S(uint64_t j,const uint64_t *S,fx *out){
    fx js; fx_zero(&js); js.m[0]=j; js.neg=0;
    /* j*S: multiply S by small j */
    uint64_t prod[2*LIMBS]; memset(prod,0,sizeof prod);
    __uint128_t c=0;
    for(int i=0;i<LIMBS;i++){ __uint128_t cur=(__uint128_t)S[i]*j+(uint64_t)c; prod[i]=(uint64_t)cur; c=cur>>64; }
    memcpy(out->m,prod,LIMBS*sizeof(uint64_t)); out->neg=0; }

static int fx_below_tiny(const fx *t){
    for(int i=1;i<LIMBS;i++) if(t->m[i]) return 0;
    return t->m[0]<10; }


/* ── wide interior for the trig series: fact reaches (79)!*S ~ 1e158,
 * far past 5 limbs. WL=9 limbs (576 bits ~ 173 digits) holds every
 * intermediate of the 40-term law; values narrow back on return.      */
#define WL 9
typedef struct { uint64_t m[WL]; int8_t neg; } fw;
static int fw_is0(const fw*a){ for(int i=0;i<WL;i++) if(a->m[i]) return 0; return 1; }
static int wmag_cmp(const uint64_t*a,const uint64_t*b){
    for(int i=WL-1;i>=0;i--){ if(a[i]!=b[i]) return a[i]>b[i]?1:-1; } return 0; }
static void wmag_add(uint64_t*r,const uint64_t*x){
    __uint128_t c=0; for(int i=0;i<WL;i++){ __uint128_t cur=(__uint128_t)r[i]+x[i]+(uint64_t)c; r[i]=(uint64_t)cur; c=cur>>64; } }
static void wmag_sub(uint64_t*r,const uint64_t*x){
    __int128 b=0; for(int i=0;i<WL;i++){ __int128 cur=(__int128)r[i]-x[i]-(int64_t)b; b=cur<0; r[i]=(uint64_t)(cur<0?cur+((__int128)1<<64):cur); } }
static void fw_add(const fw*a,const fw*b,fw*r){
    if(a->neg==b->neg){ memcpy(r->m,a->m,sizeof r->m); wmag_add(r->m,b->m); r->neg=a->neg; }
    else { int c=wmag_cmp(a->m,b->m);
        if(c>=0){ memcpy(r->m,a->m,sizeof r->m); wmag_sub(r->m,b->m); r->neg=a->neg; }
        else    { memcpy(r->m,b->m,sizeof r->m); wmag_sub(r->m,a->m); r->neg=b->neg; } }
    if(fw_is0(r)) r->neg=0; }
static void wmul_acc(const uint64_t*a,const uint64_t*b,uint64_t*prod){ /* WL x WL -> 2WL */
    for(int i=0;i<WL;i++){ uint64_t c=0;
        for(int j=0;j<WL;j++){ __uint128_t cur=(__uint128_t)a[i]*b[j]+prod[i+j]+c;
            prod[i+j]=(uint64_t)cur; c=(uint64_t)(cur>>64); }
        prod[i+WL]+=c; } }
/* 2WL-wide // WL-wide, quotient 2WL kept wide enough via WL out + high check */
static void wmag_divl(const uint64_t*num,const uint64_t*den,uint64_t*q,uint64_t*rem_out){
    knuth_div(num,2*WL,den,WL,q,WL,rem_out); }
/* wide S: SCALE widened to WL limbs (top limbs zero) */
static void widenS(const uint64_t*S,uint64_t*WS){ memset(WS,0,WL*sizeof(uint64_t)); memcpy(WS,S,LIMBS*sizeof(uint64_t)); }
static void fw_from_fx(const fx*a,fw*o){ memset(o->m,0,sizeof o->m); memcpy(o->m,a->m,LIMBS*sizeof(uint64_t)); o->neg=a->neg; }
static void fx_from_fw(const fw*a,fx*o){ memcpy(o->m,a->m,LIMBS*sizeof(uint64_t)); o->neg=a->neg; }
/* wide signed-floor mul by /S */
static void fw_smul(const fw*a,const fw*b,const uint64_t*WS,fw*r){
    uint64_t prod[2*WL]; memset(prod,0,sizeof prod);
    wmul_acc(a->m,b->m,prod);
    uint64_t rem[WL];
    wmag_divl(prod,WS,r->m,rem);
    int rnz=0; for(int i=0;i<WL;i++) if(rem[i]){rnz=1;break;}
    r->neg=(a->neg!=b->neg);
    if(r->neg&&rnz){ __uint128_t c=1; for(int i=0;i<WL&&c;i++){ __uint128_t cur=(__uint128_t)r->m[i]+(uint64_t)c; r->m[i]=(uint64_t)cur; c=cur>>64; } }
    if(fw_is0(r)) r->neg=0; }
/* wide signed (X*S)//Y with clamp (pole unreachable: fact>0) */
static void fw_sdiv(const fw*X,const fw*Y,const uint64_t*WS,fw*r){
    uint64_t num[2*WL]; memset(num,0,sizeof num);
    wmul_acc(X->m,WS,num);
    uint64_t rem[WL];
    wmag_divl(num,Y->m,r->m,rem);
    int rnz=0; for(int i=0;i<WL;i++) if(rem[i]){rnz=1;break;}
    r->neg=(X->neg!=Y->neg);
    if(r->neg&&rnz){ __uint128_t c=1; for(int i=0;i<WL&&c;i++){ __uint128_t cur=(__uint128_t)r->m[i]+(uint64_t)c; r->m[i]=(uint64_t)cur; c=cur>>64; } }
    if(fw_is0(r)){ int xnz=!fw_is0(X); if(xnz){ r->m[0]=1; r->neg=(X->neg!=Y->neg);} else r->neg=0; } }
static void w_small_times_S(uint64_t j,const uint64_t*WS,fw*out){
    memset(out->m,0,sizeof out->m); out->neg=0;
    __uint128_t c=0; for(int i=0;i<WL;i++){ __uint128_t cur=(__uint128_t)WS[i]*j+(uint64_t)c; out->m[i]=(uint64_t)cur; c=cur>>64; } }
static int fw_below_tiny(const fw*t){ for(int i=1;i<WL;i++) if(t->m[i]) return 0; return t->m[0]<10; }
static void fx_sin(const fx*Xrad,const uint64_t*S,fx*r){
    uint64_t WS[WL]; widenS(S,WS);
    fw x; fw_from_fx(Xrad,&x);
    fw x2; fw_smul(&x,&x,WS,&x2);
    fw fact; memset(fact.m,0,sizeof fact.m); memcpy(fact.m,S,LIMBS*sizeof(uint64_t)); fact.neg=0;
    fw xpow=x; fw res; memset(&res,0,sizeof res);
    for(int k=0;k<40;k++){
        if(k){ fw jS,t;
            w_small_times_S((uint64_t)(2*k),WS,&jS);   fw_smul(&fact,&jS,WS,&t); fact=t;
            w_small_times_S((uint64_t)(2*k+1),WS,&jS); fw_smul(&fact,&jS,WS,&t); fact=t; }
        fw term; fw_sdiv(&xpow,&fact,WS,&term);
        if(k%2) term.neg=!term.neg;
        fw r2; fw_add(&res,&term,&r2); res=r2;
        fw t2; fw_smul(&xpow,&x2,WS,&t2); xpow=t2;
        fw at=term; at.neg=0;
        if(fw_below_tiny(&at)) break; }
    fx_from_fw(&res,r); }

static void fx_cos(const fx*Xrad,const uint64_t*S,fx*r){
    uint64_t WS[WL]; widenS(S,WS);
    fw x; fw_from_fx(Xrad,&x);
    fw x2; fw_smul(&x,&x,WS,&x2);
    fw fact; memset(fact.m,0,sizeof fact.m); memcpy(fact.m,S,LIMBS*sizeof(uint64_t)); fact.neg=0;
    fw xpow=x2; fw res; memset(&res,0,sizeof res);
    memcpy(res.m,S,LIMBS*sizeof(uint64_t)); res.neg=0;
    for(int k=1;k<40;k++){
        { fw jS,t;
          w_small_times_S((uint64_t)(2*k-1),WS,&jS); fw_smul(&fact,&jS,WS,&t); fact=t;
          w_small_times_S((uint64_t)(2*k),WS,&jS);   fw_smul(&fact,&jS,WS,&t); fact=t; }
        fw term; fw_sdiv(&xpow,&fact,WS,&term);
        if(k%2) term.neg=!term.neg;
        fw r2; fw_add(&res,&term,&r2); res=r2;
        fw t2; fw_smul(&xpow,&x2,WS,&t2); xpow=t2;
        fw at=term; at.neg=0;
        if(fw_below_tiny(&at)) break; }
    fx_from_fw(&res,r); }

/* _fixed_sqrt(amp, 60): Newton with bit-length seed on target=amp*S    */
static void fx_sqrt_mag(const uint64_t *amp,const uint64_t *S,uint64_t *R){
    uint64_t target[2*LIMBS]; memset(target,0,sizeof target);
    mul_acc(amp,S,target);
    int bits=0; for(int i=2*LIMBS-1;i>=0;i--){ if(target[i]){ bits=i*64+64-__builtin_clzll(target[i]); break; } }
    if(!bits){ memset(R,0,LIMBS*sizeof(uint64_t)); return; }
    uint64_t Rg[LIMBS]; memset(Rg,0,LIMBS*sizeof(uint64_t));
    int sb=(bits+1)/2; if(sb>LIMBS*64-1) sb=LIMBS*64-1;
    Rg[sb>>6]=1ULL<<(sb&63);
    for(int it=0; it<60; it++){
        uint64_t q[LIMBS]; mag_divl(target,Rg,q,0);
        uint64_t nx[LIMBS]; memcpy(nx,Rg,sizeof nx);
        __uint128_t c=0; for(int i=0;i<LIMBS;i++){ __uint128_t cur=(__uint128_t)nx[i]+q[i]+(uint64_t)c; nx[i]=(uint64_t)cur; c=cur>>64; }
        for(int i=0;i<LIMBS-1;i++) nx[i]=(nx[i]>>1)|(nx[i+1]<<63);
        nx[LIMBS-1]>>=1;
        uint64_t diff[LIMBS]; int ge=mag_cmp(nx,Rg)>=0;
        if(ge){ memcpy(diff,nx,sizeof diff); mag_sub(diff,Rg); } else { memcpy(diff,Rg,sizeof diff); mag_sub(diff,nx); }
        int small=1; for(int i=1;i<LIMBS;i++) if(diff[i]){ small=0; break; }
        if(small && diff[0]<=1) break;    /* engine: break BEFORE commit */
        memcpy(Rg,nx,sizeof Rg); }
    memcpy(R,Rg,LIMBS*sizeof(uint64_t)); }

/* ═══ exported entry points (flat limb buffers, sign bytes) ═══        */
static void load_fx(const uint64_t *m,const int8_t *n,int i,fx *o){
    memcpy(o->m,m+(size_t)i*LIMBS,LIMBS*sizeof(uint64_t)); o->neg=n[i]; }
static void store_fx(uint64_t *m,int8_t *n,int i,const fx *v){
    memcpy(m+(size_t)i*LIMBS,v->m,LIMBS*sizeof(uint64_t)); n[i]=v->neg; }

void fxv_add(const uint64_t*A,const int8_t*An,const uint64_t*B,const int8_t*Bn,int n,uint64_t*O,int8_t*On){
    for(int i=0;i<n;i++){ fx a,b,r; load_fx(A,An,i,&a); load_fx(B,Bn,i,&b); fx_add(&a,&b,&r); store_fx(O,On,i,&r);} }
void fxv_sub(const uint64_t*A,const int8_t*An,const uint64_t*B,const int8_t*Bn,int n,uint64_t*O,int8_t*On){
    for(int i=0;i<n;i++){ fx a,b,r; load_fx(A,An,i,&a); load_fx(B,Bn,i,&b); fx_sub(&a,&b,&r); store_fx(O,On,i,&r);} }
void fxv_mul(const uint64_t*A,const int8_t*An,const uint64_t*B,const int8_t*Bn,int n,uint64_t*O,int8_t*On){
    for(int i=0;i<n;i++){ fx a,b,r; load_fx(A,An,i,&a); load_fx(B,Bn,i,&b); fx_tmul(&a,&b,&r); store_fx(O,On,i,&r);} }
void fxv_scale(const uint64_t*A,const int8_t*An,const uint64_t*K,int8_t Kn,int n,uint64_t*O,int8_t*On){
    fx k; memcpy(k.m,K,LIMBS*sizeof(uint64_t)); k.neg=Kn;
    for(int i=0;i<n;i++){ fx a,r; load_fx(A,An,i,&a); fx_tmul(&a,&k,&r); store_fx(O,On,i,&r);} }
void fxv_axpy(uint64_t*ACC,int8_t*ACCn,const uint64_t*K,int8_t Kn,const uint64_t*X,const int8_t*Xn,int n){
    fx k; memcpy(k.m,K,LIMBS*sizeof(uint64_t)); k.neg=Kn;
    for(int i=0;i<n;i++){ fx x,p,acc,r; load_fx(X,Xn,i,&x); fx_tmul(&x,&k,&p);
        load_fx(ACC,ACCn,i,&acc); fx_add(&acc,&p,&r); store_fx(ACC,ACCn,i,&r);} }
void fx_exp1(const uint64_t*X,int8_t Xn,const uint64_t*S,uint64_t*O,int8_t*On){
    fx x,r; memcpy(x.m,X,LIMBS*sizeof(uint64_t)); x.neg=Xn; fx_exp(&x,S,&r);
    memcpy(O,r.m,LIMBS*sizeof(uint64_t)); *On=r.neg; }
void fx_sin1(const uint64_t*X,int8_t Xn,const uint64_t*S,uint64_t*O,int8_t*On){
    fx x,r; memcpy(x.m,X,LIMBS*sizeof(uint64_t)); x.neg=Xn; fx_sin(&x,S,&r);
    memcpy(O,r.m,LIMBS*sizeof(uint64_t)); *On=r.neg; }
void fx_cos1(const uint64_t*X,int8_t Xn,const uint64_t*S,uint64_t*O,int8_t*On){
    fx x,r; memcpy(x.m,X,LIMBS*sizeof(uint64_t)); x.neg=Xn; fx_cos(&x,S,&r);
    memcpy(O,r.m,LIMBS*sizeof(uint64_t)); *On=r.neg; }
void fx_sqrt1(const uint64_t*X,const uint64_t*S,uint64_t*O){
    fx_sqrt_mag(X,S,O); }
void fx_tdiv1(const uint64_t*X,int8_t Xn,const uint64_t*Y,int8_t Yn,const uint64_t*S2,uint64_t*O,int8_t*On){
    fx x,y,r; memcpy(x.m,X,LIMBS*sizeof(uint64_t)); x.neg=Xn;
    memcpy(y.m,Y,LIMBS*sizeof(uint64_t)); y.neg=Yn;
    fx_tdiv(&x,&y,S2,&r);
    memcpy(O,r.m,LIMBS*sizeof(uint64_t)); *On=r.neg; }

/* ── fused row kernels: one crossing per row, engine op order verbatim ── */
void fx_softmax(const uint64_t*Z,const int8_t*Zn,int n,
                const uint64_t*S,const uint64_t*S2,
                uint64_t*O,int8_t*On){
    /* max (boundary compare, signed) */
    fx m; load_fx(Z,Zn,0,&m);
    for(int i=1;i<n;i++){ fx zi; load_fx(Z,Zn,i,&zi);
        fx d; fx_sub(&zi,&m,&d);
        if(!d.neg && !fx_is0(&d)) m=zi; }
    /* exps of (z_i - m) */
    fx *ex=(fx*)malloc(sizeof(fx)*n);
    fx ssum; fx_zero(&ssum);
    for(int i=0;i<n;i++){ fx zi,d; load_fx(Z,Zn,i,&zi); fx_sub(&zi,&m,&d);
        fx_exp(&d,S,&ex[i]);
        fx t; fx_add(&ssum,&ex[i],&t); ssum=t; }
    /* inv_s = t.div(1*S, sum); then vscale */
    fx one; fx_zero(&one); memcpy(one.m,S,LIMBS*sizeof(uint64_t));
    fx inv; fx_tdiv(&one,&ssum,S2,&inv);
    for(int i=0;i<n;i++){ fx r; fx_tmul(&ex[i],&inv,&r); store_fx(O,On,i,&r); }
    free(ex); }

void fx_silu_mul(const uint64_t*H1,const int8_t*H1n,
                 const uint64_t*H3,const int8_t*H3n,int n,
                 const uint64_t*S,const uint64_t*S2,
                 uint64_t*O,int8_t*On){
    fx one; fx_zero(&one); memcpy(one.m,S,LIMBS*sizeof(uint64_t));
    for(int i=0;i<n;i++){
        fx a,b; load_fx(H1,H1n,i,&a); load_fx(H3,H3n,i,&b);
        fx na=a; na.neg=!na.neg; if(fx_is0(&na)) na.neg=0;
        fx e; fx_exp(&na,S,&e);
        fx den; fx_add(&one,&e,&den);
        fx sig; fx_tdiv(&one,&den,S2,&sig);
        fx t1; fx_tmul(&a,&sig,&t1);
        fx r;  fx_tmul(&t1,&b,&r);
        store_fx(O,On,i,&r); }
}

void fx_rope(uint64_t*V,int8_t*Vn,int upto,int head_size,
             const uint64_t*POSF,const uint64_t*INVF,const int8_t*INVFn,
             const uint64_t*TWO_PI,const uint64_t*S,const uint64_t*S2){
    /* per pair: val=mul(pos,invf); pf=t.div(val,2pi) mod S; cos,sin;
       v0'=sub(mul(v0,c),mul(v1,s)); v1'=add(mul(v0,s),mul(v1,c))       */
    fx pos; fx_zero(&pos); memcpy(pos.m,POSF,LIMBS*sizeof(uint64_t));
    fx twopi; fx_zero(&twopi); memcpy(twopi.m,TWO_PI,LIMBS*sizeof(uint64_t));
    fx Sfx; fx_zero(&Sfx); memcpy(Sfx.m,S,LIMBS*sizeof(uint64_t));
    for(int i=0;i<upto;i+=2){
        int j=(i%head_size)/2;
        fx invf; load_fx(INVF,INVFn,j,&invf);
        fx val; fx_tmul(&pos,&invf,&val);
        fx pf; fx_tdiv(&val,&twopi,S2,&pf);
        /* pf %= S: subtract S while >= S (val>=0, invf>=0) */
        while(mag_cmp(pf.m,S)>=0){ mag_sub(pf.m,S); }
        /* specials */
        fx c,sn; int done=0;
        uint64_t q4[LIMBS], q2[LIMBS], q34[LIMBS];
        memcpy(q4,S,sizeof q4);  { uint64_t r=0; uint32_t*w=(uint32_t*)q4;  for(int t2=2*LIMBS-1;t2>=0;t2--){ uint64_t cur=(r<<32)|w[t2]; w[t2]=(uint32_t)(cur/4); r=cur%4; } }
        memcpy(q2,S,sizeof q2);  { uint64_t r=0; uint32_t*w=(uint32_t*)q2;  for(int t2=2*LIMBS-1;t2>=0;t2--){ uint64_t cur=(r<<32)|w[t2]; w[t2]=(uint32_t)(cur/2); r=cur%2; } }
        for(int t2=0;t2<LIMBS;t2++) q34[t2]=q4[t2];
        { __uint128_t c2=0; for(int t2=0;t2<LIMBS;t2++){ __uint128_t cur=(__uint128_t)q34[t2]+q2[t2]+(uint64_t)c2; q34[t2]=(uint64_t)cur; c2=cur>>64; } }
        if(fx_is0(&pf)){ c=Sfx; fx_zero(&sn); done=1; }
        else if(!memcmp(pf.m,q4,sizeof q4)){ fx_zero(&c); sn=Sfx; done=1; }
        else if(!memcmp(pf.m,q2,sizeof q2)){ c=Sfx; c.neg=1; fx_zero(&sn); done=1; }
        else if(!memcmp(pf.m,q34,sizeof q34)){ fx_zero(&c); sn=Sfx; sn.neg=1; done=1; }
        if(!done){
            /* angle = _fixed_div(_fixed_mul(pf,2PI), S) — module semantics */
            fx ang_m; fx_smul(&pf,&twopi,S,&ang_m);       /* signed-floor */
            fx ang; fx_sdiv(&ang_m,&Sfx,S,&ang);
            fx_cos(&ang,S,&c); fx_sin(&ang,S,&sn); }
        fx v0,v1; load_fx(V,Vn,i,&v0); load_fx(V,Vn,i+1,&v1);
        fx a,b,r0,r1,t;
        fx_tmul(&v0,&c,&a); fx_tmul(&v1,&sn,&b); fx_sub(&a,&b,&r0);
        fx_tmul(&v0,&sn,&a); fx_tmul(&v1,&c,&t); fx_add(&a,&t,&r1);
        store_fx(V,Vn,i,&r0); store_fx(V,Vn,i+1,&r1); }
}

/* ═══ TRAINING KERNELS — the reverse walk's two hot patterns, same law ═══
 * Both are the transcriber's mul (magnitude floor, sign after) + signed
 * accumulation, exactly as the pure loops in learn.py mat_b and the
 * lm_head adjoint. Zero dy-rows are skipped exactly as the pure loops
 * skip them (gy == 0: continue) — same values, same generator counts. */

static int mag_is0(const uint64_t *m){
    for (int i = 0; i < LIMBS; i++) if (m[i]) return 0;
    return 1;
}

/* out[j] = Σ_r ±((|Y[r]|·|W[r][j]|)//S)  — dx = Wᵀ·dy, skipping zero rows */
void fixed_dot_cols(const uint64_t *W, const int8_t *Wneg,
                    const uint64_t *Y, const int8_t *Yneg,
                    int rows, int n, uint64_t *out, int8_t *outneg)
{
    for (int j = 0; j < n; j++) {
        uint64_t accpos[2 * LIMBS]; memset(accpos, 0, sizeof accpos);
        uint64_t accneg[2 * LIMBS]; memset(accneg, 0, sizeof accneg);
        for (int r = 0; r < rows; r++) {
            const uint64_t *y = Y + (size_t)r * LIMBS;
            if (mag_is0(y)) continue;                    /* gy==0: continue */
            const uint64_t *w = W + ((size_t)r * n + j) * LIMBS;
            uint64_t prod[2 * LIMBS]; memset(prod, 0, sizeof prod);
            mul_acc(y, w, prod);
            uint64_t q[LIMBS];
            div_by_scale(prod, q);
            int neg = Yneg[r] ^ Wneg[r * n + j];
            uint64_t wideq[2 * LIMBS]; memset(wideq, 0, sizeof wideq);
            memcpy(wideq, q, LIMBS * sizeof(uint64_t));
            wide_add(neg ? accneg : accpos, wideq);
        }
        if (wide_cmp(accpos, accneg) >= 0) {
            wide_sub(accpos, accneg);
            memcpy(out + (size_t)j * LIMBS, accpos, LIMBS * sizeof(uint64_t));
            outneg[j] = 0;
        } else {
            wide_sub(accneg, accpos);
            memcpy(out + (size_t)j * LIMBS, accneg, LIMBS * sizeof(uint64_t));
            outneg[j] = 1;
        }
    }
}

/* Gw[r][j] = Gw[r][j] ± (|Y[r]|·|X[j]|)//S  — dW += dy⊗x, signed fx_add;
 * skips zero dy rows; returns the count of nonzero rows for braid parity */
int fixed_outer_acc(uint64_t *Gw, int8_t *Gneg,
                    const uint64_t *Y, const int8_t *Yneg,
                    const uint64_t *X, const int8_t *Xneg,
                    int rows, int n)
{
    int nz = 0;
    for (int r = 0; r < rows; r++) {
        const uint64_t *y = Y + (size_t)r * LIMBS;
        if (mag_is0(y)) continue;
        nz++;
        for (int j = 0; j < n; j++) {
            const uint64_t *x = X + (size_t)j * LIMBS;
            fx p, g, s;
            mag_mul_divS(y, x, p.m);
            p.neg = (Yneg[r] != Xneg[j]) && !fx_is0(&p);
            size_t off = ((size_t)r * n + j);
            memcpy(g.m, Gw + off * LIMBS, LIMBS * sizeof(uint64_t));
            g.neg = Gneg[off];
            fx_add(&g, &p, &s);
            memcpy(Gw + off * LIMBS, s.m, LIMBS * sizeof(uint64_t));
            Gneg[off] = s.neg;
        }
    }
    return nz;
}
