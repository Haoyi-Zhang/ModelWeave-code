#!/usr/bin/env python3
"""Summarize stored inputs/certificates without new semantic queries."""
from __future__ import annotations
import argparse,collections,gzip,json
from pathlib import Path

def summarize(root: Path) -> dict:
    counts=collections.Counter();groups={}
    paths=sorted(root.glob('cases-*.jsonl.gz'))
    if len(paths)!=50:raise ValueError('expected all 50 campaign streams')
    for path in paths:
        with gzip.open(path,'rt') as source:
            for line in source:
                r=json.loads(line);s=groups.setdefault(r['group'],collections.Counter())
                s['cases']+=1;s['queries']+=len(r['queries'])
                s['invalid_queries']+=sum(q['end'] is None for q in r['queries'])
                counts['zero_event_inputs']+=not r['case']['events']
                cert=r['certificate'];s[cert['kind']+'_certificates']+=1
                if cert['kind']=='success':
                    out=cert['outcome']
                    counts['empty_mask_successes']+=out['mask']==0
                    counts['no_receipt_successes']+=not out['receipts']
                    counts['nonempty_receipt_successes']+=bool(out['receipts'])
                    counts['receipt_occurrences']+=len(out['receipts'])
                    counts['full_mask_successes']+=out['mask']==(1<<r['case']['aspects'])-1
    return {'scope':'Descriptive analysis of stored campaign inputs and certificates; no new semantic queries.',
            'certificate_coverage':dict(counts),'groups':{k:dict(v) for k,v in groups.items()}}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--campaign',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=summarize(a.campaign)
    with a.output.open('x') as target:json.dump(result,target,indent=2);target.write('\n')
    print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
