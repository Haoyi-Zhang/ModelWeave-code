# Observation-stable model unweaving artifact

This directory is a standalone executable artifact for the paper
*Observation-Stable Model Unweaving: Local Certificates and a Two-Write Boundary*.
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
- `tests/`: semantic, structural, source-projection, mutation, and pilot tests.
- `proofs/semantics.md`: definitions and written proofs T1--T26.
- `results/`: immutable campaign records, summaries, examples, and final validation.
- `docs/`: schema, proof/code map, reproduction, resources, evidence limits, and audit.
- `claim_evidence_ledger.csv`: claim-to-proof/test/result mapping.
