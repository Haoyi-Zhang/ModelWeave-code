"""Portable exact comparisons for owned, finite named-update examples.

The source interpreter and positive-precondition action interpreter below do not
call engine execution, normalization, or the compiler. No third-party tool runs.
Without --output this entrypoint writes nothing; an explicit output must be new.
"""
from __future__ import annotations
import argparse
import copy
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import baselines
import checker
import engine
import producer
import structural
from update_language import compile_positive_actions, compile_updates, decode_state


def patch(label, require=None, assign=None):
    return {'label': label, 'require': require or {}, 'assign': assign or {}}


def fixtures():
    boolean = ['off', 'on']
    yield 'single_provider', {'domains': {'ready': boolean, 'shown': boolean},
        'base': {'ready': 'off', 'shown': 'off'}, 'labels': ['prepare', 'view', 'extra'],
        'patches': [patch('prepare', assign={'ready': 'on'}),
                    patch('view', {'ready': ['on']}, {'shown': 'on'})]}
    yield 'alternative_providers', {'domains': {'ready': boolean}, 'base': {'ready': 'off'},
        'labels': ['cache', 'fallback', 'view'],
        'patches': [patch('cache', assign={'ready': 'on'}), patch('fallback', assign={'ready': 'on'}),
                    patch('view', {'ready': ['on']})]}
    yield 'overwriting_inhibitor', {'domains': {'visible': boolean}, 'base': {'visible': 'off'},
        'labels': ['publish', 'hide', 'check'],
        'patches': [patch('publish', assign={'visible': 'on'}), patch('hide', assign={'visible': 'off'}),
                    patch('check', {'visible': ['off']})]}
    yield 'shared_label', {'domains': {'ready': boolean, 'shown': boolean},
        'base': {'ready': 'off', 'shown': 'off'}, 'labels': ['bundle', 'override', 'view'],
        'patches': [patch('bundle', assign={'ready': 'on'}), patch('override', assign={'ready': 'off'}),
                    patch('bundle', assign={'ready': 'on'}), patch('view', {'ready': ['on']}, {'shown': 'on'})]}
    yield 'membership_guard', {'domains': {'mode': ['plain', 'dark', 'compact'], 'fixed': ['locked']},
        'base': {'mode': 'plain', 'fixed': 'locked'}, 'labels': ['theme', 'dashboard'],
        'patches': [patch('theme', assign={'mode': 'dark'}),
                    patch('dashboard', {'mode': ['plain', 'dark']}, {'mode': 'compact', 'fixed': 'locked'})]}
    yield 'receipt_rebase', {'domains': {'mode': ['plain', 'dark', 'compact'], 'visible': boolean,
                                       'quota': ['zero', 'three']},
        'base': {'mode': 'plain', 'visible': 'on', 'quota': 'zero'},
        'labels': ['theme', 'privacy', 'dashboard'],
        'patches': [patch('theme', assign={'mode': 'dark'}), patch('privacy', assign={'visible': 'off'}),
                    patch('dashboard', {'visible': ['off']}, {'mode': 'compact', 'quota': 'three'})]}


def source_execute(program, kept):
    state = dict(program['base'])
    predecessors = []
    for i, event in enumerate(program['patches']):
        if event['label'] not in kept:
            continue
        if any(state[name] not in allowed for name, allowed in event['require'].items()):
            return i, state, predecessors
        predecessors.append((i, {name: state[name] for name in event['assign']}))
        # All requirements and predecessors were evaluated before the update.
        state.update(event['assign'])
    return None, state, predecessors


def positive_actions(program):
    """Exercise the delivered compiler against the separate action interpreter."""
    return compile_positive_actions(program)


def action_execute(initial, actions, kept):
    state = set(initial)
    for i, (label, pre, add, delete) in enumerate(actions):
        if label not in kept:
            continue
        if not pre <= state:
            return i, state
        state = (state - delete) | add
    return None, state


def reduction_cnf(n, formula, mask):
    """Directly evaluate the displayed gadget CNF, not normalized trace clauses."""
    d = 2 * n
    r = 2 * n + len(formula) + 1
    kept = lambda a: bool(mask & (1 << a))
    for i in range(n):
        if kept(r) and not (kept(i) or kept(n + i)):
            return False
        if kept(n + i) and kept(i) and not kept(d):
            return False
    for j, clause in enumerate(formula):
        padded = clause + [clause[-1]] * (3 - len(clause))
        tags = [lit - 1 if lit > 0 else n + (-lit - 1) for lit in padded]
        q = d + 1 + j
        if kept(q) and not (kept(tags[1]) or kept(tags[2])):
            return False
        if kept(r) and not (kept(tags[0]) or kept(q)):
            return False
    return True


