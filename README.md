# Observation-stable model unweaving artifact

This directory is a standalone executable artifact for the paper
*Observation-Stable Model Unweaving: A One-Write/Two-Write Boundary*.
It uses only the Python standard library and does not require `paper/`.

## Exact scope

The implemented and proved fragment has a finite typed cell catalog, fixed event
order and fixed matches, explicit unary observations, simultaneous constant
overwrite events, and one keep/erase decision per tag. Keeping a tag keeps all of
its event occurrences in their original order. There is no rematching, fresh
identity creation, hidden read, concurrency, external effect, arbitrary graph
rewrite, or production-tool claim.

The central boundary is precise: policy feasibility is polynomial in the
one-write-per-cell fragment, and NP-complete with at most two writes per cell even
when each aspect has exactly one event, cells are Boolean, and there is one forced
keep and one forced removal. A single event may touch polynomially many cells; no
constant-arity hardness result is claimed.

## Named updates and fixed-sequence actions

`src/update_language.py` accepts declared named cells/domains, a base state,
labels, and ordered `label/require/assign` patches. Requirements are unary value
lists; assignments are constants applied atomically after all requirements pass.
`compile_updates` codes names without adding occurrences or changing writer
counts. `compile_positive_actions` additionally supports singleton/full-domain
requirements using one value proposition per domain member and positive
precondition/add/delete sets. Proper nonsingleton requirements are rejected by
the action interface, not approximated. Both require an executable full history.
Selection retains source order and all occurrences of a label; the action output
does not permit a planner to insert, repeat, or reorder occurrences.

Written preservation arguments are L27--L28 in `proofs/semantics.md`. They specify
a closed update interface, not a production extractor or a new planning formalism.
L29 gives the exact mixed Horn/dual-Horn gadget CNF and its helper projection under
the keep-reader/remove-reset request. Choice alone is not the hardness mechanism.

Portable focused checks, with no third-party planner:

The three named-update/supporter scientific entry points require enabled Python
assertions and refuse `-O` before evaluating fixtures or emitting a pass record.
`tests/test_assertion_gate.py` checks that execution contract in both modes;
optimized execution of the scientific entries is a refusal, not extra evidence.

```sh
python -B tests/test_update_bridge.py
python -B tests/test_update_contract.py
```

The prior six-example record is `results/update-language/summary.json` (44 masks,
144 partial policies). `results/update-contract/summary.json` stores eight new
owned programs in two code orderings (70 masks, 62 action comparisons, 80 one-write
policies), and 75 gadget formulas with 4,880 target masks and 154 assignment/helper
projections. These are separate regressions, not additions to the campaign or
published-source projections. To save a new contract result, add `--output` with
a fresh file path inside P003; omitting it writes nothing.

## Closest SAS+ encoding correspondence

`src/sas_supporters.py` constructs the existing supporter/opposer feasibility
encoding for a supplied valid full SAS+ plan with equality preconditions and
constant effects. The full plan must execute and reach its goal. Both construction
APIs enforce the coded-case bounds; invalid histories and unreached goals are
rejected. Proper nonsingleton guards, conditional effects and computed assignments
are outside this mapping. Source finite domains remain cells; idempotent and
repeated-label writer occurrences are preserved, not one-hot effect counts.

Supporters are existential and need not be unique. Base support exists only
when the base equality holds; opponents use the strict interval j<k<i. All
occurrences of a label share its retention bit. A nonempty terminal goal adds
one fresh, mandatory write-free label, not an optional action or artificial cost.
That addition does not preserve general keep-fact cardinality; the two-write
construction has an empty goal and its existing forced reader is unchanged.
L30--L31 and paper Appendix SAS+ Supporters prove the bounded-interface
correspondence. The mathematical statements concern arbitrary finite valid full
plans; executable size bounds are additional admission controls.

`python -B tests/test_supporter_equivalence.py` runs nine hand-written models
and writes nothing unless a fresh `--output` file is supplied.
`results/supporter-correspondence/summary.json` stores their complete source
tasks, coded traces, options/clauses, writer counts, 45 mask results, 50 local
projections, 133 partial-request comparisons and ten named rejections.
Source, encoding and trace paths enforce identical obligations. No published
tool is executed; no cost or timing win is claimed. The local prime profile is
not a globally prime trace CNF. Prior coverage of the joint two-write restriction
remains unknown; inherited encoding and label binding are not originality claims.

