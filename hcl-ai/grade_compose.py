import json, sys
taught=[l.strip() for l in open('gradebook.txt') if l.strip()]
prior=[l.strip() for l in open('prior.txt') if l.strip()]
def grade(q, a):
    aw=a.split(); n=len(aw)
    cover=[None]*n
    for ti,t in enumerate(taught):
        tw=t.split()
        for i in range(n):
            for j in range(n,i,-1):
                if j-i<3: break
                seg=aw[i:j]
                for k in range(len(tw)-len(seg)+1):
                    if tw[k:k+len(seg)]==seg:
                        for x in range(i,j):
                            if cover[x] is None or (cover[x][1]-cover[x][0])<(j-i):
                                cover[x]=(i,j,ti)
                        break
    srcs={c[2] for c in cover if c}
    novel=[]; i=0
    while i<n:
        if cover[i] is None:
            j=i
            while j<n and cover[j] is None: j+=1
            if j-i>=2: novel.append(' '.join(aw[i:j]))
            i=j
        else: i+=1
    # check novel spans against prior-grade corpus
    really_novel=[]; prior_recall=[]
    for sp in novel:
        if any(sp in p for p in prior): prior_recall.append(sp)
        else:
            hit=False
            for p in prior:
                pw=p.split(); sw=sp.split()
                for k in range(len(pw)-2):
                    if ' '.join(pw[k:k+3]) in sp: hit=True; break
                if hit: break
            (prior_recall if hit else really_novel).append(sp)
    novel=really_novel
    longest=0
    for c in set(c for c in cover if c): longest=max(longest,c[1]-c[0])
    kind='RECALL' if len(srcs)<=1 and not novel else ('SPLICE' if len(srcs)>1 and not novel else 'COMPOSED')
    return {'kind':kind,'sources':len(srcs),'longest_run':longest,'novel':novel}
for line in open('answers.log'):
    r=json.loads(line); g=grade(r['q'],r['a'])
    print(f"[{g['kind']}] srcs={g['sources']} run={g['longest_run']}  Q:{r['q'][:30]}")
    if g['novel']: print(f"   TRULY novel: {g['novel']}")
