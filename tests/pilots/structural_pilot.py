import sys,json,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import structural,engine,producer,checker,oracle
start=time.process_time()
raw,on,off=structural.two_writer_sat(2,[[1,2,-1],[-1],[-2]])
c=engine.parse_case(raw); cert=producer.solve(c,on,off);checker.check(raw,cert)
assert max(structural.writer_counts(c))<=2
assert len({e.tag for e in c.events})==len(c.events)
raw2,on2,off2=structural.binary_choice_tree(4);c2=engine.parse_case(raw2)
cert2=producer.solve(c2,on2,off2);checker.check(raw2,cert2)
assert (cert2['core_on']|cert2['core_off']).bit_count()==5
assert max(z.size for z in producer.compile_trace(c2))==3
print(json.dumps({'passed':True,'SAT_kind':cert['kind'],'choice_tree_minimum_core':5,'choice_tree_largest_local_prime':3,'cpu_seconds':time.process_time()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
