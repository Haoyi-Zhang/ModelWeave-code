"""Portable regressions for named patches, action coding, and the write boundary.

Uses the reviewed direct named/action interpreters, not a third-party planner.
No output is written unless --output names a new file inside P003.
"""
from __future__ import annotations
import argparse
import copy
import itertools
import json
from pathlib import Path

from test_update_bridge import (ROOT, action_execute, checker, engine, patch,
                                producer, reduction_cnf, source_execute, structural)
from update_language import compile_positive_actions, compile_updates, decode_state


def fixtures():
    bits = ['off', 'on']
    yield 'interleaved_one_write_cycle', {
        'domains': {'x': bits, 'y': bits}, 'base': {'x': 'off', 'y': 'off'},
        'labels': ['alpha', 'beta', 'unused'],
        'patches': [patch('alpha', assign={'x': 'on'}),
                    patch('beta', {'x': ['on']}, {'y': 'on'}),
                    patch('alpha', {'y': ['on']})]}
    yield 'simultaneous_prestate', {
        'domains': {'x': bits, 'y': bits}, 'base': {'x': 'off', 'y': 'on'},
        'labels': ['replace', 'read'],
        'patches': [patch('replace', {'x': ['off'], 'y': ['on']}, {'x': 'on', 'y': 'off'}),
                    patch('read', {'x': ['on'], 'y': ['off']})]}
    yield 'vacuous_full_domain_guard', {
        'domains': {'x': bits}, 'base': {'x': 'off'}, 'labels': ['read'],
        'patches': [patch('read', {'x': ['on', 'off']})]}
    yield 'finite_one_hot', {
        'domains': {'mode': ['plain', 'dark', 'compact'], 'fixed': ['locked']},
        'base': {'mode': 'plain', 'fixed': 'locked'}, 'labels': ['theme', 'view'],
        'patches': [patch('theme', assign={'mode': 'dark'}),
                    patch('view', {'mode': ['dark'], 'fixed': ['locked']},
                          {'mode': 'compact', 'fixed': 'locked'})]}
    yield 'proper_membership_guard', {
        'domains': {'mode': ['plain', 'dark', 'compact']}, 'base': {'mode': 'plain'},
        'labels': ['theme', 'view'],
        'patches': [patch('theme', assign={'mode': 'dark'}),
                    patch('view', {'mode': ['plain', 'dark']}, {'mode': 'compact'})]}
    yield 'same_label_anchor', {
        'domains': {'x': bits}, 'base': {'x': 'off'}, 'labels': ['old', 'bundle'],
        'patches': [patch('old', assign={'x': 'off'}), patch('bundle', assign={'x': 'on'}),
                    patch('bundle', {'x': ['on']})]}
    yield 'idempotent_writer_occurrences', {
        'domains': {'x': bits}, 'base': {'x': 'off'}, 'labels': ['first', 'second', 'read'],
        'patches': [patch('first', assign={'x': 'on'}), patch('second', assign={'x': 'on'}),
                    patch('read', {'x': ['on']})]}
    yield 'zero_label_empty_history', {
        'domains': {'fixed': ['locked']}, 'base': {'fixed': 'locked'}, 'labels': [], 'patches': []}


def recoded(program):
    other = copy.deepcopy(program)
    other['domains'] = {x: list(reversed(v)) for x, v in reversed(list(other['domains'].items()))}
    other['base'] = dict(reversed(list(other['base'].items())))
    other['labels'].reverse()
    for event in other['patches']:
        event['require'] = {x: list(reversed(v)) for x, v in reversed(list(event['require'].items()))}
        event['assign'] = dict(reversed(list(event['assign'].items())))
    return other


