#!/usr/bin/env python3
"""Exact bounded falsification of the structural refinements (one worker)."""
from __future__ import annotations
import itertools, json, random, resource, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import engine, producer, checker, oracle, generate, structural


def cnf_value(clauses, mask):
    return all(any(not mask & (1 << a) for a in neg) or any(mask & (1 << a) for a in pos)
               for neg, pos in clauses)


def one_writer_case(seed):
    rng = random.Random(seed); m = 5; cells = 3
    base = [rng.randrange(2) for _ in range(cells)]
    owner = [rng.randrange(-1, m) for _ in range(cells)]
    values = [rng.randrange(2) for _ in range(cells)]
    state = base[:]; events = []
    for tag in range(m):
        guard = {x: ([state[x]] if rng.random() < .8 else [0, 1])
                 for x in range(cells) if rng.random() < .5}
        write = {x: values[x] for x in range(cells) if owner[x] == tag}
        events.append(generate.ev(tag, guard, write))
        for x, value in write.items():
            state[x] = value
    return generate.make(base, events, m, [2] * cells)


def run(output):
    for mod in (engine, checker, oracle):
        mod.COUNTS.clear()
    cpu, wall = time.process_time(), time.perf_counter()
    records = []; queries = 0; policies = 0
    clause_types = []
    for signs in itertools.product((-1, 0, 1), repeat=4):
        neg = [a for a, sign in enumerate(signs) if sign == -1]
        pos = [a for a, sign in enumerate(signs) if sign == 1]
        if 1 <= len(neg) <= 2 and pos:
            clause_types.append((neg, pos))
    rng = random.Random(98157)
    formulas = [[c] for c in clause_types]
    formulas += [rng.sample(clause_types, rng.randrange(1, 7)) for _ in range(64)]
    for i, clauses in enumerate(formulas):
        raw = structural.realize_clauses(4, clauses); c = engine.parse_case(raw)
        compiled = producer.compile_trace(c); tests = []
        for mask in range(16):
            expected = cnf_value(clauses, mask)
            end = oracle.execute(raw, mask)
            assert expected == (end is not None) == producer.admissible(compiled, mask)
            tests.append({'mask': mask, 'valid': expected}); queries += 1
        records.append({'group': 'clause_realization', 'index': i, 'formula': clauses,
                        'case': raw, 'queries': tests})
    # The four-literal, three-negative target entails no mixed <=2-negative clause.
    target = [([0, 1, 2], [3])]
    possible = [c for c in clause_types if all(not cnf_value(target, m) or cnf_value([c], m)
                                               for m in range(16))]
    assert not possible
    for i in range(32):
        raw = one_writer_case(516239 + i); c = engine.parse_case(raw)
        assert max(structural.writer_counts(c)) <= 1
        edges = structural.one_writer_edges(c)
        valid = []
        for mask in range(32):
            end = oracle.execute(raw, mask)
            edge_ok = all(not mask & (1 << a) or mask & (1 << b) for a, b in edges)
            assert bool(edge_ok) == (end is not None)
            if end is not None:
                valid.append(mask)
            queries += 1
        tests = []
        for signs in itertools.product((-1, 0, 1), repeat=5):
            on = sum(1 << a for a, sign in enumerate(signs) if sign == 1)
            off = sum(1 << a for a, sign in enumerate(signs) if sign == -1)
            got = structural.one_writer_completion(c, on, off)
            allowed = [m for m in valid if m & on == on and not m & off]
            assert (got is not None) == bool(allowed)
            if allowed:
                assert got in allowed and all(m | got == got for m in allowed)
                optional = c.full & ~(on | off)
                assert (optional & ~got).bit_count() == min((optional & ~m).bit_count() for m in allowed)
            tests.append({'on': on, 'off': off, 'maximum': got}); policies += 1
        cert = producer.solve(c, 16, 1); checker.check(raw, cert)
        records.append({'group': 'one_writer', 'index': i, 'case': raw,
                        'edges': edges, 'valid_masks': valid, 'policies': tests, 'certificate': cert})
    sat_cases = 0
    rng = random.Random(730163)
    formulas_to_check=[]
    # Preserve the original 18 named/random checks, then add 256 deterministic
    # bounded reduction checks.  The latter exercise both satisfiable and
    # unsatisfiable formulas without changing the general theorem's proof status.
    for n in range(1, 4):
        for i in range(6):
            formula = [[rng.choice((-1, 1)) * rng.randint(1, n) for _ in range(3)] for _ in range(3)]
            if i == 0: formula = [[1], [-1], [n]]
            formulas_to_check.append((n,formula,'original'))
    for i in range(256):
        n=1+(i%3); h=1+((i//3)%3)
        local=random.Random(911731+i)
        formula=[[local.choice((-1,1))*local.randint(1,n) for _ in range(3)] for _ in range(h)]
        if i%16==0: formula=[[1],[-1]]
        elif i%16==1: formula=[[1]]
        formulas_to_check.append((n,formula,'extended'))
    for n,formula,cohort in formulas_to_check:
        expected = any(all(any(bool(mask & (1 << (abs(lit) - 1))) == (lit > 0)
                                  for lit in clause) for clause in formula) for mask in range(1 << n))
        raw, on, off = structural.two_writer_sat(n, formula); c = engine.parse_case(raw)
        assert max(structural.writer_counts(c)) <= 2
        assert len({event.tag for event in c.events}) == len(c.events) == c.aspects
        assert on.bit_count()==off.bit_count()==1 and not on&off
        assert all(d==2 for d in raw['domains'])
        assert max((cl.size for cl in producer.compile_trace(c)), default=0) <= 3
        cert = producer.solve(c, on, off); checker.check(raw, cert)
        assert (cert['kind'] == 'optimal') == expected
        records.append({'group': 'two_writer_sat', 'cohort':cohort,'variables': n, 'formula': formula,
                        'satisfiable': expected, 'case': raw, 'certificate': cert})
        sat_cases += 1
    for leaves in range(2, 7):
        raw, on, off = structural.binary_choice_tree(leaves); c = engine.parse_case(raw)
        assert max(structural.writer_counts(c)) == 2
        assert all(cl.size == 3 for cl in producer.compile_trace(c))
        cert = producer.solve(c, on, off); report = checker.check(raw, cert)
        assert cert['kind'] == 'infeasible'
        assert (cert['core_on'] | cert['core_off']).bit_count() == leaves + 1
        records.append({'group': 'choice_tree', 'leaves': leaves, 'case': raw,
                        'certificate': cert, 'checked': report})
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'structural-cases.jsonl').open('w') as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n')
    report = {'passed': True, 'total_inputs': len(records),
              'single_clause_types': len(clause_types), 'generated_conjunctions': 64,
              'one_writer_cases': 32, 'direct_retention_queries': queries,
              'one_writer_partial_policies': policies, 'two_writer_SAT_cases': sat_cases,
              'choice_tree_cases': 5, 'largest_checked_global_core': 7,
              'strict_expressivity_nonrepresentation': True,
              'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - wall,
              'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'counters': {'producer': dict(engine.COUNTS), 'checker': dict(checker.COUNTS),
                           'oracle': dict(oracle.COUNTS)}}
    (output / 'structural.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    run(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'results')
