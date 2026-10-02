# Case and certificate interface

A case is a JSON object with exactly `domains`, `nodes`, `edges`, `base`, `aspects`
and `events`. The list `domains` gives positive finite domain sizes. Cell x contains
an integer in 0..domains[x]-1. `nodes` lists Boolean presence cells. Each `edges`
entry `[e,s,t]` designates a distinct Boolean edge cell and two designated nodes.
A present edge requires both endpoints present. `base` is a well-typed complete
state. `aspects` is the number of tag bits. Every event has exactly `tag`, `guard`,
and `write`; a guard entry `[x,[v,...]]` is a nonempty set of accepted pre-values;
a write entry `[x,v]` is a simultaneous constant overwrite. Duplicate cells or
values, Boolean JSON values used as integer indices, missing fields, extra fields
inside semantic objects, invalid original executions and out-of-bound values are
rejected. An empty event sequence is allowed; at least one storage cell is used.

Every enabled graph event must satisfy the sufficient incidence typing rule in
the proofs. If an incidence is changed, its post-edge is definitely absent or its
post-endpoint is definitely present, from a written constant or an unwritten
singleton observation. This is deliberately incomplete for safe graph updates.

An outcome has `mask`, `end` and an ordered `receipts` list. Each receipt has `at`
(the exact original occurrence index) and `old` pairs. Store exactly overwritten
cells whose old value is not fixed by a singleton guard or singleton domain.
Entries are checked against independently replayed pre-values. They must be
rebased when earlier events are erased. No complement for an unwritten cell is
permitted. The checker also performs the reverse round trip.

A packet contains `case` and `certificate`; surrounding descriptive fields may be
present. A certificate's exact fields depend on `kind`:

| Kind | Other fields | Meaning |
|---|---|---|
| success | outcome | This exact retention executes and its fresh receipts reverse it. |
| local | mask,event,cell,on,off | These compatible facts force this one ghost observation to fail and have minimum cardinality for it. |
| optimal | on,off,cost,outcome,proof | This policy completion executes and no completion has lower unit collateral cost. |
| infeasible | on,off,core_on,core_off,proof,witnesses | The subpolicy is infeasible and has minimum cardinality among all subpolicies of the requested policy. |

A refutation node is exactly one of `{cut:[i,x,j]}`, `{cost:true}` or
`{split:a,zero:p0,one:p1}`. A cut has a retained reader at i; j=-1 means the base,
otherwise j<i names a retained writer of a rejected value. Every later good
writer must be forced absent. Cost leaves are authorized only for checking
strictly better alternatives to a validated candidate. Both split children are
required and the bit must not already be assigned. Infeasible-certificate
witnesses contain `on`, `off`, `mask`, one per required (k-1)-fact subpolicy of the
original requested policy, with no omission or duplicate. Checking only one-fact
deletions of the chosen core would establish inclusion-minimality, not generally
cardinality-minimality among all subpolicies.

The local checker evaluates all masks directly and performs a subset-OR transform;
it never trusts the producer's normalized clauses. Global tree leaves are checked
against raw ordered events for the same reason. Syntactic acceptance cannot prove
that an actual source weaver recorded every semantically relevant observation.