def run():
    records = []
    queries = action_queries = policies = failures = rejected_memberships = 0
    for name, original in fixtures():
        for encoding, program in [('declared', original), ('reversed_codes', recoded(original))]:
            untouched = copy.deepcopy(program)
            raw, coding = compile_updates(program)
            case = engine.parse_case(raw)
            counts = structural.writer_counts(case)
            eligible = all(len(v) == 1 or set(v) == set(program['domains'][x])
                           for e in program['patches'] for x, v in e['require'].items())
            if eligible:
                initial, actions = compile_positive_actions(program)
            else:
                try:
                    compile_positive_actions(program)
                except engine.Invalid:
                    rejected_memberships += 1
                else:
                    raise AssertionError('proper membership guard silently approximated')
            valid = []
            outcomes = []
            for mask in range(case.full + 1):
                kept = {a for i, a in enumerate(program['labels']) if mask & (1 << i)}
                failed, state, old = source_execute(program, kept)
                out = engine.replay(case, mask)
                assert (out is not None) == (failed is None)
                first = engine.first_failure(case, mask)
                assert failed == (None if first is None else first[0])
                if eligible:
                    action_failure, action_state = action_execute(initial, actions, kept)
                    assert action_failure == failed and action_state == set(state.items())
                    action_queries += 1
                if out is None:
                    checker.check(raw, producer.local_obstruction(case, mask))
                    failures += 1
                else:
                    valid.append(mask)
                    assert decode_state(coding, out['end']) == state
                    for receipt, (at, predecessor) in zip(out['receipts'], old, strict=True):
                        assert receipt['at'] == at
                        event = program['patches'][at]
                        needed = {x: v for x, v in predecessor.items()
                                  if len(event['require'].get(x, program['domains'][x])) != 1}
                        got = {coding['cells'][x]: coding['values'][x][v] for x, v in receipt['old']}
                        assert got == needed
                    checker.check(raw, {'kind': 'success', 'outcome': out})
                    assert engine.reverse(case, out) == case.base
                outcomes.append({'kept': sorted(kept), 'failure_event': failed, 'state': state})
                queries += 1
            # The modified closure is checked on new cyclic/empty/vacuous cases.
            if max(counts, default=0) <= 1:
                for signs in itertools.product((-1, 0, 1), repeat=case.aspects):
                    on = sum(1 << a for a, s in enumerate(signs) if s == 1)
                    off = sum(1 << a for a, s in enumerate(signs) if s == -1)
                    allowed = [m for m in valid if m & on == on and not m & off]
                    maximum = structural.one_writer_completion(case, on, off)
                    assert (maximum is not None) == bool(allowed)
                    cert = producer.solve(case, on, off)
                    checker.check(raw, cert)
                    if allowed:
                        assert maximum in allowed and all(m | maximum == maximum for m in allowed)
                        optional = case.full & ~(on | off)
                        assert cert['cost'] == (optional & ~maximum).bit_count()
                    else:
                        assert cert['kind'] == 'infeasible'
                        assert (cert['core_on'] | cert['core_off']).bit_count() == 2
                    policies += 1
            assert program == untouched
            records.append({'name': name, 'encoding': encoding, 'program': program,
                            'case': raw, 'writer_counts': counts,
                            'queries': sorted(outcomes, key=lambda q: q['kept'])})
    for left, right in zip(records[::2], records[1::2], strict=True):
        assert left['queries'] == right['queries']
    cycle = records[0]['program']
    assert source_execute(cycle, {'alpha'})[0] == 2
    assert source_execute(cycle, {'alpha', 'beta'})[0] is None
    assert records[12]['writer_counts'] == [2]  # identical values do not remove occurrences
    # Ordinary planning is allowed to reorder; a fixed-history selector is not.
    inhibitor = {'domains': {'x': ['off', 'on']}, 'base': {'x': 'off'},
                 'labels': ['publish', 'hide', 'read'],
                 'patches': [patch('publish', assign={'x': 'on'}),
                             patch('hide', assign={'x': 'off'}), patch('read', {'x': ['off']})]}
    assert source_execute(inhibitor, {'publish', 'read'})[0] == 2
    initial, actions = compile_positive_actions(inhibitor)
    assert action_execute(initial, [actions[2], actions[0]], {'publish', 'read'})[0] is None
    # Invalid closed histories/values still fail admission before action coding.
    invalid_inputs = []
    bad = copy.deepcopy(inhibitor); bad['patches'][0]['require'] = {'x': ['on']}; invalid_inputs.append(bad)
    bad = copy.deepcopy(inhibitor); bad['labels'].append('read'); invalid_inputs.append(bad)
    bad = copy.deepcopy(inhibitor); bad['domains']['x'].append('on'); invalid_inputs.append(bad)
    bad = copy.deepcopy(inhibitor); bad['patches'][0]['assign']['x'] = {'computed': 'on'}; invalid_inputs.append(bad)
    for bad in invalid_inputs:
        for compiler in (compile_updates, compile_positive_actions):
            try:
                compiler(bad)
            except engine.Invalid:
                pass
            else:
                raise AssertionError('invalid named program accepted')
    # New check criterion: the gadget CNF equals replay on every total mask, and
    # eliminating visible helper labels under r=1,d=0 gives the source formula.
    triples = [list(c) for c in itertools.product((1, -1), repeat=3)]
    formulas = [(1, [])] + [(1, [c]) for c in triples]
    formulas += [(1, [a, b]) for a in triples for b in triples]
    formulas += [(2, [[1, -2, 1], [-1, 2, -1]]), (2, [[1, 2, -2], [-1, -1, -1]])]
    cnf_queries = projections = 0
    reduction_records = []
    for n, formula in formulas:
        raw, on, off = structural.two_writer_sat(n, formula)
        case = engine.parse_case(raw)
        assert max(structural.writer_counts(case)) <= 2
        assert len(case.events) == case.aspects == len({e.tag for e in case.events})
        valid_count = 0
        for mask in range(case.full + 1):
            truth = reduction_cnf(n, formula, mask)
            assert truth == (engine.replay(case, mask) is not None)
            valid_count += truth
            cnf_queries += 1
        source_truth = []
        for assignment in range(1 << n):
            expected = all(any(bool(assignment & (1 << (abs(lit) - 1))) == (lit > 0)
                               for lit in c) for c in formula)
            variables = sum(1 << (i if assignment & (1 << i) else n + i) for i in range(n))
            projected = any(reduction_cnf(n, formula, variables | on | (h << (2 * n + 1)))
                            for h in range(1 << len(formula)))
            assert projected == expected
            source_truth.append(expected)
            projections += 1
        reduction_records.append({'variables': n, 'formula': formula,
                                  'source_truth': source_truth, 'valid_target_masks': valid_count})
    return {'passed': True, 'named_programs': 8, 'coding_variants': len(records),
            'retention_queries': queries, 'action_queries': action_queries,
            'guard_failures': failures, 'checked_query_packets': queries,
            'one_write_partial_policies': policies,
            'proper_membership_action_rejections': rejected_memberships,
            'invalid_program_compiler_rejections': 2 * len(invalid_inputs),
            'gadget_formulas': len(formulas), 'gadget_CNF_mask_queries': cnf_queries,
            'assignment_helper_projections': projections,
            'label_coupling_anchor': True, 'fixed_order_anchor': True,
            'idempotent_occurrence_anchor': True, 'published_tools_executed': 0,
            'records': records, 'reduction_records': reduction_records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        destination = args.output.resolve()
        if not destination.is_relative_to(ROOT.parent.resolve()) or destination.exists():
            parser.error('output must be a new file inside P003')
    report = run()
    if args.output:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('records', 'reduction_records')}, indent=2))
