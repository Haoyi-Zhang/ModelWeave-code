"""Compare event-local lookup with per-coordinate linear guard scanning.

Run timing alone, without concurrent benchmarks. Both implementations replay
the same admitted cases and restore the same receipts. Dependencies are local
artifact files and Python's standard library.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
from pathlib import Path
import sys
import time

ARTIFACT = Path(__file__).resolve().parents[1]
WIDTHS = (64, 128, 256, 512)


def plan(passes, rounds):
    return dict(
                comparison_reference='independent per-coordinate linear guard scan',
                candidate='event-local engine lookup',
                widths=list(WIDTHS), modes=['singleton', 'nonsingleton', 'unguarded',
                                           'unit_domain', 'mixed'],
                fixtures=20, masks_per_fixture=4, queries_per_pass=80,
                passes_per_sample=passes, paired_rounds=rounds,
                timed_scope='replay and successful reverse; no parsing or checking',
                equality_gate='fixture/API/oracle/checker regression; exact workload '
                              'outcomes/receipts/order/restored states/counters; timed-block counters',
                workers=1)


def load_helpers():
    path = ARTIFACT / 'tests' / 'test_event_local_guard.py'
    spec = importlib.util.spec_from_file_location('guard_lookup_regression', path)
    if spec is None or spec.loader is None:
        raise ValueError('cannot load artifact regression')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def same(left, right, label):
    if json.dumps(left, separators=(',', ':')) != json.dumps(right, separators=(',', ':')):
        raise AssertionError(label + ' differs; measurements cannot be promoted')


def workload(module, cases, passes=1, collect=False):
    module.COUNTS.clear()
    records = []
    queries = successes = failures = 0
    for _ in range(passes):
        for label, case, masks in cases:
            for mask in masks:
                outcome = module.replay(case, mask)
                restored = None
                if outcome is None:
                    failures += 1
                else:
                    restored = module.reverse(case, outcome)
                    if restored != case.base:
                        raise AssertionError('round trip failed: ' + label)
                    successes += 1
                queries += 1
                if collect:
                    records.append(dict(fixture=label, mask=mask,
                                        outcome=outcome, restored=restored))
    return dict(queries=queries, successes=successes, failures=failures,
                counters=dict(module.COUNTS), records=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--describe', action='store_true')
    mode.add_argument('--run-serial-timing', action='store_true')
    parser.add_argument('--passes', type=int, default=2)
    parser.add_argument('--rounds', type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.passes <= 10 or not 1 <= args.rounds <= 10:
        parser.error('passes and rounds must each be in 1..10')
    description = plan(args.passes, args.rounds)
    if args.describe:
        print(json.dumps(description, indent=2))
        return 0

    helper = load_helpers()
    regression = helper.run_regression()
    if not regression['passed']:
        print(json.dumps(regression, indent=2))
        return 1
    reference, engine, generate, checker, oracle = helper.runtimes()
    raw_cases = helper.multiwrite_cases(generate, WIDTHS)
    cases = []
    raw_by_label = dict(raw_cases)
    for label, raw in raw_cases:
        case = engine.parse_case(raw)
        cases.append((label, case, (0, case.full, 5, 1)))
    # Identical admitted cases, masks, counter contract, result construction and
    # reversal work; the independent reference does not call engine routines.
    gate = workload(reference, cases, collect=True)
    same(gate, workload(engine, cases, collect=True), 'complete workload equality')
    for record in gate['records']:
        raw = raw_by_label[record['fixture']]
        expected = oracle.execute(raw, record['mask'])
        outcome = record['outcome']
        same(None if outcome is None else outcome['end'], expected, 'direct replay')
        if outcome is not None:
            checker.check(raw, {'kind': 'success', 'outcome': outcome})

    modules = {'scan_reference': reference, 'event_local_engine': engine}
    same(workload(reference, cases), workload(engine, cases), 'untimed warmup')
    samples = []
    for index in range(args.rounds):
        order = ('scan_reference', 'event_local_engine') if index % 2 == 0 else (
            'event_local_engine', 'scan_reference')
        sample = dict(round=index + 1, order=list(order), nanoseconds={})
        blocks = {}
        for name in order:
            start = time.perf_counter_ns()
            blocks[name] = workload(modules[name], cases, args.passes)
            sample['nanoseconds'][name] = time.perf_counter_ns() - start
        same(blocks['scan_reference'], blocks['event_local_engine'], 'timed counters and counts')
        sample['queries_per_version'] = blocks['event_local_engine']['queries']
        samples.append(sample)
    description.update(equality_gate_passed=True,
                       regression=regression, workload_successes=gate['successes'],
                       workload_failures=gate['failures'], workload_counters=gate['counters'],
                       samples=samples, python=sys.version,
                       environment=dict(system=platform.platform(), processor=platform.processor(),
                                        logical_cpus=os.cpu_count(),
                                        clock_resolution_seconds=time.get_clock_info('perf_counter').resolution,
                                        cpu_affinity=None))
    print(json.dumps(description, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
