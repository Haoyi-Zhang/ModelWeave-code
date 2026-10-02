"""Transparent information-ablation baselines, not ports of external tools."""
from typing import Any
COUNTS: dict[str,int]={}
def tick(k: str,n: int=1) -> None:COUNTS[k]=COUNTS.get(k,0)+n

def prepare(raw: dict[str,Any]) -> dict[str,Any]:
    state=raw['base'][:];old=[];deltas=[];sources={};edges=set()
    for event in raw['events']:
        tick('baseline_prepare_events');a=event['tag']
        for x,_ in event['guard']:
            if x in sources and sources[x]!=a:edges.add((a,sources[x]))
        old.append([[x,state[x]] for x,v in event['write']])
        deltas.append([[x,v] for x,v in event['write'] if state[x]!=v])
        for x,v in event['write']:state[x]=v;sources[x]=a
    return {'old':old,'deltas':deltas,'edges':sorted(edges),'full':state}

def evaluate(raw: dict[str,Any], p: dict[str,Any], mask: int) -> dict[str,Any]:
    direct=raw['base'][:];delta=direct[:];undo=p['full'][:];undo_ok=True
    for i,e in enumerate(raw['events']):
        tick('baseline_forward_events')
        if mask&(1<<e['tag']):
            for x,v in e['write']:direct[x]=v;tick('baseline_write_updates')
            for x,v in p['deltas'][i]:delta[x]=v;tick('baseline_delta_updates')
    for i in range(len(raw['events'])-1,-1,-1):
        tick('baseline_undo_events');e=raw['events'][i]
        if not mask&(1<<e['tag']):
            if any(undo[x]!=v for x,v in e['write']):undo_ok=False;break
            for x,v in p['old'][i]:undo[x]=v;tick('baseline_undo_updates')
    for _ in p['edges']:tick('baseline_dependency_tests')
    deps=all(not mask&(1<<a) or mask&(1<<b) for a,b in p['edges'])
    return {'write_only':direct,'snapshot_delta':delta,
            'selective_old_log':undo if undo_ok else None,
            'original_provider':bool(deps)}
