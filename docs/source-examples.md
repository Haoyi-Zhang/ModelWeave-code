# Source-guided encodings

The six exact JSON encodings and their results are in `results/examples/`.
Each packet records its source URL, figure/page locator and projection boundary.
These are newly authored closed-trace projections, not author-provided artifacts.
Two inputs share one threshold example. There are five distinct source figures or
passages, not thirty independent published examples or six full tool workloads.

Model identity, multiplicities, method bodies, general pattern matching and
source-tool scheduling are not reconstructed. The rematching example intentionally
returns a different fixed-match state from the source's rematched result. The
additive example intentionally exposes the loss of match-level granularity when
all occurrences of an aspect share one retention bit. Neither difference is
reported as a fault in the source work. The event-structure example fixes an order
and represents only its disjunctive enabling relation, not all reverse transitions.

All projected masks are checked by direct replay, and each selected policy has an
independently checked outcome or minimum-conflict certificate. Reproduce with
`python tests/test_examples.py NEW_OUTPUT_DIRECTORY`. No source PDF needs to be
fetched to replay the exact included inputs. Literature interpretation remains
separate from computational reproducibility.
