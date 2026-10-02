"""Slow, direct finite oracles. No compiler or checker code is imported."""
from itertools import product, combinations
from typing import Any
COUNTS: dict[str,int]={}
def step(k: str, n: int=1) -> None:COUNTS[k]=COUNTS.get(k,0)+n

def execute(raw: dict[str,Any], mask: int) -> list[int] | None:
    state=raw['base'][:]
    for event in raw['events']:
        step('oracle_event_visits')
        if (mask//(2**event['tag']))%2==0:continue
        for x,values in event['guard']:
            step('oracle_guard_tests')
            if state[x] not in values:return None
        for x,value in event['write']:
            step('oracle_write_updates');state[x]=value
    return state

def ghost(raw: dict[str,Any], at: int, cell: int, mask: int) -> bool:
    e=raw['events'][at]
    if (mask//(2**e['tag']))%2==0:return True
    value=raw['base'][cell]
    for earlier in raw['events'][:at]:
        step('ghost_event_visits')
        if (mask//(2**earlier['tag']))%2:
            for x,v in earlier['write']:
                if x==cell:value=v
    return any(x==cell and value in values for x,values in e['guard'])

def all_primes(raw: dict[str,Any], at: int, cell: int) -> set[tuple[int,int]]:
    m=raw['aspects']
    if m>4:raise ValueError('the ternary prime oracle is limited to four aspects')
    truth=[ghost(raw,at,cell,k) for k in range(1<<m)]
    implicates=[]
    for signs in product((-1,0,1),repeat=m):
        neg=sum(1<<i for i,v in enumerate(signs) if v==-1)
        pos=sum(1<<i for i,v in enumerate(signs) if v==1)
        good=True
        for k,t in enumerate(truth):
            step('prime_boolean_tests')
            if t and not (neg&~k or pos&k):good=False;break
        if good:implicates.append((neg,pos))
    return {c for c in implicates if not any(d!=c and d[0]&c[0]==d[0] and d[1]&c[1]==d[1] for d in implicates)}

def valid_masks(raw: dict[str,Any]) -> list[int]:
    return [k for k in range(1<<raw['aspects']) if execute(raw,k) is not None]

def policy_answer(raw: dict[str,Any],on: int,off: int) -> tuple[str,int]:
    vs=valid_masks(raw);full=(1<<raw['aspects'])-1;optional=full&~(on|off)
    choices=[k for k in vs if k&on==on and not k&off]
    if choices:return 'optimal',min((optional&~k).bit_count() for k in choices)
    fs=[(i,bool(on&(1<<i))) for i in range(raw['aspects']) if (on|off)&(1<<i)]
    for n in range(1,len(fs)+1):
        for sub in combinations(fs,n):
            if not any(all(bool(k&(1<<i))==v for i,v in sub) for k in vs):return 'infeasible',n
    raise AssertionError('finite oracle failed')
