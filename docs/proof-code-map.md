# Proof, implementation, and test map

| Claim | Written argument | Implementation/checker | Finite evidence |
|---|---|---|---|
| Typed replay and round trip | `proofs/semantics.md`, T1--T3 | `src/engine.py`, `src/checker.py` | semantic typing tests; campaign receipts |
| Receipt rebasing is generally necessary | T5 | outcome receipt checks | stale-complement negative control; independent-cell safe case |
| Exact local normalization | T6--T10 | producer profiles; checker local oracle | 358 observation comparisons and exhaustive masks |
| Fixed-query minimum local facts | T12 | checker compares all compatible smaller fact sets | three-fact acceptance/four-fact rejection regression |
| One-write tractability | T24 | `src/structural.py`, policy solver/checker | 32 one-write cases and 7,776 partial policies |
| Two-write NP-completeness, one event/aspect | T25 | `two_writer_sat` | 274 bounded constructions, all correspondence checks pass |
| Exact two-write gadget CNF and helper projection | L29 | `two_writer_sat`; direct displayed-CNF evaluator | 75 formulas, 4,880 masks, 154 assignment/helper projections |
| Named update, policy, writer-count, and receipt preservation | L27 | `compile_updates`; separate named interpreter | saved 44 masks plus 70 new masks in two code orderings |
| Restricted positive-precondition action preservation | L28 | `compile_positive_actions`; separate action interpreter | 62 new masks; proper nonsingleton guards rejected |
| Large global cores | T26 | binary choice-tree constructor/checker | five trees; largest checked core has seven facts |
| Success/local/global certificate soundness | L19--T21 | `src/checker.py` | campaign, examples, mutation suite |
| Protocol cost leaves | T20--T21 | checker-authorized candidate-cost-minus-one bound | example-03 cost 0 and choice-tree tests |
