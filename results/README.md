# Result records

`campaign/`, `examples/`, `pilots/`, `tests.json`, `structural.json`, and
`structural-cases.jsonl` are the claim-linked stored records.  Runtime telemetry
inside individual files may differ between executions and is not used as a
scientific equality field.

`clean-reproduction.json` preserves the single historical resource measurement
reported in the paper.  The fixed-mask local-minimum regression and expanded
274-case one-event-per-aspect reduction suite were added later and are not
retroactively folded into that timing.

`final-validation/` contains two complete fresh 16-phase runs and a normalized
comparison.  Their scientific records agree; time, RSS, maximum-case latency, and
temporary path fields are explicitly excluded from the equality relation.
