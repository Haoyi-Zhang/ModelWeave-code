"""Nine hand-written semantic anchors; no cost or performance comparison.

Source execution, supporter quantification, guarded trace replay and local/global
prime oracles check the same selected occurrences and mandatory terminal goal.
No external code, planner, model service or generated campaign is run.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import checker
import engine
import oracle
import producer
import structural
from sas_supporters import compile_sas, encode_supporters, occurrence_mask
from update_language import decode_state


def action(label, pre=None, eff=None):
    return {'label': label, 'pre': pre or {}, 'eff': eff or {}}


def task(labels, actions, *, base=None, goal=None, domains=None):
    return {'domains': domains or {'visible': ['off', 'on']},
            'base': base or {'visible': 'off'}, 'labels': labels,
            'actions': actions, 'goal': goal or {}}


def fixtures():
    yield 'base_without_writer', task(['read'], [action('read', {'visible': 'on'})],
                                     base={'visible': 'on'})
    yield 'alternative_supporters', task(['cache', 'backup', 'view'], [
        action('cache', eff={'visible': 'on'}), action('backup', eff={'visible': 'on'}),
        action('view', {'visible': 'on'})])
    yield 'base_threat_and_later_repair', task(['publish', 'hide', 'read'], [
        action('publish', eff={'visible': 'on'}), action('hide', eff={'visible': 'off'}),
        action('read', {'visible': 'off'})])
    yield 'mixed_repeated_label', task(['bundle', 'repair', 'read'], [
        action('bundle', eff={'visible': 'on'}), action('bundle', eff={'visible': 'off'}),
        action('repair', eff={'visible': 'on'}), action('read', {'visible': 'on'})])
    yield 'same_label_anchor', task(['bundle', 'repair'], [
        action('bundle', eff={'visible': 'on'}), action('repair', eff={'visible': 'off'}),
        action('bundle', {'visible': 'off'})])
    yield 'local_global_prime_gap', task(['publish', 'reset', 'read'], [
        action('publish', eff={'visible': 'on', 'mode': 'on'}),
        action('reset', eff={'visible': 'on', 'mode': 'off'}),
        action('read', {'visible': 'on', 'mode': 'off'})],
        domains={'visible': ['off', 'on'], 'mode': ['off', 'on']},
        base={'visible': 'off', 'mode': 'off'})
    yield 'prestate_and_idempotent_writes', task(['prepare', 'read'], [
        action('prepare', eff={'visible': 'on'}),
        action('read', {'visible': 'on'}, {'visible': 'on'})])
    yield 'goal_after_last_action', task(['theme'], [action('theme', eff={'mode': 'dark'})],
        domains={'mode': ['plain', 'dark', 'compact']}, base={'mode': 'plain'}, goal={'mode': 'dark'})
    yield 'empty_history', task([], [], domains={'fixed': ['locked']}, base={'fixed': 'locked'})


def source_execute(program, selected):
    state = dict(program['base'])
    receipts = []
    for i, event in enumerate(program['actions']):
        if event['label'] not in selected:
            continue
        if any(state[x] != v for x, v in event['pre'].items()):
            return i, state, receipts
        receipts.append((i, {x: state[x] for x in event['eff']
                             if x not in event['pre'] and len(program['domains'][x]) != 1}))
        state.update(event['eff'])
    if any(state[x] != v for x, v in program['goal'].items()):
        return len(program['actions']), state, receipts
    return None, state, receipts


def cnf_holds(clauses, assignment):
    return all(any(bool(assignment & (1 << (abs(lit) - 1))) == (lit > 0)
                   for lit in clause) for clause in clauses)


def witnesses(encoded, occurrences, clauses=None):
    # Only these tiny anchors are enumerated; construction itself does not search.
    if len(encoded['options']) > 12:
        raise ValueError('supporter anchor exceeds the twelve-option bound')
    n = len(encoded['action_variables'])
    return [bits for bits in range(1 << len(encoded['options']))
            if cnf_holds(encoded['clauses'] if clauses is None else clauses,
                         occurrences | (bits << n))]


def all_primes(truth, m):
    clauses = []
    for signs in itertools.product((-1, 0, 1), repeat=m):
        neg = sum(1 << i for i, s in enumerate(signs) if s == -1)
        pos = sum(1 << i for i, s in enumerate(signs) if s == 1)
        if all(not valid or neg & ~mask or pos & mask for mask, valid in enumerate(truth)):
            clauses.append((neg, pos))
    return {c for c in clauses if not any(d != c and d[0] & c[0] == d[0]
                                           and d[1] & c[1] == d[1] for d in clauses)}


def run():
    if not __debug__:
        raise RuntimeError('scientific comparisons require assertions; run Python without -O')
    records = []
    queries = observations = policies = 0
    for name, program in fixtures():
        unchanged = copy.deepcopy(program)
        raw, coding, terminal = compile_sas(program)
        case = engine.parse_case(raw)
        encoded = encode_supporters(program)
        expected_counts = [sum(x in a['eff'] for a in program['actions']) for x in program['domains']]
        assert structural.writer_counts(case) == expected_counts
        assert len(case.events) == len(program['actions']) + bool(program['goal'])
        assert coding['labels'][:len(program['labels'])] == program['labels']
        truth = []
        query_records = []
        for mask in range(1 << len(program['labels'])):
            selected = {a for i, a in enumerate(program['labels']) if mask & (1 << i)}
            failure, state, old = source_execute(program, selected)
            target_mask = mask | terminal
            out = engine.replay(case, target_mask)
            options = witnesses(encoded, occurrence_mask(program, mask))
            assert bool(options) == (failure is None) == (out is not None)
            first = engine.first_failure(case, target_mask)
            assert failure == (None if first is None else first[0])
            if out is not None:
                assert decode_state(coding, out['end']) == state
                selected_receipts = out['receipts'][:len(old)]
                for receipt, (at, source_old) in zip(selected_receipts, old, strict=True):
                    assert receipt['at'] == at
                    decoded = {coding['cells'][x]: coding['values'][x][v] for x, v in receipt['old']}
                    assert decoded == source_old
                if terminal:
                    assert out['receipts'][-1] == {'at': len(program['actions']), 'old': []}
                assert engine.reverse(case, out) == case.base
                checker.check(raw, {'kind': 'success', 'outcome': out})
            else:
                checker.check(raw, producer.local_obstruction(case, target_mask))
            truth.append(failure is None)
            query_records.append({'mask': mask, 'valid': failure is None,
                                  'supporter_witnesses': len(options), 'first_failure': failure})
            queries += 1
        for signs in itertools.product((-1, 0, 1), repeat=len(program['labels'])):
            on = sum(1 << i for i, s in enumerate(signs) if s == 1)
            off = sum(1 << i for i, s in enumerate(signs) if s == -1)
            source_possible = any(v and m & on == on and not m & off for m, v in enumerate(truth))
            packet = producer.solve(case, on | terminal, off)
            checker.check(raw, packet)
            assert (packet['kind'] == 'optimal') == source_possible
            # No comparison of different objectives, artificial costs, or runtimes.
            policies += 1
        for local in encoded['observations']:
            if local['reader'] is None:
                continue  # Goal formula is unconditionally active; trace goal is pinned.
            at, cell_name = local['at'], local['cell']
            cell = coding['cells'].index(cell_name)
            for mask in range(1 << len(program['labels'])):
                expected = oracle.ghost(raw, at, cell, mask)
                projected = bool(witnesses(encoded, occurrence_mask(program, mask), local['clauses']))
                assert projected == expected
                observations += 1
            assert {(c.off_literal, c.on_literal) for c in producer.local_profile(case, at, cell)} == oracle.all_primes(raw, at, cell)
        if name == 'alternative_supporters':
            full = occurrence_mask(program, 7)
            assert not cnf_holds(encoded['clauses'], full)  # Y=0 is not a valid universal choice.
            assert len(witnesses(encoded, full)) == 3  # Both true is also allowed: no exactly-one.
        if name == 'mixed_repeated_label':
            assert not truth[5]  # An early good write of bundle is killed by its own later bad write.
        if name == 'same_label_anchor':
            assert witnesses(encoded, 4)  # Occurrence-only final read sees the good base.
            assert not truth[1]  # Keeping its label also keeps the earlier bad write.
        if name == 'local_global_prime_gap':
            local_primes = producer.compile_trace(case)
            assert {c.size for c in local_primes} == {3}
            assert all_primes(truth, 3) == {(4, 2)}  # Global prime is not either local prime.
        if name == 'prestate_and_idempotent_writes':
            assert expected_counts == [2] and not truth[2]
            assert {o['source'] for o in encoded['options']} == {0}
        if name == 'goal_after_last_action':
            assert truth == [False, True]
            assert encoded['options'][0]['at'] == 1 and encoded['options'][0]['source'] == 0
        if name == 'empty_history':
            assert encoded['clauses'] == [] and truth == [True]
        assert program == unchanged
        records.append({'name': name, 'task': program, 'case': raw, 'forced_terminal_keep': terminal,
                        'writer_counts': expected_counts, 'supporter_encoding': encoded, 'queries': query_records})
    invalid = []
    base = records[1]['task']
    bad = copy.deepcopy(base); bad['actions'][2]['pre']['visible'] = ['off', 'on']; invalid.append(('membership_precondition', bad))
    bad = copy.deepcopy(base); bad['actions'][0]['eff']['visible'] = {'computed': 'on'}; invalid.append(('computed_effect', bad))
    bad = copy.deepcopy(base); bad['actions'][0]['pre']['visible'] = 'on'; invalid.append(('nonexecutable_full_plan', bad))
    bad = copy.deepcopy(base); bad['goal'] = {'visible': 'missing'}; invalid.append(('out_of_domain_goal', bad))
    bad = copy.deepcopy(base); bad['goal'] = {'visible': 'off'}; invalid.append(('unreached_full_plan_goal', bad))
    rejection_records = []
    for name, bad in invalid:
        for operation in (compile_sas, encode_supporters):
            try:
                operation(bad)
            except engine.Invalid:
                rejection_records.append({'name': name, 'operation': operation.__name__, 'rejected': True})
            else:
                raise AssertionError('invalid or unsupported SAS input accepted')
    return {'passed': True, 'hand_written_models': len(records), 'label_mask_queries': queries,
            'local_projection_queries': observations, 'partial_policy_queries': policies,
            'invalid_interface_rejections': 2 * len(invalid), 'supporter_quantifier': 'exists',
            'cost_or_timing_comparison': False, 'published_tools_executed': 0,
            'rejections': rejection_records, 'records': records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('output must be a new file')
    report = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}, indent=2))
