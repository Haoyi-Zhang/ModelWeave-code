"""Encode finite named guarded patches; no source-tool extraction or evaluation.

Each patch is atomic: test all requirements, then assign literal values together.
Labels couple patch occurrences. Values and addresses are explicit strings, not
expressions or paths to external objects. The compiler changes names to codes only.
"""
from __future__ import annotations
from typing import Any
from engine import Invalid, parse_case


def compile_updates(program: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return an admitted raw case and the bijections needed to decode its states.

    The source schema is domains/base/labels/patches. A patch has exactly
    label/require/assign, where require maps names to nonempty value lists and
    assign maps names to constant values. Declared ordering determines codes.
    """
    if type(program) is not dict or set(program) != {'domains', 'base', 'labels', 'patches'}:
        raise Invalid('named program fields')
    domains, base = program['domains'], program['base']
    labels, patches = program['labels'], program['patches']
    if type(domains) is not dict or not 1 <= len(domains) <= 512:
        raise Invalid('named cell count')
    for name, values in domains.items():
        if type(name) is not str or not name or type(values) is not list or not 1 <= len(values) <= 256:
            raise Invalid('named domain')
        if any(type(v) is not str or not v for v in values) or len(set(values)) != len(values):
            raise Invalid('domain values must be distinct nonempty names')
    if type(base) is not dict or set(base) != set(domains):
        raise Invalid('named base fields')
    if any(type(v) is not str or v not in domains[x] for x, v in base.items()):
        raise Invalid('named base value')
    if type(labels) is not list or len(labels) > 12 or any(type(a) is not str or not a for a in labels):
        raise Invalid('named labels')
    if len(set(labels)) != len(labels):
        raise Invalid('duplicate named label')
    if type(patches) is not list or len(patches) > 96:
        raise Invalid('named patch count')
    cells = list(domains)
    cell_code = {name: i for i, name in enumerate(cells)}
    label_code = {name: i for i, name in enumerate(labels)}
    value_code = {name: {v: i for i, v in enumerate(values)} for name, values in domains.items()}
    events = []
    for patch in patches:
        if type(patch) is not dict or set(patch) != {'label', 'require', 'assign'}:
            raise Invalid('named patch fields')
        label, require, assign = patch['label'], patch['require'], patch['assign']
        if type(label) is not str or label not in label_code:
            raise Invalid('unknown named label')
        if type(require) is not dict or type(assign) is not dict:
            raise Invalid('named patch maps')
        guard, write = [], []
        for name, values in require.items():
            if name not in cell_code or type(values) is not list or not values:
                raise Invalid('named requirement')
            if any(type(v) is not str or v not in value_code[name] for v in values):
                raise Invalid('named requirement value')
            if len(set(values)) != len(values):
                raise Invalid('duplicate requirement value')
            guard.append([cell_code[name], sorted(value_code[name][v] for v in values)])
        for name, value in assign.items():
            if name not in cell_code or type(value) is not str or value not in value_code[name]:
                raise Invalid('named assignment')
            write.append([cell_code[name], value_code[name][value]])
        events.append({'tag': label_code[label], 'guard': sorted(guard), 'write': sorted(write)})
    raw = {'domains': [len(domains[x]) for x in cells], 'nodes': [], 'edges': [],
           'base': [value_code[x][base[x]] for x in cells], 'aspects': len(labels), 'events': events}
    # Apply the existing caps and executable-full-history premise. No new parser
    # policy is introduced for the certificate checker.
    parse_case(raw)
    return raw, {'cells': cells, 'labels': labels[:], 'values': [domains[x][:] for x in cells]}


def decode_state(coding: dict[str, Any], values: list[int]) -> dict[str, str]:
    if len(values) != len(coding['cells']):
        raise Invalid('encoded state length')
    result = {}
    for i, name in enumerate(coding['cells']):
        value = values[i]
        if type(value) is not int or not 0 <= value < len(coding['values'][i]):
            raise Invalid('encoded state value')
        result[name] = coding['values'][i][value]
    return result


def compile_positive_actions(program: dict[str, Any]) -> tuple[
        set[tuple[str, str]],
        list[tuple[str, set[tuple[str, str]], set[tuple[str, str]], set[tuple[str, str]]]]]:
    """Compile singleton/full-domain guarded patches to positive STRIPS actions.

    One proposition (cell, value) represents each domain member. A constant
    assignment adds its value and deletes every alternative value of that cell.
    Action occurrences retain the source order and label coupling; this function
    does not grant a planner permission to insert, reorder, or repeat actions.
    Proper nonsingleton requirements need disjunction and are rejected, not
    approximated. The named-program admission checks, including full execution,
    are the same as those for the trace compiler.
    """
    compile_updates(program)
    initial = set(program['base'].items())
    actions = []
    for patch in program['patches']:
        pre = set()
        for name, allowed in patch['require'].items():
            if set(allowed) == set(program['domains'][name]):
                continue
            if len(allowed) != 1:
                raise Invalid('positive actions require singleton or full-domain guards')
            pre.add((name, allowed[0]))
        add = set(patch['assign'].items())
        delete = {(name, other) for name, value in patch['assign'].items()
                  for other in program['domains'][name] if other != value}
        actions.append((patch['label'], pre, add, delete))
    return initial, actions
