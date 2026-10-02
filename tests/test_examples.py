#!/usr/bin/env python3
"""Source-guided projections, not reruns of the cited model-weaving tools.

The exact closed input traces are original encodings. Two balance inputs share
one source passage; six encodings do not mean six independent published examples.
"""
from __future__ import annotations
import argparse, json, resource, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import engine, checker, producer, oracle
from generate import make, ev

ANCHOR='https://jacquesklein2302.github.io/papers/2009-AspectUnweaving-MODELS.pdf'
RES='https://www.doc.ic.ac.uk/~iccp/papers/ReversingEventStructures.pdf'

def examples():
    # Nodes C1,C2,X; edge C2->X; method-presence attribute on C1.
    independent=make([1,1,0,0,0],[ev(0,{1:[1]},{2:1,3:1}),
        ev(1,{0:[1]},{4:1})],2,[2]*5,[0,1,2],[[3,1,2]])
    additive=make([1,0,0,0],[ev(0,{}, {1:1}),
        ev(1,{0:[1]},{2:1}),ev(1,{1:[1]},{3:1})],2,[2]*4)
    # 0=absent, 1=a, 2=b. Only the originally matched second position is captured.
    rematch=make([1,1],[ev(0,{}, {0:0}),ev(1,{1:[1]},{1:2})],2,[3,3])
    low=make([0],[ev(0,{}, {0:2}),ev(1,{0:[1,2]}, {})],2,[3])
    high=make([1],[ev(0,{}, {0:2}),ev(1,{0:[1,2]}, {})],2,[3])
    disjunction=make([0],[ev(0,{}, {0:1}),ev(1,{}, {0:1}),ev(2,{0:[1]}, {})],3,[2])
    records=[
        ('example-01',independent,2,1,ANCHOR,'Figure 3; author PDF page 8',
         'Independent additions; fixed catalog and collapsed property operations.'),
        ('example-02',additive,2,1,ANCHOR,'Figure 5; author PDF page 10',
         'Two match occurrences share a tag; whole-tag removal is stricter than match-level unweaving.'),
        ('example-03',rematch,2,1,ANCHOR,'Figure 4; author PDF page 9',
         'Newly exposed matches are not replayed. The fixed-match outcome is [1,2], not the rematched [2,2].'),
        ('example-04',low,2,1,ANCHOR,'Section 4.2; author PDF page 6',
         'Threshold projection: codes 0,1,2 represent 50,150,200. Base 50 is an encoding choice.'),
        ('example-05',high,2,1,ANCHOR,'Section 4.2; author PDF page 6',
         'Same threshold passage, base 150 chosen by this encoding. Not a second published example.'),
        ('example-06',disjunction,4,2,RES,'Figure 5, left cube; PDF page 15',
         'Disjunctive enabling projected to one fixed order; no reversible-event-structure implementation is imported.')]
    for label,raw,on,off,url,location,boundary in records:
        yield {'id':label,'case':raw,'on':on,'off':off,'source_url':url,
               'source_location':location,'encoding_boundary':boundary}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path,nargs='?',default=Path(__file__).resolve().parents[1]/'results'/'examples')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    for mod in (engine,checker,oracle):mod.COUNTS.clear()
    start=time.process_time();wall=time.perf_counter();records=[];queries=0
    for rec in examples():
        raw=rec['case'];case=engine.parse_case(raw);compiled=producer.compile_trace(case)
        truth=[]
        for mask in range(case.full+1):
            expected=oracle.execute(raw,mask)
            assert producer.admissible(compiled,mask)==(expected is not None)
            truth.append({'mask':mask,'end':expected});queries+=1
        cert=producer.solve(case,rec['on'],rec['off']);verified=checker.check(raw,cert)
        if rec['id']=='example-03':
            assert cert['outcome']['end']==[1,2]
        if rec['id'] in ('example-02','example-04'):
            assert cert['kind']=='infeasible'
        else:assert cert['kind']=='optimal'
        out={**rec,'queries':truth,'certificate':cert,'checked':verified};records.append(out)
        (args.output/(rec['id']+'.json')).write_text(json.dumps(out,indent=2)+'\n')
    report={'passed':True,'encodings':len(records),'retention_queries':queries,
            'distinct_source_passages_or_figures':5,'published_tools_executed':0,
            'optimal_certificates':sum(r['certificate']['kind']=='optimal' for r in records),
            'infeasible_certificates':sum(r['certificate']['kind']=='infeasible' for r in records),
            'cpu_seconds':time.process_time()-start,'wall_seconds':time.perf_counter()-wall,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'counters':{'producer':dict(engine.COUNTS),'checker':dict(checker.COUNTS),'oracle':dict(oracle.COUNTS)}}
    (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));return 0
if __name__=='__main__':raise SystemExit(main())
