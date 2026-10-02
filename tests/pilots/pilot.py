"""Bounded, exact pilot for grouped last-writer normalisation.
No external packages, files, or services are consumed.
"""
from itertools import product
import time, resource, json

# Event: (aspect, optional observation, optional constant write); one Boolean cell.
def replay(initial, trace, mask):
    x=initial
    for a,g,w in trace:
        if mask>>a&1:
            if g is not None and x!=g: return False
            if w is not None: x=w
    return True

def local(initial,trace,i):
    a,v,_=trace[i]
    if v is None:return []
    anchor=-1; base=initial
    for j,(b,_,w) in enumerate(trace[:i]):
        if b==a and w is not None: anchor=j; base=w
    last={}
    for j in range(anchor+1,i):
        b,_,w=trace[j]
        if b!=a and w is not None:last[b]=(j,w)
    writers=sorted((j,b,w) for b,(j,w) in last.items())
    good=[(j,b) for j,b,w in writers if w==v]
    clauses=[]
    if base!=v:
        clauses.append((frozenset([a]),frozenset(b for _,b in good)))
    for j,b,w in writers:
        if w!=v:
            clauses.append((frozenset([a,b]),frozenset(c for k,c in good if k>j)))
    # Clause=(negative variables, positive variables), disjoint after normalisation.
    return [c for c in clauses if not any(d!=c and d[0]<=c[0] and d[1]<=c[1] for d in clauses)]

def sat(c,mask):
    n,p=c
    return any(not (mask>>v&1) for v in n) or any(mask>>v&1 for v in p)

def observe_ghost(initial,trace,i,mask):
    a,g,_=trace[i]
    if not(mask>>a&1): return True
    x=initial
    for b,_,w in trace[:i]:
        if mask>>b&1 and w is not None: x=w
    return x==g

def all_primes(values,m):
    """Independent truth-table oracle: all ternary clauses, no algebraic normalisation."""
    out=[]
    for signs in product((-1,0,1), repeat=m):
        n=frozenset(i for i,s in enumerate(signs) if s==-1)
        p=frozenset(i for i,s in enumerate(signs) if s==1)
        c=(n,p)
        if all(not values[k] or sat(c,k) for k in range(1<<m)):
            out.append(c)
    return set(c for c in out if not any(d!=c and d[0]<=c[0] and d[1]<=c[1] for d in out))

def valid_traces(initial,m,maxlen):
    def rec(t,x):
        yield tuple(t)
        if len(t)==maxlen:return
        for a in range(m):
            for g in (None,x):
                for w in (None,0,1):
                    yield from rec(t+[(a,g,w)], x if w is None else w)
    return rec([],initial)

def main():
    t0=time.process_time();w0=time.perf_counter(); counts=dict(traces=0,masks=0,local_observations=0,prime_checks=0)
    for initial in (0,1):
        for trace in valid_traces(initial,3,3):
            cs=[c for i in range(len(trace)) for c in local(initial,trace,i)]
            for mask in range(8):
                assert replay(initial,trace,mask)==all(sat(c,mask) for c in cs), (initial,trace,mask,cs)
                counts['masks']+=1
            for i,(_,g,_) in enumerate(trace):
                if g is None:continue
                values=[observe_ghost(initial,trace,i,k) for k in range(8)]
                assert set(local(initial,trace,i))==all_primes(values,3),(initial,trace,i,local(initial,trace,i),all_primes(values,3))
                counts['local_observations']+=1;counts['prime_checks']+=1
            counts['traces']+=1
    # Negative controls: disjunctive replacement and a non-monotone valid family.
    replacement=(0,[(0,None,1),(1,None,1),(2,1,None)])
    # Last-writer provenance says keep aspect 1, but mask 101 uses aspect 0 instead.
    assert replay(*replacement,0b101)
    inhibition=(0,[(0,None,1),(1,None,0),(2,0,None)])
    assert replay(*inhibition,0b100) and not replay(*inhibition,0b101) and replay(*inhibition,0b111)
    # Stale undo complement after erasure would restore 1 rather than base 0.
    stale=(0,[(0,None,1),(1,None,2)])
    # This final check uses a 3-valued cell, outside the Boolean enumeration.
    assert replay(*stale,0b10)
    counts.update(cpu_seconds=time.process_time()-t0, wall_seconds=time.perf_counter()-w0, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      negative_controls={'provider_switch':True,'inhibitor_nonmonotonicity':True,'stale_complement':True},
      enumeration={'initial_values':2,'aspect_labels':3,'max_events':3,'valid_options_per_step':18,'masks_per_trace':8},
      status='finite_checks_passed_not_mechanized_general_proof')
    print(json.dumps(counts,indent=2))
if __name__=='__main__':main()