Primary sources (complete articles checked):
[Balyo, Chrpa and Kilani, SoCS 2014](https://ktiml.mff.cuni.cz/~balyo/papers/socs14.pdf),
[Salerno, Fuentetaja and Seipp, JAIR 2025](https://mrlab.ai/papers/salerno-et-al-jair2025.pdf).

## Reproduce

Run from this directory with Python 3.10 or newer and a new output directory.
Linux and native Windows are supported. The driver sets deterministic seed/hash
environment values and disables bytecode writes. Children run sequentially with
a 45-minute wall timeout. POSIX hosts additionally apply the existing 2500 MiB
address-space and 45-minute CPU limits. Native Windows does not claim these
unavailable limits; child CPU and RSS are JSON null, not fabricated zero. Available
RSS is normalized to KiB (including macOS byte-to-KiB conversion).

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python3 reproduce_all.py --output /tmp/unweave-reproduction
```

The current runner executes 20 sequential command phases: untimed event-local
guard, named-update bridge, update contract, SAS+ supporter correspondence,
semantic and structural tests,
source-guided projections, three pilots, the 50-chunk campaign, five independent
checker batches, coverage regeneration, an example check, a policy query, and an
independent check of that query. It refuses an existing output directory. No
network, GPU, external model API, non-standard package, or parallel worker is used.

The GitHub Actions workflow in `.github/workflows/scientific-checks.yml` runs
the full reproduction on `ubuntu-latest` with Python 3.12, using a fresh output
directory under `RUNNER_TEMP`. It uploads the complete output tree, including
raw compressed JSONL records and logs, without changing scientific seeds or
resource limits.

The three previously separate CI checks are now part of this default command.
Their exact saved correspondence records (and the added SAS+ record) are checked
in the driver; guard coverage is required to pass without running its timer.
Native Windows invocation:

```powershell
python -B reproduce_all.py --output D:/path/to/nonexistent-output
```

Useful focused commands (use fresh output paths):

```sh
python3 tests/test_semantics.py /tmp/semantic-tests.json
python3 tests/test_structural.py /tmp/structural-tests
python3 tests/test_examples.py /tmp/source-examples
python3 verify.py results/examples/example-03.json
```

The independent verifier does not import the resource helper and can check
stored packets on native Windows with Python 3.10 or newer:

```powershell
python -B verify.py results/examples/example-03.json
```

The event-local guard index has a portable comparison against an independent
per-coordinate scan. `python -B tests/test_event_local_guard.py` runs the
35-fixture, 429-mask regression and four hand-written outcome/counter anchors.
`python -B benchmarks/benchmark_guard_lookup.py --describe` prints the timing
protocol; `--run-serial-timing` executes it and prints all samples. Run timing
alone, not concurrently with other benchmarks.

`results/guard-lookup/measurement.json` records five alternating paired blocks
over 20 mixed wide fixtures, 160 queries per arm per block. The median scan-to-index
ratio is 8.70 (block ratios 8.05--9.80). This times replay and successful reversal,
not parsing, certificate checking, producer search, or production tools. The
measurement uses Python 3.12.14 on Windows 11, one worker, and no CPU pinning.
Absent-guard, empty-mask, and ordinary guard-failure cases remain in the mixture.

## Manuscript reproduction commands

The article gives the reproduction protocol in prose; the exact corresponding
commands are retained here. Run the scientific commands from this artifact root
on Linux, using output paths that do not exist:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python3 reproduce_all.py --output /tmp/weaving-clean
python3 tests/test_semantics.py /tmp/tests.json
python3 tests/test_structural.py /tmp/structural
python3 tests/test_examples.py /tmp/examples
```

The first command is the complete reproduction; the remaining three are focused
diagnostics and do not replace it. For the article PDF, run from the sibling
`paper/` directory:

```sh
make clean
make all
make check
```

## Recorded evidence

- 50,000 deterministic campaign packets and 231,071 direct replay queries.
- 49,526 successful certificates and 474 local-obstruction certificates.
- 23,461 successful packets execute at least one retained event occurrence;
  49,861 occurrence receipts are checked.
- 421 structural inputs: 46 clause forms, 64 conjunctions, 32 one-write cases,
  274 one-event-per-aspect two-write SAT reductions, and 5 choice trees.
- 8 semantic test methods, including the fixed-mask minimum-fact regression:
  `{r,b2,not g2}` is accepted while the four-fact inclusion-minimal but
  nonminimum set `{r,b1,not g1,not g2}` is rejected.
- 19 deliberately inconsistent mutations rejected; one coordinated input-and-
  certificate change accepted, documenting the packet-origin trust boundary.
- Six small source-guided projections from five published passages or figures;
  they are not production benchmarks and no upstream tool was executed.

The two historical full runs passed 16 phases and produced equal scientific
records after excluding runtime telemetry. See `results/final-validation/`;
these records and their timings are retained unchanged.

The current 20-phase run is a separate correctness receipt in
`results/current-reproduction/clean-run.json`, with its complete raw fresh output
tree alongside it, including all 50 campaign streams and the three correspondence
JSON outputs. It compares 50,000 semantic records and independently checks 50,000
packets, plus the existing structural/source records and the new source obligations.
It does not replace historical measurements or prove an unbounded theorem.

## Evidence boundary

The written arguments are in `proofs/semantics.md`; executable tests are finite
falsification and certificate-replay evidence. Neither is described as Lean, Coq,
Isabelle, or other proof-assistant mechanization. The independent checker is a
separate implementation path, but not independent authorship or cryptographic
source authentication.

## Map

- `src/`: engine, producer, checker, direct oracle, generators, and reductions.
- `src/update_language.py`: named-patch and restricted positive-action coding.
- `src/sas_supporters.py`: equality SAS+ source coding and existential supporter clauses.
- `tests/`: semantic, structural, source-projection, mutation, and pilot tests.
- `proofs/semantics.md`: definitions and written proofs T1--T26, L27--L31.
- `results/`: campaign records, summaries, examples, and comparison measurements.
- `docs/`: schema, proof/code map, reproduction, resources, evidence limits, and audit.
- `claim_evidence_ledger.csv`: claim-to-proof/test/result mapping.
