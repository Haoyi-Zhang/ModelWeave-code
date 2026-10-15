# ModelWeave

ModelWeave checks which tagged updates can be retained, in their original order,
while preserving explicit observations. The artifact implements the finite
overwrite model and its one-write/two-write feasibility boundary. Python 3.10 or
later and the standard library are sufficient; the artifact runs independently
of the paper directory.

## Run

Use a fresh output directory outside the project. The full driver runs one
Python child at a time and refuses an existing output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python3 -B reproduce_all.py --output /absolute/fresh/modelweave-run
```

On Windows:

```powershell
python -B reproduce_all.py --output D:/path/to/nonexistent-output
```

The 20 command phases cover guard checks, named updates, the update contract,
SAS+ supporter correspondence, semantic and structural checks, source projections,
pilots, the 50-chunk campaign, independent packet verification, coverage and a
policy query. Output contains logs, raw compressed JSONL, comparisons and
`clean-run.json`. Scientific records are compared exactly; timing and resource
telemetry are not required to match. Failures retain diagnostics and exit nonzero.

Children have a 45-minute wall timeout. POSIX additionally applies the existing
2,500 MiB address-space and 45-minute CPU limits. Unavailable Windows CPU/RSS
fields are null. The scientific CI workflow runs this same driver on Ubuntu with
Python 3.12 and uploads its output.

## Focused checks

These commands exercise existing controls without rerunning the campaign or
writing new scientific result files:

```sh
python -B tests/test_assertion_gate.py -v
python -B tests/test_event_local_guard.py
python -B tests/test_update_bridge.py
python -B tests/test_update_contract.py
python -B tests/test_supporter_equivalence.py
python -B verify.py results/examples/example-03.json
```

The update/supporter scientific entries require enabled assertions and refuse
optimized Python before evaluating fixtures. The assertion-gate test exercises
normal execution, early optimized refusal and corrupted inputs. A refusal is not
a successful scientific run.

To save focused semantic, structural or source-projection results, supply fresh
output paths:

```sh
python -B tests/test_semantics.py /absolute/fresh/semantic-tests.json
python -B tests/test_structural.py /absolute/fresh/structural-tests
python -B tests/test_examples.py /absolute/fresh/source-examples
```

The named-update and supporter checks also accept a fresh `--output` file under
this project. Omitting that option writes nothing.

## Model and interfaces

The model has finite typed cells, fixed matches and event order, unary
observations, simultaneous constant overwrites, and one keep/erase decision per
tag. Retaining a tag retains all its occurrences. One-write policy feasibility
is polynomial; the two-write restriction is NP-complete with Boolean cells, one
event per aspect, one forced keep and one forced removal. An event may touch
polynomially many cells.

`src/update_language.py` translates declared named cells and ordered guarded
constant assignments. Its positive-action interface accepts singleton/full-domain
requirements and rejects proper nonsingleton guards. `src/sas_supporters.py`
translates valid fixed SAS+ plans with equality preconditions and constant
effects. Supporters are existential; repeated labels share a retention bit.
Nonempty terminal goals add a mandatory write-free label. These are closed
source interfaces, not extractors for arbitrary production tools.

Definitions and preservation arguments are in `proofs/semantics.md` (T1–T26,
L27–L31). `docs/sas-primary-correspondence.md` records the relation to the existing
supporter/opposer encodings and the precise additional restrictions.

## Evidence and costs

- `results/campaign/`: 50,000 packets and 231,071 direct replay queries;
  49,526 successful and 474 local-obstruction certificates.
- `results/structural-cases.jsonl`: 421 structural inputs covering clause,
  one-write, restricted two-write and choice-tree cases.
- `results/update-language/`, `results/update-contract/` and
  `results/supporter-correspondence/`: complete bounded interface comparisons.
- `results/examples/`: six small source-guided projections, not executions of
  the upstream tools.
- `results/current-reproduction/`: complete 20-phase correctness output.
- `results/final-validation/`: unchanged historical 16-phase runs and telemetry.

The guard lookup measurement in `results/guard-lookup/measurement.json` reports
five paired blocks and a median scan/index ratio of 8.70. It measures replay and
successful reversal on the recorded fixtures, not parsing, search or production
tools. Inspect `benchmarks/benchmark_guard_lookup.py --describe` before running
its explicit `--run-serial-timing` mode, and run timing without competing work.

## Map and manuscript build

`src/` contains the engine, producer, checker, direct oracle and reductions.
`tests/` contains semantic, structural, source and mutation controls.
`docs/` describes the schema, proof/code mapping, resources and evidence scope.
`claim_evidence_ledger.csv` maps manuscript claims to those files.

For the manuscript, use the sibling `paper/` directory:

```sh
make clean
make all
make check
```

The written proofs and finite checks have different roles. The checker has a
separate implementation path; it checks packet consistency rather than packet
origin. The source interfaces preserve the declared fixed histories and do not
introduce rematching, hidden reads, concurrency or arbitrary graph rewriting.
