"""Fixed-sequence SAS+ supporter clauses and whole-label trace coding.

The achiever/opposer encoding follows Balyo, Chrpa and Kilani (SoCS 2014),
as restated in Salerno, Fuentetaja and Seipp (JAIR 2025), Appendix A.
Only equality preconditions and simultaneous constant effects are admitted.
This module constructs formulas; it is not an external planner or MaxSAT solver.
"""
from __future__ import annotations

from typing import Any

from engine import Invalid
from update_language import compile_updates


def compile_sas(task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Code source coordinates directly, preserving all original occurrences.

The fields are domains/base/labels/actions/goal. Each action has label/pre/eff;
pre and eff are partial assignments, not membership lists or expressions.
A nonempty goal adds one write-free fresh-label read and returns its keep bit.
    That explicit goal label is not an original source label or an optional cost.
    Admission requires an executable full source plan reaching its goal, and
    the coded case (including the terminal label/event) must fit engine bounds.
    This is valid-plan deletion, not arbitrary planning-task compilation.
"""
    if type(task) is not dict or set(task) != {'domains', 'base', 'labels', 'actions', 'goal'}:
        raise Invalid('SAS task fields')
    if type(task['actions']) is not list or type(task['goal']) is not dict or type(task['labels']) is not list:
        raise Invalid('SAS actions, labels, or goal')
    patches = []
    for action in task['actions']:
        if type(action) is not dict or set(action) != {'label', 'pre', 'eff'}:
            raise Invalid('SAS action fields')
        if type(action['pre']) is not dict or type(action['eff']) is not dict:
            raise Invalid('SAS partial assignment maps')
        if any(type(v) is not str for v in action['pre'].values()):
            raise Invalid('SAS preconditions must be literal equalities')
        patches.append({'label': action['label'],
                        'require': {x: [v] for x, v in action['pre'].items()},
                        'assign': dict(action['eff'])})
    labels = list(task['labels'])
    terminal = 0
    if task['goal']:
        if any(type(v) is not str for v in task['goal'].values()):
            raise Invalid('SAS goal must be literal equalities')
        name = '__terminal_goal__'
        while name in labels:
            name += '_'
        terminal = 1 << len(labels)
        labels.append(name)
        patches.append({'label': name, 'require': {x: [v] for x, v in task['goal'].items()}, 'assign': {}})
    raw, coding = compile_updates({'domains': task['domains'], 'base': task['base'],
                                   'labels': labels, 'patches': patches})
    return raw, coding, terminal


def encode_supporters(task: dict[str, Any]) -> dict[str, Any]:
    """Return action variables, fresh existential options, and signed CNF clauses.

Source positions are zero-based. A read at i sees writes at j<i, and a terminal
goal is read at i=n. The virtual base source is -1 and is present as an option
only when its value satisfies the required equality. Threats use j<k<i.
Options imply their support conditions; no converse or exactly-one rule is added.
"""
    compile_sas(task)  # Admission only; clause construction below uses source maps.
    actions = task['actions']
    n = len(actions)
    clauses: list[list[int]] = []
    options: list[dict[str, Any]] = []
    observations = []

    def observation(at: int, cell: str, value: str, reader: int | None) -> None:
        local = []
        candidates = ([-1] if task['base'][cell] == value else [])
        candidates += [j for j in range(at) if actions[j]['eff'].get(cell) == value]
        variables = []
        for source in candidates:
            variable = n + len(options) + 1
            variables.append(variable)
            threats = [k for k in range(source + 1, at)
                       if cell in actions[k]['eff'] and actions[k]['eff'][cell] != value]
            options.append({'variable': variable, 'at': at, 'cell': cell,
                            'value': value, 'source': source, 'threats': threats})
            if source >= 0:
                local.append([-variable, source + 1])
            local.extend([-variable, -(k + 1)] for k in threats)
        # An inactive action imposes no demand. A terminal goal is unconditional.
        local.append(([] if reader is None else [-(reader + 1)]) + variables)
        observations.append({'at': at, 'cell': cell, 'value': value,
                             'reader': reader, 'clauses': local})
        clauses.extend(local)

    for i, action in enumerate(actions):
        for cell, value in action['pre'].items():
            observation(i, cell, value, i)
    for cell, value in task['goal'].items():
        observation(n, cell, value, None)
    return {'action_variables': list(range(1, n + 1)), 'options': options,
            'clauses': clauses, 'observations': observations,
            'source_positions': 'zero-based; base=-1; terminal read=n',
            'supporter_quantifier': 'exists'}


def occurrence_mask(task: dict[str, Any], label_mask: int) -> int:
    """Substitute one selection bit for every occurrence of the same source label."""
    if type(label_mask) is not int or not 0 <= label_mask < (1 << len(task['labels'])):
        raise Invalid('source label mask')
    codes = {label: i for i, label in enumerate(task['labels'])}
    return sum(1 << i for i, action in enumerate(task['actions'])
               if label_mask & (1 << codes[action['label']]))
