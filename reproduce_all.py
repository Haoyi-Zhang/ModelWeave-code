#!/usr/bin/env python3
"""Fresh sequential reproduction and semantic comparison against included evidence.

Only Python standard-library programs are executed, one child at a time. No hash,
version, toolchain or commit manifest is generated. Resource records are scientific
run measurements; a successful command is not a general proof-assistant proof.
"""
from __future__ import annotations
import argparse,gzip,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from run_resources import POSIX_LIMITS_AVAILABLE, apply_child_limits, child_usage


def load(path: Path):
    return json.loads(path.read_text())


def same_stream(a: Path,b: Path) -> int:
    count=0
    with gzip.open(a,'rb') as left,gzip.open(b,'rb') as right:
        while True:
            x=left.readline();y=right.readline()
            if x!=y:raise AssertionError('semantic stream differs: '+a.name)
            if not x:break
            count+=1
    return count


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();out=args.output.resolve()
    if out.exists():p.error('output must be a fresh, nonexistent directory')
    out.mkdir(parents=True)
    reports=[];start=time.perf_counter()
    def run(label: str,command: list[str], *, stdout_file: str | None=None) -> None:
        before=child_usage()
        wall=time.perf_counter()
        log=out/(stdout_file or label+'.log')
        with log.open('w') as f:
            environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
            result=subprocess.run([sys.executable,'-B',*command],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
                                  timeout=2700,check=False,env=environment,
                                  preexec_fn=apply_child_limits if POSIX_LIMITS_AVAILABLE else None)
        after=child_usage()
        reports.append({'command':['python',*[x.replace(str(out),'$OUTPUT') for x in command]],
                        'label':label,'exit_code':result.returncode,
                        'wall_seconds':time.perf_counter()-wall,
                        'cpu_seconds':None if before is None or after is None else after[0]-before[0],
                        'cumulative_child_peak_rss_kib':None if after is None else after[1]})
        if result.returncode:raise RuntimeError(label+' failed; inspect its log')
        print(label+': passed',flush=True)
    report={'passed':False,'commands':reports,'workers':1,
            'resource_controls':{'child_wall_timeout_seconds':2700,
                                 'posix_address_space_and_cpu_limits_applied':POSIX_LIMITS_AVAILABLE,
                                 'unavailable_telemetry':'null, not zero'}}
    try:
        run('event-local-guard',['tests/test_event_local_guard.py'],stdout_file='guard-lookup-regression.json')
        run('named-update-bridge',['tests/test_update_bridge.py','--output',str(out/'update-language.json')])
        run('update-contract',['tests/test_update_contract.py','--output',str(out/'update-contract.json')])
        run('sas-supporter-correspondence',['tests/test_supporter_equivalence.py','--output',str(out/'supporter-correspondence.json')])
        run('semantic-tests',['tests/test_semantics.py',str(out/'tests.json')])
        run('structural-tests',['tests/test_structural.py',str(out/'structural')])
        run('source-examples',['tests/test_examples.py',str(out/'examples')])
        run('exact-pilot',['tests/pilots/pilot.py'],stdout_file='exact-pilot.json')
        run('set-pilot',['tests/pilots/set_guard_pilot.py'],stdout_file='set-pilot.json')
        run('structural-pilot',['tests/pilots/structural_pilot.py'],stdout_file='structural-pilot.json')
        run('campaign',['reproduce.py','--out',str(out/'campaign')])
        streams=sorted((out/'campaign').glob('cases-*.jsonl.gz'))
        if len(streams)!=50:raise AssertionError('wrong number of campaign streams')
        checked_packets=0
        for first in range(0,50,10):
            batch=streams[first:first+10]
            label=f'independent-campaign-check-{first:03d}-{first+9:03d}'
            run(label,['verify.py',*[str(x) for x in batch]])
            verdict=json.loads((out/(label+'.log')).read_text().strip().splitlines()[-1])
            if verdict.get('accepted') is not True:
                raise AssertionError(label+' did not report acceptance')
            checked_packets+=int(verdict.get('packets',0))
        if checked_packets!=50000:raise AssertionError('wrong independently checked packet count')
        run('coverage-summary',['summarize_coverage.py','--campaign',str(out/'campaign'),'--output',str(out/'campaign/coverage.json')])
        if load(ROOT/'results/campaign/coverage.json')!=load(out/'campaign/coverage.json'):
            raise AssertionError('certificate coverage differs')
        run('independent-example-check',['verify.py',*[str(x) for x in sorted((out/'examples').glob('example-*.json'))]])
        run('policy-demo',['demo.py','results/examples/example-02.json','--on','2','--off','1','--output',str(out/'query.json')])
        run('independent-demo-check',['verify.py',str(out/'query.json')])
        original=load(ROOT/'results/campaign/summary.json');fresh=load(out/'campaign/summary.json')
        for key in ['metrics','counters','complete','chunks','seed','workers']:
            if original[key]!=fresh[key]:raise AssertionError('campaign field differs: '+key)
        records=sum(same_stream(ROOT/'results/campaign'/x.name,x) for x in streams)
        for name,subpath,keys in [
            ('tests.json','tests.json',['passed','test_methods','failures','errors','evidence','counters']),
            ('structural.json','structural/structural.json',[
                'passed','total_inputs','single_clause_types','generated_conjunctions','one_writer_cases',
                'direct_retention_queries','one_writer_partial_policies','two_writer_SAT_cases','choice_tree_cases',
                'largest_checked_global_core','strict_expressivity_nonrepresentation','counters'])]:
            a=load(ROOT/'results'/name);b=load(out/subpath)
            for key in keys:
                if a[key]!=b[key]:raise AssertionError(name+' differs at '+key)
        if (ROOT/'results/structural-cases.jsonl').read_bytes()!=(out/'structural/structural-cases.jsonl').read_bytes():
            raise AssertionError('structured raw records differ')
        for x in sorted((out/'examples').glob('example-*.json')):
            if load(ROOT/'results/examples'/x.name)!=load(x):raise AssertionError('source projection differs')
        for reference,fresh_name in [('update-language/summary.json','update-language.json'),
                                     ('update-contract/summary.json','update-contract.json'),
                                     ('supporter-correspondence/summary.json','supporter-correspondence.json')]:
            if load(ROOT/'results'/reference)!=load(out/fresh_name):
                raise AssertionError('update correspondence record differs: '+reference)
        guard=load(out/'guard-lookup-regression.json')
        if guard.get('passed') is not True or guard.get('benchmark_timing_run') is not False:
            raise AssertionError('untimed event-local guard regression failed')
        report.update(passed=True,semantic_campaign_records_compared=records,
                      independently_checked_campaign_packets=checked_packets,
                      structural_inputs_compared=421,source_guided_inputs_compared=6,
                      correspondence_records_compared=['update-language','update-contract','supporter-correspondence'],
                      event_local_guard_coverage=guard['coverage'],
                      hashes_generated=False,comparison='exact uncompressed semantic records and scientific counters; timings excluded')
    except (OSError,ValueError,TypeError,AssertionError,RuntimeError,subprocess.TimeoutExpired) as exc:
        report['error']=str(exc).replace(str(out),'$OUTPUT')
    report['wall_seconds']=time.perf_counter()-start
    report['measured_child_cpu_seconds']=(sum(c['cpu_seconds'] for c in reports)
                                          if all(c['cpu_seconds'] is not None for c in reports) else None)
    report['scope']='This clean run only; early unmetered exploratory CPU is not reconstructed.'
    (out/'clean-run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'commands':len(reports),'measured_child_cpu_seconds':report['measured_child_cpu_seconds']}))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
