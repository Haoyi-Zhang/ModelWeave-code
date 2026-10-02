"""Original constructions for expressivity and the one/two-writer boundary.

These functions construct finite, benign trace inputs. They neither invoke a
solver nor form part of the independent checker. The general results are proved
in proofs/semantics.md; executable experiments remain bounded.
"""
from __future__ import annotations
from typing import Any
from engine import Case, Invalid
from generate import make, ev


def realize_clauses(m: int, clauses: list[tuple[list[int], list[int]]]) -> dict[str, Any]:
    """Realize mixed clauses with one or two negative aspect literals.

Each pair is (negative tags, positive tags), all variables distinct within a
clause. Fresh Boolean cells prevent unintended cross-clause interference.
"""
    if type(m) is not int or not 0 <= m <= 12:
        raise ValueError('aspect bound is 0..12')
    events = []
    for cell, (negative, positive) in enumerate(clauses):
        if not 1 <= len(negative) <= 2 or not positive:
            raise ValueError('need one/two negative and at least one positive literal')
        values = negative + positive
        if any(type(a) is not int or not 0 <= a < m for a in values) or len(set(values)) != len(values):
            raise ValueError('clause tags must be distinct and in range')
        reader = negative[0]
        if len(negative) == 1:
            for a in positive:
                events.append(ev(a, {}, {cell: 1}))
            events.append(ev(reader, {cell: [1]}, {}))
        else:
            events.append(ev(negative[1], {}, {cell: 1}))
            for a in positive:
                events.append(ev(a, {}, {cell: 0}))
            events.append(ev(reader, {cell: [0]}, {}))
    if len(events) > 96 or len(clauses) > 512:
        raise ValueError('construction exceeds artifact admission bounds')
    # A dummy cell handles the valid empty conjunction without changing tags.
    return make([0] * max(1, len(clauses)), events, m, [2] * max(1, len(clauses)))


def writer_counts(case: Case) -> list[int]:
    result = [0] * len(case.base)
    for event in case.events:
        for cell, _ in event.write:
            result[cell] += 1
    return result


def one_writer_edges(case: Case) -> list[tuple[int, int]]:
    """Compute exact keep(reader) => keep(writer) requirements, when admitted."""
    if max(writer_counts(case), default=0) > 1:
        raise Invalid('not the at-most-one-write-per-cell fragment')
    prior: dict[int, int] = {}
    edges = set()
    for event in case.events:
        for cell, allowed in event.guard:
            if case.base[cell] not in allowed:
                if cell not in prior:
                    raise Invalid('the supplied original trace is not executable')
                writer = prior[cell]
                if writer != event.tag:
                    edges.add((event.tag, writer))
        for cell, _ in event.write:
            prior[cell] = event.tag
    return sorted(edges)


def one_writer_completion(case: Case, on: int, off: int) -> int | None:
    """Unique maximum valid retention extending a policy, or None.

All optional costs are one. Blocking every dependent of a forced-absent tag
therefore gives the minimum collateral deletion count without search.
"""
    if type(on) is not int or type(off) is not int or min(on, off) < 0 or on & off or (on | off) & ~case.full:
        raise Invalid('invalid partial retention policy')
    edges = one_writer_edges(case)
    blocked = off
    while True:
        previous = blocked
        for reader, writer in edges:
            if blocked & (1 << writer):
                blocked |= 1 << reader
        if previous == blocked:
            break
    return None if on & blocked else case.full & ~blocked


def two_writer_sat(n: int, formula: list[list[int]]) -> tuple[dict[str, Any], int, int]:
    """3-CNF feasibility with <=2 writes/cell and exactly one event/aspect.

Nonempty clauses of width <=3 are padded by repeated literals. A binary OR
auxiliary event per clause replaces the three-provider cell in the basic gadget.
"""
    h = len(formula)
    m = 2 * n + h + 2
    if type(n) is not int or not 1 <= n or m > 12:
        raise ValueError('construction exceeds the twelve-aspect bound')
    if any(not 1 <= len(c) <= 3 or any(type(l) is not int or not 1 <= abs(l) <= n for l in c) for c in formula):
        raise ValueError('expected nonempty clauses of width at most three')
    padded = [c + [c[-1]] * (3 - len(c)) for c in formula]
    d = 2 * n
    reader = m - 1
    writes = [{i: 1, n + i: 1} for i in range(n)] + [{n + i: 1} for i in range(n)]
    for j, clause in enumerate(padded):
        root, child = 2 * n + 2 * j, 2 * n + 2 * j + 1
        for k, lit in enumerate(clause):
            tag = lit - 1 if lit > 0 else n + (-lit - 1)
            writes[tag][root if k == 0 else child] = 1
    events = [ev(i, {}, writes[i]) for i in range(n)]
    events.append(ev(d, {}, dict.fromkeys(range(n), 0)))
    events += [ev(n + i, {i: [0]}, writes[n + i]) for i in range(n)]
    for j in range(h):
        events.append(ev(d + 1 + j, {2 * n + 2 * j + 1: [1]}, {2 * n + 2 * j: 1}))
    guards = dict.fromkeys(range(n, 2 * n), [1])
    guards.update({2 * n + 2 * j: [1] for j in range(h)})
    events.append(ev(reader, guards, {}))
    cells = 2 * n + 2 * h
    return make([0] * cells, events, m, [2] * cells), 1 << reader, 1 << d


def binary_choice_tree(leaves: int) -> tuple[dict[str, Any], int, int]:
    """An OR tree with ternary local obstructions but a (leaves+1)-fact core."""
    if type(leaves) is not int or not 2 <= leaves <= 6:
        raise ValueError('two through six leaves fit the artifact bound')
    queue = list(range(leaves)); children: dict[int, tuple[int, int]] = {}
    parent: dict[int, int] = {}
    while len(queue) > 1:
        a, b = queue.pop(0), queue.pop(0)
        p = leaves + len(children)
        children[p] = (a, b)
        parent[a] = parent[b] = p
        queue.append(p)
    root = queue[0]
    cells = {p: p - leaves for p in children}
    events = []
    for a in range(root + 1):
        guard = {} if a < leaves else {cells[a]: [1]}
        write = {} if a == root else {cells[parent[a]]: 1}
        events.append(ev(a, guard, write))
    return make([0] * (leaves - 1), events, root + 1, [2] * (leaves - 1)), 1 << root, (1 << leaves) - 1
