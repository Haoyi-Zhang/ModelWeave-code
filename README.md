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

## Reproduce

Run from this directory on Linux with Python 3.10 or newer and a new output
directory. The full runner, campaign, and test drivers use the Unix `resource`
module for resource limits and telemetry; RSS is recorded in Linux KiB units.
These entry points do not support native Windows.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python3 reproduce_all.py --output /tmp/unweave-reproduction
```

The runner executes 16 sequential phases: semantic and structural tests,
source-guided projections, three pilots, the 50-chunk campaign, five independent
checker batches, coverage regeneration, an example check, a policy query, and an
independent check of that query. It refuses an existing output directory. No
network, GPU, external model API, non-standard package, or parallel worker is used.

The GitHub Actions workflow in `.github/workflows/scientific-checks.yml` runs
the full reproduction on `ubuntu-latest` with Python 3.12, using a fresh output
directory under `RUNNER_TEMP`. It uploads the complete output tree, including
raw compressed JSONL records and logs, without changing scientific seeds or
resource limits.

Useful focused commands on Linux:

```sh
python3 tests/test_semantics.py /tmp/semantic-tests.json
python3 tests/test_structural.py /tmp/structural-tests
python3 tests/test_examples.py /tmp/source-examples
python3 verify.py results/examples/example-03.json
```

The independent verifier itself does not import `resource` and can also check
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

Two fresh full runs passed all 16 phases and produced equal scientific records
after excluding runtime telemetry. See `results/final-validation/`.

## Evidence boundary

The written arguments are in `proofs/semantics.md`; executable tests are finite
falsification and certificate-replay evidence. Neither is described as Lean, Coq,
Isabelle, or other proof-assistant mechanization. The independent checker is a
separate implementation path, but not independent authorship or cryptographic
source authentication.

## Map

- `src/`: engine, producer, checker, direct oracle, generators, and reductions.
- `src/update_language.py`: named-patch and restricted positive-action coding.
- `tests/`: semantic, structural, source-projection, mutation, and pilot tests.
- `proofs/semantics.md`: definitions and written proofs T1--T26.
- `results/`: campaign records, summaries, examples, and comparison measurements.
- `docs/`: schema, proof/code map, reproduction, resources, evidence limits, and audit.
- `claim_evidence_ledger.csv`: claim-to-proof/test/result mapping.
