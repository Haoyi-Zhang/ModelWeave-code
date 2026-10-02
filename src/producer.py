"""Untrusted compiler and bounded certificate producer.

All input traces are finite. Search is exhaustive over at most twelve aspect bits.
Certificates are checked separately by checker.py, which imports no project code.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from typing import Any
from engine import Case, Invalid, first_failure, replay, tick

@dataclass(frozen=True)
class Clause:
    off_literal: int  # A clause is (OR not X_b for b in this mask) OR positive literals.
    on_literal: int
    event: int
    cell: int

    def holds(self, mask: int) -> bool:
        tick('clause_tests')
        return bool(self.off_literal & ~mask or self.on_literal & mask)

    @property
    def size(self) -> int:
        return self.off_literal.bit_count()+self.on_literal.bit_count()


def local_profile(case: Case, at: int, cell: int) -> list[Clause]:
    reader=case.events[at]; wanted=dict(reader.guard)[cell]
    anchor=-1; base=case.base[cell]
    for j,e in enumerate(case.events[:at]):
        tick('profile_prefix_events')
        w=dict(e.write)
        if e.tag==reader.tag and cell in w:
            anchor=j;base=w[cell]
    last={}
    for j in range(anchor+1,at):
        e=case.events[j];w=dict(e.write)
        if e.tag!=reader.tag and cell in w:
            last[e.tag]=(j,w[cell])
    writers=sorted((j,a,v) for a,(j,v) in last.items())
    goods=[(j,a) for j,a,v in writers if v in wanted]
    good_mask=sum(1<<a for _,a in goods)
    r=1<<reader.tag; result=[]
    base_bad=base not in wanted
    if base_bad:
        result.append(Clause(r,good_mask,at,cell))
    for j,a,v in writers:
        if v not in wanted:
            later=sum(1<<b for k,b in goods if k>j)
            # These, and only these, clauses are subsumed by the base clause.
            if base_bad and later==good_mask:
                continue
            result.append(Clause(r|(1<<a),later,at,cell))
    return result


def compile_trace(case: Case) -> list[Clause]:
    return [c for i,e in enumerate(case.events) for x,_ in e.guard
            for c in local_profile(case,i,x)]


def admissible(compiled: list[Clause], mask: int) -> bool:
    return all(c.holds(mask) for c in compiled)


def raw_cuts(case: Case) -> list[tuple[int,int,int,int,int]]:
    """Non-normalized sufficient cuts, used only to justify refutation leaves.

    Tuple: forced-on, forced-off, reader index, cell, bad source index (-1=base).
    Repeated aspect tags can make a raw cut inconsistent. Such cuts are omitted.
    """
    cuts=[]
    for i,reader in enumerate(case.events):
        for x,allowed in reader.guard:
            writers=[(j,e.tag,dict(e.write)[x]) for j,e in enumerate(case.events[:i]) if x in dict(e.write)]
            sources=[(-1,None,case.base[x])]+writers
            for j,a,v in sources:
                if v in allowed:continue
                on=(1<<reader.tag)|(0 if a is None else 1<<a)
                off=0
                for k,b,w in writers:
                    if k>j and w in allowed:off|=1<<b
                if not on&off:cuts.append((on,off,i,x,j))
    return cuts


def refutation(case: Case, on: int, off: int, *, budget: int | None=None,
               optional: int=0, cuts: list[tuple[int,int,int,int,int]] | None=None) -> dict[str,Any]:
    if on&off or (on|off)&~case.full:
        raise Invalid('inconsistent proof root')
    cuts=raw_cuts(case) if cuts is None else cuts
    nodes=0
    def visit(yes: int,no: int) -> dict[str,Any]:
        nonlocal nodes
        nodes+=1;tick('produced_proof_nodes')
        if nodes>10000:raise Invalid('proof exceeds node budget')
        if budget is not None and (no&optional).bit_count()>budget:
            return {'cost':True}
        for p,n,i,x,j in cuts:
            if p&yes==p and n&no==n:
                return {'cut':[i,x,j]}
        remaining=case.full&~(yes|no)
        if not remaining:
            raise Invalid('attempted to refute a successful completion')
        bit=remaining&-remaining;a=bit.bit_length()-1
        return {'split':a,'zero':visit(yes,no|bit),'one':visit(yes|bit,no)}
    return visit(on,off)


def local_obstruction(case: Case, mask: int) -> dict[str,Any]:
    failed=first_failure(case,mask)
    if failed is None:raise Invalid('a valid mask has no failed observation')
    i,x=failed
    bad=[c for c in local_profile(case,i,x) if not c.holds(mask)]
    if not bad:raise Invalid('compiler omitted a failed observation')
    c=min(bad,key=lambda c:(c.size,c.off_literal,c.on_literal))
    return {'kind':'local','mask':mask,'event':i,'cell':x,
            'on':c.off_literal,'off':c.on_literal}


def matches(mask: int,on: int,off: int) -> bool:
    return mask&on==on and not mask&off


def solve(case: Case,on: int,off: int) -> dict[str,Any]:
    """Optimal unit-cost completion, or a cardinality-minimum conflicting subpolicy."""
    if type(on) is not int or type(off) is not int or min(on,off)<0 or (on|off)&~case.full or on&off:
        raise Invalid('policy must contain disjoint, in-range masks')
    compiled=compile_trace(case)
    valid=[m for m in range(case.full+1) if admissible(compiled,m)]
    allowed=[m for m in valid if matches(m,on,off)]
    optional=case.full&~(on|off)
    cuts=raw_cuts(case)
    if allowed:
        mask=min(allowed,key=lambda m:((optional&~m).bit_count(),m))
        cost=(optional&~mask).bit_count()
        outcome=replay(case,mask)
        if outcome is None:raise Invalid('compiler returned a non-executable mask')
        proof=refutation(case,on,off,budget=cost-1,optional=optional,cuts=cuts)
        return {'kind':'optimal','on':on,'off':off,'cost':cost,
                'outcome':outcome,'proof':proof}
    facts=[(i,1 if on>>i&1 else 0) for i in range(case.aspects) if (on|off)>>i&1]
    def masks(items: tuple[tuple[int,int], ...] | list[tuple[int,int]]) -> tuple[int,int]:
        return (sum(1<<i for i,v in items if v),sum(1<<i for i,v in items if not v))
    core=None
    for k in range(1,len(facts)+1):
        for sub in combinations(facts,k):
            p,n=masks(sub)
            if not any(matches(v,p,n) for v in valid):
                core=(p,n,k);break
        if core is not None:break
    if core is None:raise Invalid('failed to locate a conflicting subpolicy')
    p,n,k=core; witnesses=[]
    for sub in combinations(facts,k-1):
        a,b=masks(sub)
        witness=next((v for v in valid if matches(v,a,b)),None)
        if witness is None:raise Invalid('claimed minimum core is not minimum')
        witnesses.append({'on':a,'off':b,'mask':witness})
    return {'kind':'infeasible','on':on,'off':off,'core_on':p,'core_off':n,
            'proof':refutation(case,p,n,cuts=cuts),'witnesses':witnesses}
