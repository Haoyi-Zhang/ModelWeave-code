"""Producer-side semantics for finite, observation-stable weaving traces.

The checker does not import this module. Values are finite-domain integer codes;
an observation is membership in an explicitly listed, nonempty unary set.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from functools import cached_property

LIMIT_ASPECTS = 12
LIMIT_EVENTS = 96
LIMIT_CELLS = 512
COUNTS: dict[str, int] = {}

def tick(name: str, amount: int = 1) -> None:
    COUNTS[name] = COUNTS.get(name, 0) + amount

class Invalid(ValueError):
    pass

@dataclass(frozen=True)
class Event:
    tag: int
    guard: tuple[tuple[int, tuple[int, ...]], ...]
    write: tuple[tuple[int, int], ...]

@dataclass(frozen=True)
class Case:
    domains: tuple[int, ...]
    nodes: tuple[int, ...]
    edges: tuple[tuple[int, int, int], ...]
    base: tuple[int, ...]
    aspects: int
    events: tuple[Event, ...]

    def to_dict(self) -> dict[str, Any]:
        return {'domains': list(self.domains), 'nodes': list(self.nodes),
                'edges': [list(e) for e in self.edges], 'base': list(self.base),
                'aspects': self.aspects, 'events': [
                    {'tag': e.tag, 'guard': [[x, list(s)] for x, s in e.guard],
                     'write': [list(w) for w in e.write]} for e in self.events]}

    @cached_property
    def incidence(self) -> tuple[tuple[tuple[int,int], ...], ...]:
        index: list[set[tuple[int,int]]] = [set() for _ in self.domains]
        for e,s,t in self.edges:
            for n in (s,t):
                tick('schema_index_entries',2)
                index[e].add((e,n));index[n].add((e,n))
        return tuple(tuple(sorted(v)) for v in index)

    @property
    def full(self) -> int:
        return (1 << self.aspects) - 1

def integer(x: Any, lo: int, hi: int) -> bool:
    return type(x) is int and lo <= x <= hi

def mask_ok(case: Case, mask: int) -> bool:
    return integer(mask, 0, case.full)

def state_ok(case: Case, state: tuple[int, ...] | list[int]) -> bool:
    if len(state) != len(case.domains):
        return False
    tick('value_checks', len(state))
    if any(not integer(v, 0, d - 1) for v, d in zip(state, case.domains)):
        return False
    for e, s, t in case.edges:
        tick('edge_checks')
        if state[e] and not (state[s] and state[t]):
            return False
    return True

def statically_safe(case: Case, event: Event) -> bool:
    """Sufficient, deliberately not complete, graph-preservation typing rule."""
    g = dict(event.guard); w = dict(event.write)
    affected={p for x in w for p in case.incidence[x]}
    for e,n in sorted(affected):
        tick('static_edge_checks')
        if w.get(e) == 0 or w.get(n) == 1:
            continue
        if e in w and n in w:
            return False
        if e in w and g.get(n) != (1,):
            return False
        if n in w and g.get(e) != (0,):
            return False
    return True

def parse_case(obj: Any, *, original: bool = True) -> Case:
    if type(obj) is not dict or set(obj) != {'domains','nodes','edges','base','aspects','events'}:
        raise Invalid('case fields must match the documented finite schema')
    ds = obj['domains']; ns = obj['nodes']; es = obj['edges']; base = obj['base']
    m = obj['aspects']; raw = obj['events']
    if type(ds) is not list or not 1 <= len(ds) <= LIMIT_CELLS or any(not integer(d,1,256) for d in ds):
        raise Invalid('invalid cell domains')
    if type(ns) is not list or len(ns)>64 or any(not integer(n,0,len(ds)-1) or ds[n]!=2 for n in ns) or len(set(ns))!=len(ns):
        raise Invalid('invalid node-presence cells')
    if type(es) is not list or len(es)>192:
        raise Invalid('invalid edge catalog')
    seen=set(ns); parsed_edges=[]
    for e in es:
        if type(e) is not list or len(e)!=3 or any(type(x) is not int for x in e):
            raise Invalid('malformed edge')
        c,s,t=e
        if not integer(c,0,len(ds)-1) or ds[c]!=2 or c in seen or s not in ns or t not in ns:
            raise Invalid('edge catalog is not typed')
        seen.add(c); parsed_edges.append(tuple(e))
    if type(base) is not list or not integer(m,0,LIMIT_ASPECTS) or type(raw) is not list or len(raw)>LIMIT_EVENTS:
        raise Invalid('invalid base, aspect count, or event count')
    ev=[]
    for r in raw:
        if type(r) is not dict or set(r)!={'tag','guard','write'} or not integer(r['tag'],0,m-1):
            raise Invalid('invalid event or tag')
        g=[]; w=[]; gs=set(); ws=set()
        if type(r['guard']) is not list or type(r['write']) is not list:
            raise Invalid('event maps must be pair lists')
        for z in r['guard']:
            if type(z) is not list or len(z)!=2:
                raise Invalid('malformed observation')
            x, allowed=z
            if not integer(x,0,len(ds)-1) or x in gs or type(allowed) is not list or not allowed or any(not integer(v,0,ds[x]-1) for v in allowed) or len(set(allowed))!=len(allowed):
                raise Invalid('invalid unary observation')
            gs.add(x);g.append((x,tuple(sorted(allowed))))
        for z in r['write']:
            if type(z) is not list or len(z)!=2:
                raise Invalid('malformed overwrite')
            x,v=z
            if not integer(x,0,len(ds)-1) or x in ws or not integer(v,0,ds[x]-1):
                raise Invalid('invalid overwrite')
            ws.add(x);w.append((x,v))
        ev.append(Event(r['tag'],tuple(sorted(g)),tuple(sorted(w))))
    c=Case(tuple(ds),tuple(ns),tuple(parsed_edges),tuple(base),m,tuple(ev))
    if not state_ok(c, c.base) or not all(statically_safe(c,e) for e in c.events):
        raise Invalid('base or event violates graph typing')
    if original and replay(c,c.full) is None:
        raise Invalid('the supplied original trace is not executable')
    return c

def inferred_old(case: Case, event: Event, x: int) -> int | None:
    allowed=dict(event.guard).get(x)
    if allowed is not None and len(allowed)==1:
        return allowed[0]
    if case.domains[x]==1:
        return 0
    return None

def replay(case: Case, mask: int) -> dict[str, Any] | None:
    if not mask_ok(case,mask):
        raise Invalid('invalid retention mask')
    state=list(case.base); receipts=[]
    for i,event in enumerate(case.events):
        tick('event_visits')
        if not mask>>event.tag&1:
            continue
        for x,allowed in event.guard:
            tick('guard_tests')
            if state[x] not in allowed:
                return None
        old=[]
        for x,v in event.write:
            tick('write_updates')
            if inferred_old(case,event,x) is None:
                old.append([x,state[x]])
        for x,v in event.write:
            state[x]=v
        receipts.append({'at':i,'old':old})
    return {'mask':mask,'end':state,'receipts':receipts}

def reverse(case: Case, outcome: dict[str, Any]) -> tuple[int, ...]:
    state=list(outcome['end'])
    for r in reversed(outcome['receipts']):
        tick('inverse_event_visits')
        event=case.events[r['at']]; old=dict(r['old'])
        for x,v in event.write:
            if state[x]!=v:
                raise Invalid('inverse postcondition failed')
        for x,_ in event.write:
            value=inferred_old(case,event,x)
            state[x]=old[x] if value is None else value
        if any(state[x] not in allowed for x,allowed in event.guard):
            raise Invalid('inverse observation failed')
    return tuple(state)

def first_failure(case: Case, mask: int) -> tuple[int,int] | None:
    s=list(case.base)
    for i,e in enumerate(case.events):
        tick('failure_scan_events')
        if mask>>e.tag&1:
            for x,a in e.guard:
                if s[x] not in a:
                    return i,x
            for x,v in e.write:s[x]=v
    return None

def independent(left: Event, right: Event) -> bool:
    lw={x for x,_ in left.write};rw={x for x,_ in right.write}
    lr={x for x,_ in left.guard};rr={x for x,_ in right.guard}
    return not(lw&(rw|rr) or rw&(lw|lr))
