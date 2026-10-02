"""Deterministic, original finite inputs; no external datasets or services."""
from __future__ import annotations
import random
from typing import Any, Iterator

def make(base: list[int],events: list[dict[str,Any]],m: int,domains: list[int] | None=None,
         nodes: list[int] | None=None,edges: list[list[int]] | None=None) -> dict[str,Any]:
    return {'domains':domains or [max(2,max(base,default=0)+1)]*len(base),
            'nodes':nodes or [],'edges':edges or [],'base':base,
            'aspects':m,'events':events}

def ev(a: int,g: dict[int,list[int]],w: dict[int,int]) -> dict[str,Any]:
    return {'tag':a,'guard':[[x,sorted(s)] for x,s in sorted(g.items())],
            'write':[[x,v] for x,v in sorted(w.items())]}

def tiny() -> Iterator[dict[str,Any]]:
    for initial in (0,1):
        def visit(events: list[dict[str,Any]],x: int) -> Iterator[dict[str,Any]]:
            yield make([initial],events,3,[2])
            if len(events)==3:return
            for a in range(3):
                for guard in ({},{0:[x]}):
                    for value in (None,0,1):
                        e=ev(a,guard,{} if value is None else {0:value})
                        yield from visit(events+[e],x if value is None else value)
        yield from visit([],initial)

def scalar(seed: int, m: int=3, cells: int=3, length: int=6, domain: int=3) -> dict[str,Any]:
    rng=random.Random(seed);base=[rng.randrange(domain) for _ in range(cells)];s=base[:];events=[]
    for i in range(length):
        a=rng.randrange(m);g={};w={}
        for x in range(cells):
            if rng.random()<.45:
                g[x]=sorted({s[x]}|{v for v in range(domain) if rng.random()<.35})
            if rng.random()<.4:w[x]=rng.randrange(domain)
        events.append(ev(a,g,w))
        for x,v in w.items():s[x]=v
    return make(base,events,m,[domain]*cells)

def graph(seed: int,m: int=12,nodes_count: int=64,edges_count: int=192,length: int=96) -> dict[str,Any]:
    rng=random.Random(seed);ns=list(range(nodes_count));es=[]
    for k in range(edges_count):es.append([nodes_count+k,rng.randrange(nodes_count),rng.randrange(nodes_count)])
    attr_start=nodes_count+edges_count
    ds=[2]*attr_start+[4]*nodes_count
    base=[int(rng.random()<.75) for _ in ns]
    base += [int(base[a] and base[b] and rng.random()<.3) for _,a,b in es]
    base += [rng.randrange(4) for _ in ns]
    s=base[:];events=[]
    for i in range(length):
        a=i%m if i<m else rng.randrange(m);g={};w={};kind=rng.randrange(5)
        if kind==0:
            x=attr_start+rng.randrange(nodes_count)
            if rng.random()<.7:g[x]=sorted({s[x],rng.randrange(4)})
            w[x]=rng.randrange(4)
        elif kind==1:
            c,u,v=rng.choice(es);w[c]=1
            # Activate missing endpoints in this same atomic event.
            for n in (u,v):
                if not s[n]:w[n]=1
                else:g[n]=[1]
        elif kind==2:
            c,_,_=rng.choice(es);w[c]=0
        elif kind==3:
            n=rng.randrange(nodes_count);w[n]=1
        else:
            n=rng.randrange(nodes_count);w[n]=0
            for c,u,v in es:
                if n==u or n==v:w[c]=0
        events.append(ev(a,g,w))
        for x,v in w.items():s[x]=v
    return make(base,events,m,ds,ns,es)

def sat_gadget(n: int,formula: list[list[int]]) -> tuple[dict[str,Any],int,int]:
    if not 1<=n<=5 or any(not c or any(type(l) is not int or not 1<=abs(l)<=n for l in c) for c in formula):
        raise ValueError('invalid bounded SAT formula')
    base=[0]*(2*n+len(formula));events=[];d=2*n;r=d+1
    for i in range(n):
        w={i:1,n+i:1}
        for j,c in enumerate(formula):
            if i+1 in c:w[2*n+j]=1
        events.append(ev(i,{},w))
    events.append(ev(d,{},dict.fromkeys(range(n),0)))
    for i in range(n):
        w={n+i:1}
        for j,c in enumerate(formula):
            if -(i+1) in c:w[2*n+j]=1
        events.append(ev(n+i,{i:[0]},w))
    events.append(ev(r,dict.fromkeys(range(n,2*n+len(formula)),[1]),{}))
    return make(base,events,2*n+2,[2]*len(base)),1<<r,1<<d

def cover_gadget(n: int,edges: list[tuple[int,int]]) -> tuple[dict[str,Any],int,int]:
    if not 1<=n<=6 or not edges or any(not(0<=a<b<n) for a,b in edges):raise ValueError('invalid graph')
    events=[]
    for v in range(n):
        g={k:[0] for k,(a,b) in enumerate(edges) if b==v}
        w={k:1 for k,(a,b) in enumerate(edges) if a==v}
        events.append(ev(v,g,w))
        events.append(ev(n+v,{},dict.fromkeys(w,0)))
    return make([0]*len(edges),events,2*n,[2]*len(edges)),0,((1<<n)-1)<<n

def named() -> dict[str,dict[str,Any]]:
    return {
      'replacement':make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:1}),ev(2,{0:[1]}, {})],3,[2]),
      'inhibitor':make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:0}),ev(2,{0:[0]}, {})],3,[2]),
      'stale_complement':make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:2})],2,[3]),
      'local_global_gap':make([0,0],[ev(0,{}, {0:1,1:1}),ev(1,{}, {0:1,1:0}),ev(2,{0:[1],1:[0]}, {})],3,[2,2]),
      'repeated_mixed_tag':make([0],[ev(0,{}, {0:1}),ev(0,{}, {0:0}),ev(1,{}, {0:1}),ev(2,{0:[1]}, {})],3,[2]),
      'unary_not_exact':make([1],[ev(0,{}, {0:2}),ev(1,{0:[1,2]}, {})],2,[3]),
      'observation_exact':make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:0}),ev(2,{0:[0]}, {})],3,[2]),
      'observation_weak':make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:0}),ev(2,{0:[0,1]}, {})],3,[2]),
      'order_left':make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:0}),ev(2,{}, {0:1}),ev(3,{}, {0:0}),ev(4,{0:[0]}, {})],5,[2]),
      'order_right':make([0],[ev(2,{}, {0:1}),ev(3,{}, {0:0}),ev(0,{}, {0:1}),ev(1,{}, {0:0}),ev(4,{0:[0]}, {})],5,[2]),
      'idempotent_delta':make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:1})],2,[2])
    }
