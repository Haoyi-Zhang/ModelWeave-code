"""Independent executable certificate checker for the documented finite calculus.

No producer, compiler, oracle, or engine module is imported. This is a separate
implementation, not an independently authored review or a mechanized general proof.
The only imports are Python standard-library modules.
"""
from __future__ import annotations
from itertools import combinations
from typing import Any

COUNTS: dict[str,int] = {}

def count(name: str, amount: int=1) -> None:
    COUNTS[name]=COUNTS.get(name,0)+amount

class Rejected(ValueError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:raise Rejected(message)

def num(v: Any, lo: int, hi: int) -> bool:
    return type(v) is int and lo<=v<=hi

def fields(v: Any, keys: set[str]) -> None:
    require(type(v) is dict and set(v)==keys,'unexpected or missing fields')

def _state(ds: list[int], edges: list[list[int]], s: Any) -> None:
    require(type(s) is list and len(s)==len(ds),'state length/type')
    for d,v in zip(ds,s):
        count('value_checks');require(num(v,0,d-1),'state value outside domain')
    for e,a,b in edges:
        count('edge_checks');require(s[e]==0 or (s[a]==1 and s[b]==1),'dangling edge')

def _case(raw: Any) -> tuple[Any,...]:
    fields(raw,{'domains','nodes','edges','base','aspects','events'})
    ds=raw['domains'];ns=raw['nodes'];es=raw['edges'];m=raw['aspects'];base=raw['base'];rs=raw['events']
    require(type(ds) is list and 1<=len(ds)<=512,'cell count')
    require(all(num(d,1,256) for d in ds),'domain size')
    require(type(ns) is list and len(ns)<=64,'node count')
    require(all(num(n,0,len(ds)-1) and ds[n]==2 for n in ns),'node type')
    require(len(set(ns))==len(ns),'duplicate node cell')
    require(type(es) is list and len(es)<=192,'edge count')
    occupied=set(ns)
    for e in es:
        require(type(e) is list and len(e)==3 and all(type(v) is int for v in e),'edge fields')
        c,a,b=e
        require(num(c,0,len(ds)-1) and ds[c]==2 and c not in occupied and a in ns and b in ns,'edge typing')
        occupied.add(c)
    _state(ds,es,base)
    require(num(m,0,12),'aspect count')
    require(type(rs) is list and len(rs)<=96,'event count')
    incidence=[set() for _ in ds]
    for eid,(e,a,b) in enumerate(es):
        for x in {e,a,b}:
            count('schema_index_entries');incidence[x].add(eid)
    ev=[]
    for r in rs:
        fields(r,{'tag','guard','write'});require(num(r['tag'],0,m-1),'tag')
        require(type(r['guard']) is list and type(r['write']) is list,'event maps')
        g={};w={}
        for z in r['guard']:
            require(type(z) is list and len(z)==2,'guard pair')
            x,s=z
            require(num(x,0,len(ds)-1) and x not in g,'guard cell')
            require(type(s) is list and bool(s),'guard set')
            require(all(num(v,0,ds[x]-1) for v in s),'guard domain')
            require(len(set(s))==len(s),'duplicate guard value')
            g[x]=frozenset(s)
        for z in r['write']:
            require(type(z) is list and len(z)==2,'write pair')
            x,v=z
            require(num(x,0,len(ds)-1) and x not in w,'write cell')
            require(num(v,0,ds[x]-1),'write domain');w[x]=v
        # A changed incidence must have a definitely absent edge or a definitely
        # present endpoint. Unchanged incidences inherit the input invariant.
        affected=set()
        for x in w:affected.update(incidence[x])
        for eid in sorted(affected):
            e,a,b=es[eid]
            for n in {a,b}:
                if e not in w and n not in w:continue
                count('static_edge_checks')
                edge_zero=(w[e]==0) if e in w else g.get(e)==frozenset((0,))
                node_one=(w[n]==1) if n in w else g.get(n)==frozenset((1,))
                require(edge_zero or node_one,'event is outside the typed fragment')
        ev.append((r['tag'],g,w))
    c=(ds,es,list(base),m,ev)
    require(_execute(c,(1<<m)-1) is not None,'original trace fails')
    return c

def _execute(c: tuple[Any,...], mask: int) -> list[int] | None:
    ds,es,base,m,ev=c;s=list(base)
    for a,g,w in ev:
        count('event_visits')
        if mask&(1<<a):
            for x,allowed in g.items():
                count('guard_tests')
                if s[x] not in allowed:return None
            for x,v in w.items():count('write_updates');s[x]=v
    return s

def _mask(c: tuple[Any,...], v: Any) -> None:
    require(num(v,0,(1<<c[3])-1),'mask is not an in-range integer')

def _policy(c: tuple[Any,...], on: Any, off: Any) -> None:
    _mask(c,on);_mask(c,off);require(not on&off,'contradictory policy')

def _inferred(ds: list[int], g: dict[int,frozenset[int]], x: int) -> int | None:
    if x in g and len(g[x])==1:return next(iter(g[x]))
    if ds[x]==1:return 0
    return None

def _outcome(c: tuple[Any,...], out: Any) -> int:
    fields(out,{'mask','end','receipts'})
    ds,es,base,m,ev=c;mask=out['mask'];_mask(c,mask)
    receipts=out['receipts'];require(type(receipts) is list,'receipt list')
    require(len(receipts)==sum(bool(mask&(1<<a)) for a,_,_ in ev),'receipt count')
    s=list(base);k=0;checked=[]
    for i,(a,g,w) in enumerate(ev):
        count('outcome_event_visits')
        if not mask&(1<<a):continue
        for x,allowed in g.items():
            count('guard_tests');require(s[x] in allowed,'retained observation fails')
        r=receipts[k];k+=1;fields(r,{'at','old'})
        require(type(r['at']) is int and r['at']==i,'receipt event/order')
        require(type(r['old']) is list,'complement list');old={}
        for z in r['old']:
            require(type(z) is list and len(z)==2,'complement pair');x,v=z
            require(num(x,0,len(ds)-1) and x not in old and num(v,0,ds[x]-1),'complement value')
            old[x]=v
        needed={x for x in w if _inferred(ds,g,x) is None}
        require(set(old)==needed,'complement domain must be exact')
        for x in needed:require(old[x]==s[x],'stale or forged complement')
        for x,v in w.items():count('write_updates');s[x]=v
        checked.append((i,old))
    _state(ds,es,out['end']);require(s==out['end'],'reported final state differs')
    # A second direction checks the operational round trip of the accepted receipt.
    back=list(out['end'])
    for i,old in reversed(checked):
        count('inverse_event_visits');a,g,w=ev[i]
        for x,v in w.items():require(back[x]==v,'inverse postcondition')
        for x in w:
            val=_inferred(ds,g,x);back[x]=old[x] if val is None else val
        require(all(back[x] in allowed for x,allowed in g.items()),'inverse observation')
    require(back==base,'round trip does not recover the base')
    return mask

def _cut(c: tuple[Any,...], leaf: Any, yes: int, no: int) -> None:
    ds,es,base,m,ev=c
    require(type(leaf) is list and len(leaf)==3 and all(type(x) is int for x in leaf),'cut fields')
    i,x,j=leaf
    require(0<=i<len(ev) and x in ev[i][1] and -1<=j<i,'cut index')
    a,g,_=ev[i];allowed=g[x]
    require(bool(yes&(1<<a)),'cut reader is not forced present')
    if j==-1:value=base[x]
    else:
        b,_,w=ev[j];require(x in w and bool(yes&(1<<b)),'bad source is not forced present');value=w[x]
    require(value not in allowed,'cut source satisfies the observation')
    for b,_,w in ev[j+1:i]:
        count('cut_prefix_events')
        if x in w and w[x] in allowed:
            require(bool(no&(1<<b)),'a later repairing writer is not forced absent')

def _proof(c: tuple[Any,...], proof: Any, on: int, off: int,
           budget: int | None=None, optional: int=0) -> int:
    nodes=0
    def visit(p: Any,yes: int,no: int,depth: int) -> None:
        nonlocal nodes
        nodes+=1;count('checked_proof_nodes')
        require(nodes<=10000 and depth<=c[3],'proof budget/depth')
        require(type(p) is dict,'proof node')
        if set(p)=={'cut'}:_cut(c,p['cut'],yes,no);return
        if set(p)=={'cost'}:
            require(p['cost'] is True and budget is not None,'cost leaf not authorized')
            require((no&optional).bit_count()>budget,'insufficient cost lower bound');return
        fields(p,{'split','zero','one'});a=p['split']
        require(num(a,0,c[3]-1) and not (yes|no)&(1<<a),'split variable already assigned or invalid')
        visit(p['zero'],yes,no|(1<<a),depth+1)
        visit(p['one'],yes|(1<<a),no,depth+1)
    visit(proof,on,off,0)
    return nodes

def _local(c: tuple[Any,...], cert: dict[str,Any]) -> None:
    fields(cert,{'kind','mask','event','cell','on','off'})
    mask=cert['mask'];on=cert['on'];off=cert['off'];_mask(c,mask);_policy(c,on,off)
    require(mask&on==on and not mask&off,'local facts do not describe the queried mask')
    i=cert['event'];x=cert['cell'];ds,es,base,m,ev=c
    require(num(i,0,len(ev)-1) and type(x) is int and x in ev[i][1],'local observation')
    a,g,_=ev[i];allowed=g[x];full=(1<<m)-1
    # Truth-table construction is independent of last-occurrence normalization.
    # A subset z of differing bits has a good completion iff possible[z] is true.
    possible=[False]*(1<<m)
    for k in range(1<<m):
        good=True
        if k&(1<<a):
            v=base[x]
            for b,_,w in reversed(ev[:i]):
                count('local_oracle_events')
                if k&(1<<b) and x in w:v=w[x];break
            good=v in allowed
        if good:possible[k^mask]=True
    for b in range(m):
        bit=1<<b
        for z in range(1<<m):
            count('local_subset_operations')
            if z&bit:possible[z]=possible[z] or possible[z^bit]
    facts=on|off
    require(not possible[full^facts],'local facts do not force failure')
    minimum=min(z.bit_count() for z in range(1<<m) if not possible[full^z])
    require(facts.bit_count()==minimum,'local certificate is not minimum-cardinality')

def _check(c: tuple[Any,...], cert: Any) -> dict[str,Any]:
    require(type(cert) is dict and type(cert.get('kind')) is str,'certificate kind')
    mode=cert['kind'];nodes=0
    if mode=='success':
        fields(cert,{'kind','outcome'});_outcome(c,cert['outcome'])
    elif mode=='local':_local(c,cert)
    elif mode=='optimal':
        fields(cert,{'kind','on','off','cost','outcome','proof'})
        on=cert['on'];off=cert['off'];_policy(c,on,off)
        mask=_outcome(c,cert['outcome']);require(mask&on==on and not mask&off,'outcome violates policy')
        optional=((1<<c[3])-1)&~(on|off)
        cost=(optional&~mask).bit_count()
        require(type(cert['cost']) is int and cert['cost']==cost,'collateral cost')
        nodes=_proof(c,cert['proof'],on,off,cost-1,optional)
    elif mode=='infeasible':
        fields(cert,{'kind','on','off','core_on','core_off','proof','witnesses'})
        on=cert['on'];off=cert['off'];_policy(c,on,off)
        p=cert['core_on'];n=cert['core_off'];_policy(c,p,n)
        require(p&on==p and n&off==n and p|n!=0,'core is not a nonempty subpolicy')
        nodes=_proof(c,cert['proof'],p,n)
        k=(p|n).bit_count();facts=[(b,1 if on&(1<<b) else 0) for b in range(c[3]) if (on|off)&(1<<b)]
        expected=set()
        for sub in combinations(facts,k-1):
            expected.add((sum(1<<b for b,v in sub if v),sum(1<<b for b,v in sub if not v)))
        ws=cert['witnesses'];require(type(ws) is list and len(ws)==len(expected),'missing minimality witnesses')
        require(nodes+len(ws)<=10000,'combined proof-node budget')
        seen=set()
        for w in ws:
            fields(w,{'on','off','mask'});a=w['on'];b=w['off'];_policy(c,a,b);_mask(c,w['mask'])
            require((a,b) in expected and (a,b) not in seen,'duplicate or unrelated minimality witness')
            seen.add((a,b));v=w['mask']
            require(v&a==a and not v&b and _execute(c,v) is not None,'invalid minimum-core witness')
        require(seen==expected,'incomplete cardinality-minimality coverage')
    else:raise Rejected('unsupported certificate kind')
    return {'accepted':True,'kind':mode,'proof_nodes':nodes}


def check(raw: Any, cert: Any) -> dict[str,Any]:
    """Validate a case and one certificate, without trusting producer state."""
    return _check(_case(raw),cert)

def check_many(raw: Any, certificates: Any) -> list[dict[str,Any]]:
    """One immutable input case, independently admitted once, several certificates."""
    require(type(certificates) is list and 1<=len(certificates)<=64,'certificate batch size')
    c=_case(raw)
    return [_check(c,cert) for cert in certificates]
