"""Test-only scalar guard-scan semantics for admitted cases.

Inputs are admitted Case-like values. Admission is tested by the actual parser
and checker, not implemented here. This reference calls no engine routines and
performs a fresh linear guard scan for each written coordinate. Counter names
describe the engine's event/guard/write contract, not lookup allocation costs.
"""
from __future__ import annotations

COUNTS: dict[str, int] = {}


class ReferenceError(ValueError):
    pass


def count(name):
    COUNTS[name] = COUNTS.get(name, 0) + 1


def inferred_by_scan(domain, guard, cell):
    for guarded_cell, accepted in guard:
        if guarded_cell == cell:
            if len(accepted) == 1:
                return accepted[0]
            break
    return 0 if domain == 1 else None


def replay(case, mask):
    if type(mask) is not int or not 0 <= mask <= case.full:
        raise ReferenceError('invalid retention mask')
    values = list(case.base)
    receipts = []
    for position, event in enumerate(case.events):
        count('event_visits')
        if not mask & (1 << event.tag):
            continue
        for cell, accepted in event.guard:
            count('guard_tests')
            if values[cell] not in accepted:
                return None
        saved = []
        for cell, _ in event.write:
            count('write_updates')
            if inferred_by_scan(case.domains[cell], event.guard, cell) is None:
                saved.append([cell, values[cell]])
        for cell, constant in event.write:
            values[cell] = constant
        receipts.append({'at': position, 'old': saved})
    return {'mask': mask, 'end': values, 'receipts': receipts}


def reverse(case, outcome):
    values = list(outcome['end'])
    for receipt in outcome['receipts'][::-1]:
        count('inverse_event_visits')
        event = case.events[receipt['at']]
        saved = {cell: value for cell, value in receipt['old']}
        for cell, constant in event.write:
            if values[cell] != constant:
                raise ReferenceError('inverse postcondition failed')
        for cell, _ in event.write:
            inferred = inferred_by_scan(case.domains[cell], event.guard, cell)
            values[cell] = saved[cell] if inferred is None else inferred
        for cell, accepted in event.guard:
            if values[cell] not in accepted:
                raise ReferenceError('inverse observation failed')
    return tuple(values)
