"""Self-contained, untimed fixture/API/oracle/checker regression.

Only standard-library computation and source reads are used. No saved results,
resource/fault drivers, subprocesses, network calls, or benchmark timers are used.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import unittest

ARTIFACT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError('cannot load reviewed source: ' + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def runtimes():
    return (
        load_module('p003_guard_scan', ARTIFACT / 'tests' / 'guard_scan_reference.py'),
        load_module('p003_guard_candidate', ARTIFACT / 'src' / 'engine.py'),
        load_module('p003_guard_generate', ARTIFACT / 'src' / 'generate.py'),
        load_module('p003_guard_checker', ARTIFACT / 'src' / 'checker.py'),
        load_module('p003_guard_oracle', ARTIFACT / 'src' / 'oracle.py'),
    )


def wide_case(generate, width, mode):
    if mode not in ('singleton', 'nonsingleton', 'unguarded', 'unit_domain'):
        raise ValueError('unknown inference mode')
    domains = [1 if mode == 'unit_domain' else 3] * width
    events = []
    for i in range(8):
        if mode == 'singleton':
            guard = {x: [i % 3] for x in range(width)}
        elif mode == 'nonsingleton':
            guard = {x: [0, 1, 2] for x in range(width)}
        else:
            guard = {}
        value = 0 if mode == 'unit_domain' else (i + 1) % 3
        events.append(generate.ev(i % 4, guard, dict.fromkeys(range(width), value)))
    return generate.make([0] * width, events, 4, domains)


def mixed_case(generate, width):
    if width % 4:
        raise ValueError('mixed width must be a multiple of four')
    domains = [3, 3, 1, 3] * (width // 4)
    events = []
    for i, tag in enumerate((0, 1, 2, 0)):
        guard = {x: ([i % 3] if x % 4 == 0 else [0, 1, 2])
                 for x in range(width) if x % 4 in (0, 1)}
        write = {x: (0 if domains[x] == 1 else (i + 1) % 3)
                 for x in range(width)}
        events.append(generate.ev(tag, guard, write))
    return generate.make([0] * width, events, 3, domains)


def multiwrite_cases(generate, widths):
    cases = []
    for width in widths:
        for mode in ('singleton', 'nonsingleton', 'unguarded', 'unit_domain'):
            cases.append((f'wide-{width}-{mode}', wide_case(generate, width, mode)))
        cases.append((f'mixed-{width}', mixed_case(generate, width)))
    return cases


def bounded_variants(generate):
    cases = multiwrite_cases(generate, (4, 8, 16, 32))
    graph = generate.make([1, 1, 1, 0, 0], [
        generate.ev(0, {0: [1], 1: [1], 2: [1], 3: [0, 1, 2]},
                    {0: 0, 2: 0, 3: 1, 4: 0}),
        generate.ev(1, {1: [1], 3: [0, 1, 2]}, {0: 1, 2: 1, 3: 2}),
        generate.ev(0, {1: [1], 3: [0, 1, 2]}, {0: 0, 2: 0, 3: 1, 4: 0}),
    ], 2, [2, 2, 2, 3, 1], [0, 1], [[2, 0, 1]])
    cases.append(('atomic-edge-endpoint-and-attribute', graph))
    cases.append(('zero-tags-zero-events', generate.make([0], [], 0, [1])))
    cases.append(('guard-only-empty-write', generate.make([0, 0], [
        generate.ev(0, {0: [0, 1], 1: [0]}, {}),
        generate.ev(1, {0: [0], 1: [0]}, {}),
    ], 2, [2, 1])))
    reordered = copy.deepcopy(mixed_case(generate, 8))
    for event in reordered['events']:
        event['guard'].reverse()
        event['write'].reverse()
        for _, allowed in event['guard']:
            allowed.reverse()
    cases.append(('reordered-maps-and-guard-sets', reordered))
    return cases


def capture(module, function, *args):
    module.COUNTS.clear()
    value = function(*args)
    return value, dict(module.COUNTS)


def run_regression():
    reference, candidate, generate, checker, oracle = runtimes()
    named = list(generate.named().items())
    variants = bounded_variants(generate)
    metrics = dict(named_fixtures=0, variant_fixtures=0, named_masks=0,
                   variant_masks=0, success_masks=0, failure_masks=0,
                   receipt_occurrences=0, old_pairs=0, public_api_calls=0,
                   checker_calls=0)

    class GuardLookupRegression(unittest.TestCase):
        def exact(self, left, right):
            # Serialized comparison preserves list order AND JSON numeric types.
            self.assertEqual(type(left), type(right))
            self.assertEqual(json.dumps(left, separators=(',', ':')),
                             json.dumps(right, separators=(',', ':')))

        def compare_cases(self, cases, group):
            for label, raw in cases:
                with self.subTest(fixture=label):
                    original = copy.deepcopy(raw)
                    case = candidate.parse_case(raw)
                    canonical = copy.deepcopy(case.to_dict())
                    metrics[group + '_fixtures'] += 1
                    for mask in range(case.full + 1):
                        with self.subTest(mask=mask):
                            expected_out, reference_counts = capture(reference, reference.replay, case, mask)
                            actual_out, actual_counts = capture(candidate, candidate.replay, case, mask)
                            self.exact(expected_out, actual_out)
                            self.exact(reference_counts, actual_counts)
                            expected = oracle.execute(raw, mask)
                            self.assertEqual(actual_out is None, expected is None)
                            metrics[group + '_masks'] += 1
                            if actual_out is None:
                                metrics['failure_masks'] += 1
                                continue
                            self.exact(actual_out['end'], expected)
                            selected = [i for i, event in enumerate(case.events)
                                        if mask >> event.tag & 1]
                            self.exact([r['at'] for r in actual_out['receipts']], selected)
                            reference_snapshot = copy.deepcopy(expected_out)
                            actual_snapshot = copy.deepcopy(actual_out)
                            expected_base, reference_counts = capture(reference, reference.reverse, case, expected_out)
                            actual_base, actual_counts = capture(candidate, candidate.reverse, case, actual_out)
                            self.exact(expected_base, actual_base)
                            self.exact(reference_counts, actual_counts)
                            self.assertEqual(expected_base, case.base)
                            self.assertEqual(actual_base, case.base)
                            self.exact(expected_out, reference_snapshot)
                            self.exact(actual_out, actual_snapshot)
                            expected_check, reference_counts = capture(
                                checker, checker.check, raw, {'kind': 'success', 'outcome': expected_out})
                            actual_check, actual_counts = capture(
                                checker, checker.check, raw, {'kind': 'success', 'outcome': actual_out})
                            self.exact(expected_check, actual_check)
                            self.exact(reference_counts, actual_counts)
                            self.assertIs(actual_check['accepted'], True)
                            metrics['success_masks'] += 1
                            metrics['checker_calls'] += 2
                            metrics['receipt_occurrences'] += len(actual_out['receipts'])
                            metrics['old_pairs'] += sum(len(r['old']) for r in actual_out['receipts'])
                    self.exact(raw, original)
                    self.exact(case.to_dict(), canonical)

        def test_named_fixtures(self):
            self.compare_cases(named, 'named')

        def test_bounded_multiwrite_variants(self):
            self.compare_cases(variants, 'variant')

        def test_public_inferred_old_api(self):
            self.assertEqual(list(inspect.signature(candidate.inferred_old).parameters),
                             ['case', 'event', 'x'])
            self.assertTrue(all(p.default is inspect.Parameter.empty for p in
                                inspect.signature(candidate.inferred_old).parameters.values()))
            for label, raw in named + variants:
                with self.subTest(fixture=label):
                    case = candidate.parse_case(raw)
                    for event in case.events:
                        for x, domain in enumerate(case.domains):
                            expected = reference.inferred_by_scan(domain, event.guard, x)
                            actual, actual_counts = capture(candidate, candidate.inferred_old, case, event, x)
                            self.exact(actual, expected)
                            self.assertEqual(actual_counts, {})
                            metrics['public_api_calls'] += 1

        def test_hand_written_receipt_and_counter_anchors(self):
            case = candidate.parse_case(mixed_case(generate, 4))
            expected = {'mask': 7, 'end': [1, 1, 0, 1], 'receipts': [
                {'at': 0, 'old': [[1, 0], [3, 0]]},
                {'at': 1, 'old': [[1, 1], [3, 1]]},
                {'at': 2, 'old': [[1, 2], [3, 2]]},
                {'at': 3, 'old': [[1, 0], [3, 0]]},
            ]}
            for module in (reference, candidate):
                outcome, counts = capture(module, module.replay, case, 7)
                self.exact(outcome, expected)
                self.exact(counts, {'event_visits': 4, 'guard_tests': 8, 'write_updates': 16})
                restored, counts = capture(module, module.reverse, case, outcome)
                self.exact(restored, (0, 0, 0, 0))
                self.exact(counts, {'inverse_event_visits': 4})
                outcome, counts = capture(module, module.replay, case, 0)
                self.exact(outcome, {'mask': 0, 'end': [0, 0, 0, 0], 'receipts': []})
                self.exact(counts, {'event_visits': 4})
                outcome, counts = capture(module, module.replay, case, 1)
                self.assertIsNone(outcome)
                self.exact(counts, {'event_visits': 4, 'guard_tests': 3, 'write_updates': 4})

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuardLookupRegression)
    names = [test._testMethodName for test in suite]
    result = unittest.TestResult()
    suite.run(result)
    return dict(passed=result.wasSuccessful(), tests_run=result.testsRun, tests=names,
                coverage=metrics, failures=[detail for _, detail in result.failures],
                errors=[detail for _, detail in result.errors],
                comparison_reference='independent per-coordinate guard scan',
                benchmark_timing_run=False, saved_results_written=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = run_regression()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
