# Evidence limits

- Finite tests can falsify the implementation but do not prove the general theorems.
- Written proofs are not proof-assistant mechanizations.
- The checker is independently implemented relative to the producer modules, but
  was developed in the same project and is not an external replication.
- Six source-guided projections are small semantic projections, not six production
  systems and not the originally contemplated thirty published benchmarks.
- The campaign is deterministic and synthetic. No statistical model is trained;
  the relevant common-mode risk is addressed with a direct oracle, separate
  checker, exhaustive tiny cases, mutation rejection, and two clean runs.
- The artifact says nothing about rematching, concurrency, hidden reads, arbitrary
  graph rewriting, or production-scale model repositories.
- Internal closure does not imply journal acceptance or exhaustive prior-art clearance.
