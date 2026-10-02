#!/usr/bin/env python3
"""Reproduce the frozen finite campaign in resumable bounded chunks (one worker)."""
from __future__ import annotations
import argparse,csv,gzip,itertools,json,os,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import engine,producer,checker,oracle,generate,baselines
TOTAL=50000
CHUNK=1000
SEED=27182818

def dump(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True)

def inputs():
    for raw in generate.tiny():yield 'exhaustive',raw
    for i in range(36400):yield 'small',generate.scalar(SEED+i,m=3,cells=2,length=3,domain=3)
    for i in range(1200):yield 'medium',generate.scalar(SEED+100000+i,m=4+i%5,cells=3,length=8,domain=3)
    for i in range(50):yield 'graph',generate.graph(SEED+200000+i)

def query_masks(raw,index,group):
    full=(1<<raw['aspects'])-1
    if group=='exhaustive':return list(range(full+1))
    # Four deterministic queries; duplicates are removed, never counted twice.
    return sorted({full,full^(1<<(index%raw['aspects'])),index*2654435761&full,(index*1315423911+17)&full})

def counts():
    return {name:dict(module.COUNTS) for name,module in [('producer',engine),('checker',checker),('oracle',oracle),('baselines',baselines)]}

def process(index,group,raw):
    c=engine.parse_case(raw);clauses=producer.compile_trace(c);masks=query_masks(raw,index,group)
    results=[]
    for mask in masks:
        expected=oracle.execute(raw,mask)
        predicted=producer.admissible(clauses,mask)
        if predicted!=(expected is not None):raise AssertionError(('normalization',index,mask))
        results.append({'mask':mask,'end':expected})
    bad=next((q for q in results if q['end'] is None),None)
    if index%20==0 and bad is not None and group!='graph':
        cert=producer.local_obstruction(c,bad['mask'])
    else:
        good=next(q for q in results if q['end'] is not None)
        out=engine.replay(c,good['mask'])
        if out is None or out['end']!=good['end']:raise AssertionError('producer replay')
        cert={'kind':'success','outcome':out}
    checked=checker.check(raw,cert)
    baseline=[]
    if group=='exhaustive' or group=='small' and index<14350:
        prep=baselines.prepare(raw)
        for q in results:
            baseline.append({'mask':q['mask'],'values':baselines.evaluate(raw,prep,q['mask'])})
    return {'index':index,'group':group,'case':raw,'queries':results,
            'clauses':[[z.event,z.cell,z.off_literal,z.on_literal] for z in clauses],
            'certificate':cert,'checked':checked,'baselines':baseline}

def metrics(records):
    out={'cases':len(records),'queries':0,'valid_queries':0,'invalid_queries':0,'clauses':0,'literals':0,
         'success_certificates':0,'local_certificates':0,'baseline_queries':0,
         'original_provider_false_accept':0,'original_provider_false_reject':0,
         'write_only_false_accept':0,'snapshot_delta_false_accept':0,'snapshot_delta_wrong_valid_state':0,
         'selective_old_log_false_accept':0,'selective_old_log_false_reject':0,'selective_old_log_wrong_valid_state':0}
    for r in records:
        for g in ['exhaustive','small','medium','graph']:
            out[g+'_cases']=out.get(g+'_cases',0)+int(r['group']==g)
        out['queries']+=len(r['queries']);out['valid_queries']+=sum(q['end'] is not None for q in r['queries'])
        out['invalid_queries']+=sum(q['end'] is None for q in r['queries'])
        out['clauses']+=len(r['clauses']);out['literals']+=sum(a.bit_count()+b.bit_count() for _,_,a,b in r['clauses'])
        out[r['certificate']['kind']+'_certificates']+=1
        truth={q['mask']:q['end'] for q in r['queries']}
        for b in r['baselines']:
            out['baseline_queries']+=1;t=truth[b['mask']];v=b['values'];valid=t is not None
            out['original_provider_false_accept']+=int(v['original_provider'] and not valid)
            out['original_provider_false_reject']+=int(not v['original_provider'] and valid)
            out['write_only_false_accept']+=int(not valid)
            out['snapshot_delta_false_accept']+=int(not valid)
            out['snapshot_delta_wrong_valid_state']+=int(valid and v['snapshot_delta']!=t)
            out['selective_old_log_false_accept']+=int(v['selective_old_log'] is not None and not valid)
            out['selective_old_log_false_reject']+=int(v['selective_old_log'] is None and valid)
            out['selective_old_log_wrong_valid_state']+=int(valid and v['selective_old_log'] is not None and v['selective_old_log']!=t)
    return out

