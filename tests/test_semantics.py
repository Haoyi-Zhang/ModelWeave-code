"""Finite adversarial tests. They do not constitute a proof-assistant development."""
import copy,itertools,json,random,resource,sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import engine,producer,checker,oracle,generate,baselines
EVIDENCE={}
class Semantics(unittest.TestCase):
    def test_named_masks_and_all_policies(self):
        nm=nq=np=0
        for name,raw in generate.named().items():
            nm+=1;c=engine.parse_case(raw);cs=producer.compile_trace(c)
            for m in range(c.full+1):
                nq+=1;out=engine.replay(c,m);expected=oracle.execute(raw,m)
                self.assertEqual(out is not None,expected is not None,(name,m))
                self.assertEqual(producer.admissible(cs,m),expected is not None,(name,m))
                if out is not None:
                    self.assertEqual(out['end'],expected)
                    self.assertEqual(engine.reverse(c,out),c.base)
                    checker.check(raw,{'kind':'success','outcome':out})
                else:checker.check(raw,producer.local_obstruction(c,m))
            for bits in itertools.product((-1,0,1),repeat=c.aspects):
                on=sum(1<<i for i,v in enumerate(bits) if v==1)
                off=sum(1<<i for i,v in enumerate(bits) if v==-1)
                cert=producer.solve(c,on,off);checker.check(raw,cert);kind,value=oracle.policy_answer(raw,on,off);np+=1
                self.assertEqual(cert['kind'],kind)
                self.assertEqual(value,cert['cost'] if kind=='optimal' else (cert['core_on']|cert['core_off']).bit_count())
        EVIDENCE['named']={'cases':nm,'retention_queries':nq,'all_partial_policies':np}

    def test_prime_oracle(self):
        n=0
        for k in range(32):
            raw=generate.scalar(8547+k,m=4,cells=3,length=8);c=engine.parse_case(raw)
            for i,e in enumerate(c.events):
                for x,_ in e.guard:
                    n+=1;self.assertEqual({(z.off_literal,z.on_literal) for z in producer.local_profile(c,i,x)},oracle.all_primes(raw,i,x))
        EVIDENCE['prime_oracle']={'cases':32,'observations':n,'all_ternary_clauses_per_observation':81,'all_masks':16}

    def test_typing_complete_tiny_input_space(self):
        tried=admitted=0
        gs=[None,[0],[1],[0,1]];ws=[None,0,1]
        for state in itertools.product((0,1),repeat=3):
            if state[2] and not(state[0] and state[1]):continue
            for g in itertools.product(gs,repeat=3):
                for w in itertools.product(ws,repeat=3):
                    tried+=1;raw=generate.make(list(state),[generate.ev(0,{i:v for i,v in enumerate(g) if v is not None},{i:v for i,v in enumerate(w) if v is not None})],1,[2,2,2],[0,1],[[2,0,1]])
                    try:c=engine.parse_case(raw)
                    except engine.Invalid:continue
                    admitted+=1;out=engine.replay(c,1);self.assertIsNotNone(out)
                    self.assertFalse(out['end'][2] and not(out['end'][0] and out['end'][1]))
                    checker.check(raw,{'kind':'success','outcome':out})
        EVIDENCE['typing']={'input_event_state_pairs':tried,'admitted_enabled_pairs':admitted,'bad_poststates':0,'nodes':2,'edges':1}

    def test_static_independence(self):
        n=0
        for a,b,va,vb,ga,gb in itertools.product(range(2),range(2),range(2),range(2),range(3),range(3)):
            # Each event writes its own chosen cell and may observe one chosen cell.
            ea=generate.ev(0,{} if ga==2 else {ga:[0]},{a:va})
            eb=generate.ev(1,{} if gb==2 else {gb:[0]},{b:vb})
            raw=generate.make([0,0],[ea,eb],2,[2,2])
            try:c=engine.parse_case(raw)
            except engine.Invalid:continue
            if not engine.independent(c.events[0],c.events[1]):continue
            rev=copy.deepcopy(raw);rev['events'].reverse();d=engine.parse_case(rev)
            x=engine.replay(c,3);y=engine.replay(d,3);n+=1
            self.assertEqual(x['end'],y['end'])
            # Compare complements by the event's tag, not its changing sequence index.
            xo={raw['events'][r['at']]['tag']:r['old'] for r in x['receipts']}
            yo={rev['events'][r['at']]['tag']:r['old'] for r in y['receipts']}
            self.assertEqual(xo,yo)
        EVIDENCE['independence']={'admitted_swaps':n,'differences':0}

    def test_sat_and_vertex_cover(self):
        rng=random.Random(62119);sat_count=cover_count=0
        for n in range(1,5):
            for k in range(4):
                formula=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(3)] for _ in range(n+2)]
                if k==0:formula=[[1],[-1]]
                raw,on,off=generate.sat_gadget(n,formula);c=engine.parse_case(raw)
                satisfiable=any(all(any(bool(mask&(1<<(abs(l)-1)))==(l>0) for l in clause) for clause in formula) for mask in range(1<<n))
                cert=producer.solve(c,on,off);checker.check(raw,cert)
                self.assertEqual(cert['kind']=='optimal',satisfiable);sat_count+=1
        for n in range(2,6):
            es=[(a,b) for a in range(n) for b in range(a+1,n)]
            for k in range(4):
                edges=[e for e in es if rng.random()<.6] or [es[0]]
                raw,on,off=generate.cover_gadget(n,edges);c=engine.parse_case(raw)
                best=min(mask.bit_count() for mask in range(1<<n) if all(mask&(1<<a) or mask&(1<<b) for a,b in edges))
                cert=producer.solve(c,on,off);checker.check(raw,cert)
                self.assertEqual(cert['kind'],'optimal');self.assertEqual(cert['cost'],best);cover_count+=1
        EVIDENCE['reductions']={'SAT_formulas':sat_count,'vertex_cover_graphs':cover_count,'differences':0}

    def test_fixed_mask_local_cardinality_and_protocol(self):
        # Query mask M keeps b1, b2, and reader r.  The four-fact explanation is
        # inclusion-minimal but not minimum-cardinality; the checker must reject it.
        raw=generate.make([1],[
            generate.ev(0,{}, {0:0}),  # b1
            generate.ev(1,{}, {0:1}),  # g1
            generate.ev(2,{}, {0:0}),  # b2
            generate.ev(3,{}, {0:1}),  # g2
            generate.ev(4,{0:[1]}, {}), # r
        ],5,[2])
        c=engine.parse_case(raw);mask=(1<<0)|(1<<2)|(1<<4)
        self.assertIsNone(engine.replay(c,mask))
        minimum={'kind':'local','mask':mask,'event':4,'cell':0,
                 'on':(1<<4)|(1<<2),'off':1<<3}
        inclusion_only={'kind':'local','mask':mask,'event':4,'cell':0,
                        'on':(1<<4)|(1<<0),'off':(1<<1)|(1<<3)}
        checker.check(raw,minimum)
        with self.assertRaisesRegex(checker.Rejected,'minimum-cardinality'):
            checker.check(raw,inclusion_only)
        self.assertEqual(producer.local_obstruction(c,mask),minimum)

        # The shipped zero-cost optimum authorizes its cost leaf with budget -1.
        example=json.loads((Path(__file__).resolve().parents[1]/'results/examples/example-03.json').read_text())
        self.assertEqual(example['certificate']['cost'],0)
        checker.check(example['case'],example['certificate'])
        bad=copy.deepcopy(example['certificate']);bad['kind']='infeasible'
        bad.pop('cost');bad.pop('outcome');bad['core_on']=bad['on'];bad['core_off']=bad['off'];bad['witnesses']=[]
        with self.assertRaises(checker.Rejected):checker.check(example['case'],bad)
        EVIDENCE['targeted_protocol']={
            'query_mask':mask,'minimum_facts':3,'inclusion_minimal_nonminimum_facts':4,
            'minimum_accepted':True,'nonminimum_rejected':True,
            'example_03_zero_cost_accepted':True,'cost_leaf_rejected_without_optimal_budget':True}

    def test_mutations(self):
        raw=generate.named()['stale_complement'];c=engine.parse_case(raw);good={'kind':'success','outcome':engine.replay(c,2)}
        trials=[]
        def add(name,rr,cc):trials.append((name,rr,cc))
        def mutate(name,fn,case=False):
            rr=copy.deepcopy(raw);cc=copy.deepcopy(good);fn(rr if case else cc);add(name,rr,cc)
        mutate('wrong_final',lambda z:z['outcome']['end'].__setitem__(0,1))
        mutate('wrong_old',lambda z:z['outcome']['receipts'][0]['old'][0].__setitem__(1,1))
        mutate('missing_old',lambda z:z['outcome']['receipts'][0].__setitem__('old',[]))
        mutate('duplicate_old',lambda z:z['outcome']['receipts'][0]['old'].append([0,0]))
        mutate('wrong_occurrence',lambda z:z['outcome']['receipts'][0].__setitem__('at',0))
        mutate('missing_receipt',lambda z:z['outcome'].__setitem__('receipts',[]))
        mutate('bool_mask',lambda z:z['outcome'].__setitem__('mask',True))
        mutate('high_mask',lambda z:z['outcome'].__setitem__('mask',4))
        mutate('unknown_field',lambda z:z.__setitem__('trusted',True))
        mutate('duplicate_write',lambda z:z['events'][0]['write'].append([0,1]),True)
        mutate('out_of_domain',lambda z:z['base'].__setitem__(0,3),True)
        mutate('bad_original_guard',lambda z:z['events'][0]['guard'].append([0,[1]]),True)
        tr=generate.named()['replacement'];tc=engine.parse_case(tr);lc=producer.local_obstruction(tc,4)
        x=copy.deepcopy(lc);x['off']=0;add('nonforcing_local',tr,x)
        # An extra compatible fact makes this local certificate non-minimal.
        weak=generate.named()['unary_not_exact'];wc=engine.parse_case(weak)
        non=producer.solve(tc,4,3)
        x=copy.deepcopy(non);x['witnesses']=[];add('missing_core_witnesses',tr,x)
        x=copy.deepcopy(non);x['proof']={'cut':[2,0,0]};add('unforced_bad_source',tr,x)
        opt=producer.solve(tc,0,0)
        x=copy.deepcopy(opt);x['cost']=1;add('wrong_cost',tr,x)
        x=copy.deepcopy(opt);x['proof']={'split':0,'zero':{'cost':True}};add('missing_branch',tr,x)
        x=copy.deepcopy(non);x['proof']={'cost':True};add('unauthorized_cost_leaf',tr,x)
        gr=generate.make([1,1,1],[],0,[2,2,2],[0,1],[[2,0,1]])
        go={'kind':'success','outcome':{'mask':0,'end':[1,1,1],'receipts':[]}}
        gr['base'][0]=0;add('dangling_base',gr,go)
        for name,rr,cc in trials:
            with self.subTest(name=name):
                with self.assertRaises((checker.Rejected,ValueError,TypeError,KeyError)):checker.check(rr,cc)
        # This is deliberately accepted: internally consistent data is not authenticated data.
        rr=copy.deepcopy(raw);rr['base'][0]=1;cc=copy.deepcopy(good);cc['outcome']['receipts'][0]['old'][0][1]=1
        checker.check(rr,cc)
        EVIDENCE['mutations']={'rejected_names':[n for n,_,_ in trials],'rejected':len(trials),'consistent_case_and_receipt_change_accepted':True}

    def test_nonlocal_gap_and_omissions(self):
        cases=generate.named();gap=cases['local_global_gap'];c=engine.parse_case(gap)
        local=producer.local_obstruction(c,4);global_=producer.solve(c,4,2)
        self.assertEqual((local['on']|local['off']).bit_count(),3)
        self.assertEqual((global_['core_on']|global_['core_off']).bit_count(),2)
        for name in ('observation_exact','observation_weak','order_left','order_right','idempotent_delta','stale_complement'):
            self.assertIsNotNone(engine.parse_case(cases[name]))
        self.assertIsNone(oracle.execute(cases['observation_exact'],5));self.assertIsNotNone(oracle.execute(cases['observation_weak'],5))
        self.assertIsNotNone(oracle.execute(cases['order_left'],25));self.assertIsNone(oracle.execute(cases['order_right'],25))
        raw=cases['idempotent_delta'];prep=baselines.prepare(raw);got=baselines.evaluate(raw,prep,2)
        self.assertNotEqual(got['snapshot_delta'],oracle.execute(raw,2))
        # A retained event's original complement is observably stale after erasure.
        raw=cases['stale_complement'];c=engine.parse_case(raw);orig=engine.replay(c,3);new=engine.replay(c,2)
        new['receipts'][0]['old']=orig['receipts'][1]['old']
        with self.assertRaises(checker.Rejected):checker.check(raw,{'kind':'success','outcome':new})
        EVIDENCE['boundaries']={'local_size':3,'global_size':2,'observation_omission':True,'order_omission':True,'stale_complement_rejected':True,'delta_omission':True}

if __name__=='__main__':
    cpu=time.process_time();wall=time.perf_counter();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Semantics)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    data={'passed':result.wasSuccessful(),'test_methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
          'evidence':EVIDENCE,'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-wall,
          'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'counters':{'producer':engine.COUNTS,'checker':checker.COUNTS,'oracle':oracle.COUNTS,'baselines':baselines.COUNTS}}
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(data,indent=2)+'\n')
    else:print(json.dumps(data,indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
