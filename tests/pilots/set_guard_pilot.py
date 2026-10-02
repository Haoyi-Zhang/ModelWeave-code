"""Exact truth-table checks for unary set observations and the SAT reduction.
A second bounded pilot; it is not a general mechanized proof.
"""
from itertools import product
import random, json, time, resource

def cs(initial, tr, i, x):
    a,g,_=tr[i]; allowed=g[x]; anchor=-1; base=initial[x]
    for j,(b,_,w) in enumerate(tr[:i]):
        if b==a and x in w: anchor=j; base=w[x]
    last={}
    for j in range(anchor+1,i):
        b,_,w=tr[j]
        if b!=a and x in w: last[b]=(j,w[x])
    writers=sorted((j,b,v) for b,(j,v) in last.items())
    goods=[(j,b) for j,b,v in writers if v in allowed]
    out=[]
    if base not in allowed: out.append((frozenset([a]),frozenset(b for _,b in goods)))
    for j,b,v in writers:
        if v not in allowed:out.append((frozenset([a,b]),frozenset(c for k,c in goods if k>j)))
    return set(c for c in out if not any(d!=c and d[0]<=c[0] and d[1]<=c[1] for d in out))

def holds(c, mask):
    return any(not(mask>>b&1) for b in c[0]) or any(mask>>b&1 for b in c[1])

def ghost(base,tr,i,x,mask):
    a,g,_=tr[i]
    if not(mask>>a&1):return True
    v=base[x]
    for b,_,w in tr[:i]:
        if mask>>b&1 and x in w:v=w[x]
    return v in g[x]

def run(base,tr,mask):
    s=dict(base)
    for a,g,w in tr:
        if mask>>a&1:
            if any(s[x] not in v for x,v in g.items()): return False
            s.update(w)
    return True

def primes(values,m):
    out=[]
    for c in product((-1,0,1),repeat=m):
        cc=(frozenset(i for i,v in enumerate(c) if v==-1),frozenset(i for i,v in enumerate(c) if v==1))
        if all(not v or holds(cc,k) for k,v in enumerate(values)):out.append(cc)
    return set(c for c in out if not any(d!=c and d[0]<=c[0] and d[1]<=c[1] for d in out))

def sat_trace(n,formula):
    # p_i first, one reset d, n_i next, one final reader r. One event per aspect.
    d=2*n;r=d+1; initial={i:0 for i in range(2*n+len(formula))};tr=[]
    for i in range(n):
        w={i:1,n+i:1}
        for j,c in enumerate(formula):
            if i+1 in c:w[2*n+j]=1
        tr.append((i,{},w))
    tr.append((d,{},dict.fromkeys(range(n),0)))
    for i in range(n):
        w={n+i:1}
        for j,c in enumerate(formula):
            if -(i+1) in c:w[2*n+j]=1
        tr.append((n+i,{i:{0}},w))
    tr.append((r,{i:{1} for i in range(n,2*n+len(formula))},{}))
    return initial,tr,d,r

def main():
    t0=time.process_time(); rng=random.Random(716421); observations=0; masks=0
    for cid in range(512):
        m=4; nc=3; initial={x:rng.randrange(3) for x in range(nc)};s=dict(initial);tr=[]
        for i in range(8):
            a=rng.randrange(m);g={};w={}
            for x in range(nc):
                if rng.random()<.55:g[x]={s[x]}|{v for v in range(3) if rng.random()<.5}
                if rng.random()<.45:w[x]=rng.randrange(3)
            tr.append((a,g,w));s.update(w)
        allcs=[]
        for i,(_,g,_) in enumerate(tr):
            for x in g:
                c=cs(initial,tr,i,x)
                vals=[ghost(initial,tr,i,x,k) for k in range(1<<m)]
                assert c==primes(vals,m),(cid,i,x,c,primes(vals,m))
                observations+=1;allcs.extend(c)
        for mask in range(1<<m):
            assert run(initial,tr,mask)==all(holds(c,mask) for c in allcs)
            masks+=1
    sat_cases=0; completions=0
    for n in range(1,5):
        for j in range(32):
            formula=[tuple((1 if rng.randrange(2) else -1)*(1+rng.randrange(n)) for _ in range(3)) for __ in range(1+j%8)]
            initial,tr,d,r=sat_trace(n,formula)
            assert run(initial,tr,(1<<(2*n+2))-1)
            expected=any(all(any((bits>>(abs(l)-1)&1)==(l>0) for l in c) for c in formula) for bits in range(1<<n))
            found=False
            for bits in range(1<<(2*n)):
                ok=run(initial,tr,bits|(1<<r));completions+=1
                if ok:
                    assert all(bool(bits>>i&1)^bool(bits>>(n+i)&1) for i in range(n))
                    found=True
            assert expected==found
            sat_cases+=1
    # Explicit local/global gap: each local prime has 3 literals; global prime has 2.
    base={0:0,1:0};tr=[(0,{}, {0:1,1:1}),(1,{}, {0:1,1:0}),(2,{0:{1},1:{0}}, {})]
    assert [len(n)+len(p) for x in (0,1) for n,p in cs(base,tr,2,x)]==[3,3]
    assert all(run(base,tr,k)==(not(k&4) or bool(k&2)) for k in range(8))
    print(json.dumps(dict(random_traces=512,observations=observations,masks=masks,prime_equality_checks=observations,SAT_gadget_cases=sat_cases,policy_completions=completions,local_global_gap=True,unary_guard_domain=3,seed=716421,cpu_seconds=time.process_time()-t0,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,status='finite_checks_passed_not_mechanized_general_proof'),indent=2))
if __name__=='__main__':main()