def add_dict(to,fr):
    for k,v in fr.items():
        if type(v) is dict:add_dict(to.setdefault(k,{}),v)
        else:to[k]=to.get(k,0)+v

def aggregate(out):
    ms=sorted(out.glob('chunk-*.json'));totals={};counters={};cpu=0;wall=0;peak=0;maximum=0
    for p in ms:
        d=json.loads(p.read_text());add_dict(totals,d['metrics']);add_dict(counters,d['counters'])
        cpu+=d['cpu_seconds'];wall+=d['wall_seconds'];peak=max(peak,d['peak_rss_kib']);maximum=max(maximum,d['max_case_seconds'])
    summary={'status':'finite_checks_passed_not_mechanized_general_proof','complete':totals.get('cases',0)==TOTAL,
             'chunks':len(ms),'metrics':totals,'counters':counters,'cpu_seconds':cpu,'wall_seconds':wall,
             'peak_rss_kib':peak,'max_case_seconds':maximum,'workers':1,'seed':SEED}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (out/'metrics.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['metric','value']);w.writerows(sorted(totals.items()))
    return summary

def run_chunk(out,chunk):
    meta=out/f'chunk-{chunk:03d}.json';data=out/f'cases-{chunk:03d}.jsonl.gz'
    if meta.exists():
        if not data.exists():raise ValueError('metadata exists but raw evidence is missing')
        return
    if data.exists():raise ValueError('uncommitted raw chunk exists; inspect it before removing it')
    for mod in (engine,checker,oracle,baselines):mod.COUNTS.clear()
    cpu=time.process_time();wall=time.perf_counter();records=[];maximum=0
    start=chunk*CHUNK;stop=min(start+CHUNK,TOTAL)
    # The input generator is deterministic. Skipping computes earlier inputs but
    # never executes scientific checks for skipped cases; its CPU is still metered.
    for index,(group,raw) in enumerate(itertools.islice(inputs(),start,stop),start):
        before=time.perf_counter();records.append(process(index,group,raw));dt=time.perf_counter()-before
        maximum=max(maximum,dt)
        if dt>5:raise RuntimeError('per-case budget exceeded')
    if len(records)!=stop-start:raise AssertionError('input cardinality changed')
    with data.open('xb') as rawfile:
        with gzip.GzipFile(fileobj=rawfile,mode='wb',filename='',mtime=0) as f:
            for r in records:f.write((dump(r)+'\n').encode())
    report={'start':start,'stop':stop,'metrics':metrics(records),'counters':counts(),
            'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-wall,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'max_case_seconds':maximum}
    if report['peak_rss_kib']>2500*1024:raise RuntimeError('memory budget exceeded')
    tmp=meta.with_suffix('.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');os.replace(tmp,meta)
    print(dump({'chunk':chunk,'cases':len(records),'cpu_seconds':report['cpu_seconds']}),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--chunk',type=int);p.add_argument('--aggregate',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    if not a.aggregate:
        chunks=range((TOTAL+CHUNK-1)//CHUNK) if a.chunk is None else [a.chunk]
        if any(not 0<=c<50 for c in chunks):p.error('chunk must be 0..49')
        for chunk in chunks:run_chunk(a.out,chunk)
    print(dump(aggregate(a.out)))
if __name__=='__main__':main()