def run():
    if not __debug__:
        raise RuntimeError('scientific comparisons require assertions; run Python without -O')
    records = []
    successes = failures = packets = actions_checked = policies = 0
    for name, program in fixtures():
        original = copy.deepcopy(program)
        raw, coding = compile_updates(program)
        case = engine.parse_case(raw)
        clauses = producer.compile_trace(case)
        boolean = all(v == ['off', 'on'] for v in program['domains'].values())
        rail = positive_actions(program) if boolean else None
        truth = []
        valid = []
        for mask in range(case.full + 1):
            kept = {label for a, label in enumerate(program['labels']) if mask & (1 << a)}
            failed, state, old = source_execute(program, kept)
            outcome = engine.replay(case, mask)
            assert (failed is None) == (outcome is not None) == producer.admissible(clauses, mask)
            failure = engine.first_failure(case, mask)
            assert failed == (None if failure is None else failure[0])
            if rail is not None:
                rf, rs = action_execute(*rail, kept)
                assert rf == failed and dict(rs) == state
                actions_checked += 1
            if outcome is None:
                checker.check(raw, producer.local_obstruction(case, mask))
                failures += 1
            else:
                valid.append(mask)
                assert decode_state(coding, outcome['end']) == state
                for receipt, (at, source_old) in zip(outcome['receipts'], old, strict=True):
                    assert receipt['at'] == at
                    event = program['patches'][at]
                    needed = {x: v for x, v in source_old.items()
                              if len(event['require'].get(x, program['domains'][x])) != 1}
                    actual = {coding['cells'][x]: coding['values'][x][v] for x, v in receipt['old']}
                    assert actual == needed
                assert engine.reverse(case, outcome) == case.base
                checker.check(raw, {'kind': 'success', 'outcome': outcome})
                successes += 1
            packets += 1
            truth.append({'mask': mask, 'failure_event': failed, 'state': state})
        # Exact completion comparison uses the independently interpreted source masks.
        for signs in itertools.product((-1, 0, 1), repeat=case.aspects):
            on = sum(1 << a for a, v in enumerate(signs) if v == 1)
            off = sum(1 << a for a, v in enumerate(signs) if v == -1)
            allowed = [mask for mask in valid if mask & on == on and not mask & off]
            cert = producer.solve(case, on, off)
            checker.check(raw, cert)
            assert (cert['kind'] == 'optimal') == bool(allowed)
            if allowed:
                optional = case.full & ~(on | off)
                assert cert['cost'] == min((optional & ~mask).bit_count() for mask in allowed)
            if max(structural.writer_counts(case), default=0) <= 1:
                maximum = structural.one_writer_completion(case, on, off)
                assert (maximum is not None) == bool(allowed)
                if allowed:
                    assert maximum in allowed and all(mask | maximum == maximum for mask in allowed)
            policies += 1
        assert program == original
        records.append({'name': name, 'program': program, 'case': raw,
                        'writer_counts': structural.writer_counts(case), 'queries': truth})
    # Two hand-computed anchors bind the comparison to concrete source semantics.
    alternative = records[1]
    assert next(q for q in alternative['queries'] if q['mask'] == 5)['failure_event'] is None
    assert not baselines.evaluate(alternative['case'], baselines.prepare(alternative['case']), 5)['original_provider']
    rebase = records[5]
    assert next(q for q in rebase['queries'] if q['mask'] == 6)['state']['mode'] == 'compact'
    c = engine.parse_case(rebase['case'])
    selected = engine.replay(c, 6)
    historical = engine.replay(c, 7)
    assert selected['receipts'][-1]['old'] != historical['receipts'][-1]['old']
    # A disabled requirement must not silently skip an active patch.
    bad = copy.deepcopy(records[0]['program'])
    bad['patches'][0]['require'] = {'ready': ['on']}
    try:
        compile_updates(bad)
    except engine.Invalid:
        pass
    else:
        raise AssertionError('nonexecutable full source accepted')
    bad = copy.deepcopy(records[0]['program'])
    bad['patches'][0]['assign']['ready'] = 'missing'
    try:
        compile_updates(bad)
    except engine.Invalid:
        pass
    else:
        raise AssertionError('out-of-domain constant accepted')
    # Match the displayed reduction clauses on all masks, not merely SAT answers.
    cnf_queries = formula_count = sat_witnesses = 0
    for n, formula in [(1, [[1]]), (1, [[-1]]), (1, [[1], [-1]]),
                       (2, [[1, 2, -1]]), (2, [[1, 2], [-1, -2]]),
                       (2, [[1], [-1, 2]])]:
        raw, on, off = structural.two_writer_sat(n, formula)
        case = engine.parse_case(raw)
        assert max(structural.writer_counts(case)) <= 2
        assert len(case.events) == case.aspects == len({e.tag for e in case.events})
        for mask in range(case.full + 1):
            assert reduction_cnf(n, formula, mask) == (engine.replay(case, mask) is not None)
            cnf_queries += 1
        for assignment in range(1 << n):
            expected = all(any(bool(assignment & (1 << (abs(lit) - 1))) == (lit > 0)
                               for lit in clause) for clause in formula)
            variable_mask = sum(1 << (i if assignment & (1 << i) else n + i) for i in range(n))
            possible = any(reduction_cnf(n, formula, variable_mask | on | (helper << (2*n+1)))
                           for helper in range(1 << len(formula)))
            assert expected == possible
            sat_witnesses += 1
        formula_count += 1
    return {'passed': True, 'owned_examples': len(records), 'retention_queries': successes + failures,
            'successes': successes, 'guard_failures': failures, 'checked_packets': packets,
            'partial_policy_comparisons': policies, 'positive_action_queries': actions_checked,
            'gadget_formulas': formula_count, 'gadget_CNF_mask_queries': cnf_queries,
            'source_assignment_helper_comparisons': sat_witnesses,
            'original_provider_false_rejection_anchor': True, 'stale_receipt_anchor': True,
            'published_tools_executed': 0, 'records': records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        destination = args.output.resolve()
        if destination.exists():
            parser.error('output must be a new file')
    report = run()
    if args.output:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}, indent=2))
