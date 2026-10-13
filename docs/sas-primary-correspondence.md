# Primary-source and proof correspondence

The two closest articles were read completely, not just their abstracts or
encoding appendices:

- Balyo, Chrpa and Kilani, **On Different Strategies for Eliminating Redundant
  Actions from Plans**, SoCS 2014, pages 10--18, DOI
  [10.1609/socs.v5i1.18318](https://doi.org/10.1609/socs.v5i1.18318).
  [Complete author PDF](https://ktiml.mff.cuni.cz/~balyo/papers/socs14.pdf):
  nine PDF pages, including definitions, greedy methods, propositional encoding,
  optimal reductions, experimental evaluation, discussion and references.
- Salerno, Fuentetaja and Seipp, **Finding Minimal Plan Reductions Using Classical
  Planning**, JAIR 84 Article 10, October 2025, 35 pages, DOI
  [10.1613/jair.1.19437](https://doi.org/10.1613/jair.1.19437).
  [Complete author PDF](https://mrlab.ai/papers/salerno-et-al-jair2025.pdf):
  Definitions 1--14, Sections 1--8, four planning compilations and their proofs,
  PAL/always-redundant analysis, evaluation, references and Appendix A.

## Claims transferred and formulation made explicit

| Source location | Fact used | Exact candidate correspondence |
|---|---|---|
| 2014 Planning preliminaries (PDF page 2); 2025 Definition 1 (page 3) | Finite-domain partial equality preconditions and constant partial effects, applied to pre-state | Direct cell/value bijections; no one-hot expansion; full source sequence must execute and reach its goal |
| 2014 Propositional Encoding of Plan Redundancy (pages 4--6), Propositions 1--2; 2025 Section 3.2 and Appendix A (pages 34--35) | Earlier achievers and intervening opposers represented by option variables | L30 explicitly existentially projects fresh options; C_q includes base only when its equality holds, and threats use strict j<k<i |
| 2014 Minimal Length Reduction/Minimal Reduction (pages 6--7); 2025 Appendix A | Negated occurrence-selector soft clauses optimize removed action cost | Only hard feasibility semantics is compared here; no cost or runtime superiority claim |
| 2025 Section 4 (pages 7--15) | Four skip/apply planning compilations | Recognized as nearest optimal alternatives, not claimed to be implemented or benchmarked by this artifact |
| 2025 Section 5 (pages 15--20) | Single-achiever necessity and fix-point PAL reasoning | One-write implication closure is identified as standard reasoning; these general results do not settle the joint writer-count restriction |

Our zero-based read positions, explicit base side condition and strict threat
intervals are a semantic formulation, **not a literal transcription of printed
index shorthand**. Action i tests before its own effects; terminal goals at n
include effects at n-1. A selected valid subsequence admits *some* supporter
assignment, not every assignment. Neither exactly-one options nor converse
option implications are imposed. The written proof establishes the projected
meaning rather than treating satisfiability of arbitrary auxiliary assignments
as equivalent to source execution.

## Selection, admission and goal boundary

Published occurrence selectors become u_i(M)=[a_i in M]. Repeated occurrences
share a tag bit, so the interface cannot choose them independently. This is
ordinary selector binding, not a new SAT encoding. Writer counts count each
original assignment occurrence, including idempotent writes and repeated labels.

The mathematical source domain is a **supplied valid full plan**, executable
from its base and reaching its terminal equality goal. Both implementation APIs
admit only coded cases within engine bounds. A nonempty goal adds one fresh,
mandatory, write-free final read; no writer counts change, but the total number
of mandatory labels can increase. The two-write construction uses an empty goal
and its existing forced reader, preserving its exact joint restriction.
Proper nonsingleton trace guards, conditional/computed effects, rematching and
arbitrary planning insertion/reordering are outside this correspondence.

The prime theorem concerns the auxiliary-free projection of **one** observation.
Its conjunction is globally exact but need not be globally prime; the two-cell
anchor explicitly checks two ternary local primes resolving to a binary global
prime. Unconditional source goals do not inherit unpinned-reader endpoint claims.

## Proof and executable evidence

- Paper Appendix SAS+ Supporters: source definition, candidate/threat sets,
  existential local projection lemma, whole-label correspondence theorem and
  local/global prime boundary.
- `proofs/semantics.md`: L30 is local projection; L31 is valid-full-plan
  whole-label/goal correspondence. L27 supplies the coordinate/receipt induction.
- `src/sas_supporters.py`: `compile_sas`, `encode_supporters`,
  `occurrence_mask`. Admission delegates only validation/coding to the closed
  update interface; clauses are constructed from source maps, not normalized CNF.
- `tests/test_supporter_equivalence.py`: nine hand-written models, 45 original
  label masks, 50 local projections, 133 partial policies and ten named rejections.
  The source interpreter, option evaluator and replay enforce the same obligations.
- `results/supporter-correspondence/summary.json`: complete source tasks, target
  cases, formulas, writer counts, per-mask verdicts/witness counts and rejection
  identities.
- `results/current-reproduction/clean-run.json` and its raw tree: current 20-phase
  reproduction; new source records are compared exactly with shipped summaries.

The inherited feasibility semantics, objective-sign change and tag binding are
not originality claims. **Prior coverage of the joint Boolean/two-write/
one-event-per-aspect/one-keep/one-removal restriction remains unknown.** The
candidate proves its stated restriction but does not claim to be first. Published
tools were not executed, and the finite anchors are not a new generated campaign.
