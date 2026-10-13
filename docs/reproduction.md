# Reproduction records

## Current default driver

The current default reproduction has 20 command phases: the historical 16 plus
the untimed event-local guard check, named-update bridge, update contract and
SAS+ supporter correspondence. `results/current-reproduction/clean-run.json`
is its current receipt; the directory contains the complete raw fresh output
tree. The driver exactly compares the bridge, contract and supporter records
against their shipped summaries, as well as existing campaign, structural and
source records. Guard coverage is required to pass with timing disabled.

Children run sequentially with a 2700-second wall timeout. POSIX CPU/address-space
limits remain available on supporting hosts. Windows unavailable child CPU/RSS
are null; the current Windows correctness run is not a substitute for the earlier
Linux resource measurement. Structural JSONL uses canonical LF on both systems.

## Historical 16-phase runs (unchanged)

Two isolated output directories were generated from the final artifact source.
Both runs executed **16/16 commands with exit code 0**, compared 50,000 campaign
records, independently checked 50,000 campaign packets, compared 421 structural
inputs, and compared six source-guided projections.

Run 1 measured 31.452709 seconds wall and
37.215422 seconds child CPU. Run 2 measured
30.574479 seconds wall and
36.409117 seconds child CPU. These timings are
telemetry, not a speed claim. Scientific equality excludes time, RSS, maximum-case
latency, and temporary paths; `results/final-validation/two-run-comparison.json`
records the comparison.

The paper's campaign resource table intentionally reports the earlier single
traceable campaign embedded in `results/clean-reproduction.json` and
`results/final-validation/` does not retroactively merge later regression tests
into that historical measurement.
