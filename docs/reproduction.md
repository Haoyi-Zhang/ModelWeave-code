# Reproduction record

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
