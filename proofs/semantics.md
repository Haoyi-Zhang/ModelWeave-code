# Observation-stable weaving: definitions and mathematical proofs

These are mathematical proofs of the stated finite calculus, not proof-assistant
output. The executable checker and exhaustive tests provide a different, bounded
kind of evidence. Neither substitutes for independent scrutiny of these arguments.

## 1. Objects, observations, and the meaning of unweaving

A signature has a finite set of cells X and a nonempty finite domain D_x for each
cell. Designated node cells and edge cells have domain {0,1}. Every designated edge
e has two fixed endpoints s(e), t(e), which are designated node cells. Node and
edge cells are disjoint and each edge has its own presence cell. Other cells are
scalar attributes. The allocated catalog and scalar domains do not change.

A state sigma assigns a member of D_x to each cell. It is well typed when, for
every edge e, sigma(e)=1 implies sigma(s(e))=sigma(t(e))=1. Scalar values of absent
nodes remain allocated, unobserved storage; this model does not allocate fresh
identities, collect unreachable cells, or decide graph isomorphism.

An event e_i=(a_i,g_i,w_i) consists of an aspect tag, a finite observation map, and
a finite constant-overwrite map. An observation g_i(x)=S is a nonempty subset of
D_x and means that the pre-state value is in S. The event is enabled when every
observation holds, and its effect is simultaneous overwrite by w_i. A consumed
value whose identity affects a captured computation must be recorded by a
singleton observation. A unary test can instead record its full accepting set.
The calculus concerns these closed event instances, not an unspecified source
language that discovers new matches or recomputes different constants.

The original trace T=e_0...e_(n-1) is assumed to execute from a well-typed base B.
A retention assignment K is a subset of aspect tags. Retaining a tag retains all
its occurrences, including interleaved occurrences. Replay scans the original
order and executes exactly the retained events. An assignment is valid precisely
when that replay is enabled throughout. This is observation-stable, fixed-match
unweaving. A refusal is relative to this specification; it does not prove that no
other graph transformation, rematching strategy, or semantic-equivalence relation
could produce a satisfactory model.

## 2. Type preservation

For each incidence (edge e, endpoint p), impose the following rule on an event
that overwrites at least one of e,p: either the post-event edge is definitely zero,
or the post-event endpoint is definitely one. A written constant determines the
corresponding post-value. An unwritten edge is definitely zero when its observation
is exactly {0}; an unwritten endpoint is definitely one when its observation is
exactly {1}. If neither cell is written, inherit the incidence invariant. All
written constants and observation members must have their declared cell types.

**Theorem T1 (forward preservation).** An enabled, well-typed event maps a
well-typed state to a well-typed state.

**Proof.** Domain membership follows for each overwritten cell from its declared
constant and for each other cell from the input. Consider an arbitrary incidence.
If neither cell changes, its implication is unchanged and holds by the input
invariant. Otherwise the typing rule gives one of two facts. A written zero or an
unchanged edge observed to be zero makes the implication's antecedent false. A
written one or an unchanged endpoint observed to be one makes its consequent
true. These are all admitted cases. Both endpoint incidences therefore hold for
every edge. Simultaneous overwrite is important: deletion of an edge and endpoint
in one event is legal without an ill-typed intermediate state. QED.

The rule is sufficient, not a complete inference procedure for all safe graph
updates. For example, an observation that an unchanged edge is present can imply
that its endpoint is present, but the rule above deliberately does not infer that
additional fact. This incompleteness cannot invalidate preservation.

## 3. Complements and round trips

For an overwritten cell x define A_x=g_i(x) if an observation exists, and A_x=D_x
otherwise. When |A_x|=1, its old value is determined by the event and need not be
stored. Otherwise the receipt stores the actual old value of x. The receipt also
identifies its event occurrence. Unwritten cells are not copied into the receipt.

The inverse of a receipt first requires the current values of every written cell
to equal the event's written constants. It restores each written cell from either
the receipt or its unique possible old value. It then checks the observations in
the restored state. Receipt-domain exactness and forward verification prevent
missing, extra, reordered, and stale complement entries from being accepted.

**Theorem T2 (one-step round trip).** If e transforms sigma to tau and h is its
correctly generated receipt, inverse(e,h,tau)=sigma.

**Proof.** On a written cell, tau has the required post-value. If the cell has one
possible pre-value, enabledness implies that sigma has that value; otherwise h
contains sigma's value by construction. On an unwritten cell, tau already agrees
with sigma and the inverse leaves it alone. Equality follows cellwise. The final
observation check succeeds because sigma enabled e. QED.

**Corollary T3 (trace round trip and backward preservation).** Reversing all
receipts of a valid execution in reverse occurrence order recovers B. Every
reconstructed intermediate state is well typed.

**Proof.** Induct backwards over the trace. The final receipt sees exactly its
forward post-state; T2 recovers its pre-state, which is the preceding receipt's
post-state. Continue to B. These states were well typed by T1 and initial typing.
This is a statement about validated receipts, not arbitrary inverse guesses. QED.

**Theorem T4 (coordinate necessity in the product fragment).** If there are no
relational graph constraints and old values are stored only as a chosen set of
coordinates, every written x with |A_x|>1 must be stored to support inversion for
all enabled inputs. The described receipt stores exactly these coordinates.

**Proof.** Suppose such an x is omitted. Choose two distinct members of A_x and two
input states differing only at x, fixing every other coordinate to an allowed
value. Both states enable the event. Their post-states are identical because x is
overwritten, and the stored coordinates are identical because x was omitted.
Consequently no decoder receiving those data can distinguish the two pre-states.
This contradicts inversion for both. Singleton coordinates are reconstructible;
therefore storing all and only the non-singleton coordinates is sufficient and
necessary in this storage model. QED.

For a fixed setting of unwritten cells, the product-fragment fiber has cardinality
product_{x in W}|A_x|. A lossless fixed-length binary encoding, or a prefix-free
encoding with all framing charged to the receipt, therefore needs at least
ceil(log2(product |A_x|)) bits in the worst case. Unrestricted variable-length
payloads with externally supplied boundaries do not obey that exact bound.
Coordinate storage is not
claimed to attain that bit bound. Relational graph constraints can also shrink a
fiber and make a coordinate inferable. Thus T4 is not a claim of globally minimal
logging for typed graphs.

**Theorem T5 (selective receipts must be rebased).** For a valid retention K,
replaying the retained events and generating their complements again yields an
outcome satisfying T3. Reusing the original complement of a retained event is not
in general sound.

**Proof.** Apply T2 and T3 to the retained execution. For the negative part take a
three-valued cell initially 0, with A writing 1 and B writing 2, both without an
observation. Retain only B. Its new pre-state is 0, whereas its original receipt
stored 1. Using the old receipt restores 1 instead of 0. The final state 2 alone
does not expose the stale receipt. QED.

## 4. Ghost observations and normalization by aspect

A ghost prefix applies the retained overwrites before i while ignoring all
observations. For an observation (i,x,S), define H_(i,x)(K) to be true if the reader
tag is absent, or if x's ghost-prefix value belongs to S. Ignoring earlier
observations here is a mathematical device, not an execution policy.

**Theorem T6 (exact factorization).** K is a valid guarded replay if and only if
H_(i,x)(K) holds for every recorded observation.

**Proof.** If guarded replay succeeds, its state before each retained event equals
the ghost prefix because both have applied the same preceding retained overwrites.
All its observations hold, and skipped readers satisfy H by definition. Conversely,
assume every H holds. Induct over original occurrence positions. The actual replay
has reached the ghost-prefix state at the induction point. A skipped occurrence
changes neither state. For a retained occurrence every unary observation holds by
hypothesis, so the event is enabled; both executions perform identical overwrites.
This completes the induction and establishes actual executability. T1 supplies
well-typedness along the actual execution. QED.

Fix one observation and let r be its reader tag. If r is retained, the last earlier
write to x by r is necessarily retained. Call its index alpha and its value b. If
there is no such write, use alpha=-1 and b=B(x). Writes at or before alpha cannot
alter the value selected after this anchor.

For every tag a other than r, retain only its last write to x between alpha and i.
Sort these representatives by occurrence index. Each representative has a distinct
tag. Classify it as good if its constant belongs to S, and bad otherwise.

**Lemma L7 (last-occurrence normalization).** Conditional on retaining r, the
observed ghost value is obtained by starting from b and applying the retained
representatives in their index order.

**Proof.** An earlier write by the same tag as a later write is either jointly
absent or jointly present with the latter. If jointly present, the later write
supersedes it before the observation. Removing all non-last writes of each tag
therefore leaves the last retained write unchanged. Writes before the last
reader-tag write cannot win because the reader-tag write is forced present.
Removing these writes leaves exactly the claimed representative sequence. This
reasoning uses constant overwrites; a retained overwrite does not read a value
implicitly. Every actual consumed value is an explicit observation. QED.

Define a Boolean variable X_a for retention of tag a. The normalized local CNF is:

* if b is bad, include not X_r OR the disjunction of every good representative;
* for each bad representative a at index j, include not X_r OR not X_a OR the
  disjunction of good representatives later than j;
* if the base clause exists, omit a bad-writer clause when no good representative
  precedes that bad writer. Exactly these clauses are subsumed by the base clause.

An empty conjunction is true, an empty positive disjunction is false. All
variables within a clause are distinct. A tag has the same polarity throughout
this local CNF: the reader and bad tags occur negatively, and good tags positively.

**Theorem T8 (exact local clauses).** This CNF denotes H_(i,x).

**Proof.** A skipped reader satisfies every clause. Suppose the reader is retained.
If the last retained representative is good, it makes the base clause true when
present and satisfies every retained bad writer's clause: every such bad writer
must occur earlier than that last good representative. An absent bad writer
satisfies its own clause negatively. If no representative is retained and the base
is good, every bad writer is absent and there is no base clause. These are exactly
the cases where the ghost observation holds. In the remaining cases, either no
good representative is retained while the base is bad, falsifying the base clause,
or the last retained representative is bad and no later good representative is
retained, falsifying that bad writer's clause. Subsumption does not change the
conjunction. QED.

## 5. All local prime implicates and a precise minimality claim

A clause is an implicate of H when every satisfying assignment of H satisfies the
clause. It is prime when no proper subclause is an implicate. Tautological clauses
are excluded. Literal count means occurrences of signed original aspect variables;
it does not mean bits, compressed bytes, shared decision nodes, or an encoding
with auxiliary variables.

**Lemma L9 (unate antichain).** For a CNF in which every variable has a fixed
polarity, its distinct non-subsumed clauses are exactly its prime implicates.

**Proof.** Rename variables so that every literal in the CNF is positive. Its
function is then monotone increasing. A prime implicate cannot contain a negative
literal: if removing not Z made a clause cease to be implied, some satisfying
assignment would falsify the other literals while setting Z=0. Increasing Z to 1
would preserve satisfaction by monotonicity but falsify the entire original
clause, a contradiction. Hence every prime implicate D is positive.

Set every variable in D to zero and every variable outside D to one. D is false,
so H must be false. Some input clause C is false under this assignment, meaning
C is a subset of D. Thus every implicate contains an input clause. An input clause
that is not subsumed cannot have a proper implicate subclause: that subclause
would contain another input clause strictly contained in it. Conversely a subsumed
clause is not prime. Renaming variables back preserves implication and containment.
QED.

**Theorem T10 (canonical local prime representation).** The normalized local
clauses are all and only the prime implicates of H_(i,x).

**Proof.** L7 removes repeated mixed-polarity histories; T8 establishes the
function. Every representative tag is exclusively good or bad, so the CNF is
unate. Distinct bad-writer clauses cannot subsume one another: each contains its
own negative bad tag, absent from the other. A bad clause cannot subsume the base
clause. The base clause subsumes a bad clause precisely when the latter's good
suffix contains all good tags, equivalently when no good tag precedes the bad
writer. The normalization removes exactly these cases. Apply L9. QED.

**Corollary T11 (literal-minimal flat CNF).** Among all equivalent flat CNFs using
only the original aspect variables, the normalized local CNF has the minimum
number of clauses and minimum total literal count. A literal-minimum solution is
unique up to clause and literal order.

**Proof.** In any equivalent CNF, every non-tautological clause contains a prime
implicate. Replace each clause by a contained prime implicate. This only shortens
clauses, and equivalence is preserved: H implies each replacement, and each
replacement implies the clause it replaced. By L9, omitting any prime implicate
from the resulting unate CNF would change its function. Therefore every normalized
prime must occur at least once. This proves both lower bounds. Equality in total
literal count leaves no room for an extra nonempty clause, a proper superclause,
or a duplicate, proving uniqueness. The constant-true case has the unique empty
CNF. QED.

This monotone-Boolean reasoning is standard; the source-specific step is L7,
which exposes unateness despite repeated, interleaved writes by one aspect.
It does not turn global unweaving into a monotone problem.

**Corollary T12 (minimum local obstruction).** Fix an invalid full assignment M
for one observation. A partial assignment drawn from M forces that observation
to fail under every completion precisely when its negated literals form an
implicate of H. The smallest such partial assignment is obtained by choosing a
shortest normalized clause falsified by M.

**Proof.** Forcing failure means no model of H agrees with all partial facts. This
is logically equivalent to H implying their negated disjunction. Every implicate
contains a prime implicate, and T10 supplies all primes. A contained prime uses
only facts already fixed by M and cannot be longer. A shortest falsified prime
therefore attains the minimum. QED.

**Theorem T13 (quadratic output and linear certificate boundary).** With m aspect
tags, a single observation has O(m) local prime clauses and O(m^2) literal
occurrences. Both the quadratic total and a linear shortest-certificate length
are attained, up to constants, in this representation class.

**Proof.** There are at most m-1 representatives and at most one base clause plus
one clause per bad representative. Every clause has at most m literals. For a
matching family use a good base, followed by b_1,g_1,...,b_k,g_k and a reader r,
where each b_j writes a bad value and each g_j a good value. There are 2k+1 tags.
The k prime clauses have lengths k-j+3, giving 2k+k(k+1)/2 literals. T11 makes that
an unavoidable flat-CNF output cost. Retain only b_1 and r. Its only falsified
prime is the first clause, of length k+2, so T12 gives a linear minimum local
obstruction. A last-writer decision list or suffix-sharing representation may use
linear space; no representation-independent quadratic information bound is claimed.
QED.

## 6. Local and global explanations differ

Use two cells initially (0,0). Aspect x writes (1,1), aspect g subsequently writes
(1,0), and aspect r observes the first cell in {1} and the second in {0}. Their
local prime clauses are, respectively,

    not r OR x OR g
    not r OR not x OR g.

The conjunction is equivalent to not r OR g. If r is retained and g erased, the
whole replay is impossible independently of x. For the full mask with x erased,
the failing first observation has a three-fact minimum local certificate, whereas
the whole replay has a two-fact obstruction. Thus local primeness, local literal
optimality, and local minimum explanations do not imply corresponding global
minimality results.

There is a related reason that a normalized local prime cannot always be checked
by a single raw last-writer cut. If an aspect first writes a good value and later
a bad value, the raw base cut may require that aspect absent, while a raw bad-write
cut requires it present. Their disjunction can justify a smaller normalized prime
that mentions neither decision. The independent checker consequently uses a
separate truth-table algorithm for local cardinality and branch proofs for global
refusals; it does not mistake one raw cut for every normalized prime.

## 7. When a dependency graph suffices

A family described by implications X_a implies X_b is closed under set union and
intersection: the antecedent in a union comes from one member; the antecedent in
an intersection occurs in both members. The consequent follows in the same union
or intersection. Not every valid-retention family has these closure properties.

For disjunctive replacement, start at 0, let A and B each write 1, and let C read
1. Keeping {A,C} or {B,C} is valid; their intersection {C} is not. For inhibition,
start at 0, let A write 1, B write 0, and C read 0. Keeping {C} or {A} is valid;
their union {A,C} is not. These are different obstructions to any fixed
implication-only dependency representation. Mere non-monotonicity is not itself
such a proof, since implication-defined families can also be non-monotone as
Boolean validity predicates.

**Theorem T14 (exact implication criterion).** For any finite family V of tag
sets containing both the empty and full sets, V is definable by implications
between tags if and only if V is closed under binary union and intersection.

**Proof.** Necessity was just proved. For sufficiency let cl(a) be the intersection
of all members of V containing a, which exists because the full set is a member.
Require each a to imply every b in cl(a). Every member of V satisfies these
implications. Conversely suppose K satisfies them. Then cl(a) is a subset of K for
every a in K, and contains a. Consequently K equals the union of cl(a) over a in K.
Each cl(a) belongs to V by finite intersection closure, and their union belongs to
V by union closure; for K empty use the explicit empty-set assumption. QED.

This representation is in general a preorder. Tags that always occur together
form equivalence classes; quotienting those classes gives a partial order.

**Corollary T15 (checkable sufficient fragment).** If every nontrivial normalized
local prime is a binary implication, collecting those implications exactly
describes valid retentions. Strongly connected components handle grouped,
interleaved tags. If each aspect occupies a single contiguous trace block, the
nontrivial dependency edges follow block order and are acyclic.

**Proof.** Conjoin T8 over observations and use T6. Every clause must contain a
negative and a positive literal because both the empty and original full retention
satisfy it; a binary clause is therefore an implication. In a contiguous block a
reader either sees a forced earlier write of its own tag (then its original
observation is unconditionally satisfied when retained), or its relevant writer
is in an earlier aspect block. Therefore nontrivial dependencies follow block
order. QED.

This is only a sufficient syntactic test for implication representability. The
two-cell example in Section 6 has ternary local primes but a binary global
representation, so rejecting that test does not prove a dependency graph
impossible. Global simplification may remove local obstacles.

## 8. Independence and the precise confluence claim

For an event let R be its observed cells and W its overwritten cells. Declare two
events independent when neither writes a cell read or written by the other:
W_1 intersect (R_2 union W_2) and W_2 intersect (R_1 union W_1) are both empty.

**Theorem T16 (commuting diamond).** If independent events execute consecutively
from a typed state, they can execute in the opposite order, with the same final
state and the same complement for each corresponding occurrence.

**Proof.** Neither event changes the other's observations, so the second was
already enabled before the first. Conversely executing the second cannot disable
the first. Their disjoint write sets give identical final values cellwise. Neither
changes any cell whose pre-value the other stores in its complement, so each
occurrence's complement is unchanged. T1 preserves types along either route. QED.

Order each non-independent pair by its order in the original trace and close
transitively. Every linear extension can be reached from another by swapping
adjacent incomparable elements: move the first desired element leftward past all
preceding elements, which must be incomparable, then induct on the suffix. Such
pairs are independent by construction. Applying T16 at each swap proves equality
of final states and per-occurrence receipts for all these linear extensions of a
valid retained trace. This is trace-relative confluence in an independence
fragment, not confluence of arbitrary graph rewriting or of reordered conflicting
aspects. Equal-valued writes can commute semantically despite failing this
conservative footprint test; completeness of the test is not claimed.

## 9. Global policy feasibility is NP-complete

A policy specifies disjoint forced-keep P and forced-remove D sets. It asks whether
some valid retention extends those decisions. Here input sizes are unbounded but
finite; the executable artifact's twelve-aspect admission bound is not a complexity
assumption of the theorem.

**Theorem T17.** Policy feasibility is NP-complete even with Boolean scalar cells,
one event per aspect, one forced-keep aspect, and one forced-remove aspect.

**Proof.** Membership in NP follows by guessing a retention and performing guarded
replay. For hardness take a 3-CNF formula with variables z_1,...,z_q and nonempty
clauses C_1,...,C_h. Introduce initially-zero cells x_i,y_i for each variable and
c_j for each clause. There are two optional aspects p_i,n_i per variable, a reset
d, and a reader r. Execute them in the fixed order

    p_1,...,p_q, d, n_1,...,n_q, r.

Event p_i writes x_i=1 and y_i=1, and writes c_j=1 for every occurrence of the
positive literal z_i in C_j. It has no observations. Reset d writes all x_i=0.
Event n_i observes x_i=0, writes y_i=1, and writes c_j=1 for every occurrence of
not z_i in C_j. Reader r observes all y_i=1 and all c_j=1 and writes nothing.
All domains are Boolean, and no graph-incidence constraints are needed.

The original all-retained trace is valid: d makes every n_i observation true,
every variable's y_i is written, and every nonempty clause has some literal
whose corresponding aspect writes its c_j. Force r kept and d removed. If n_i is
kept, its observation prohibits retaining p_i. The final observation y_i=1
requires at least one of p_i,n_i. Thus exactly one is kept for each variable.
Interpret p_i as assigning true and n_i as assigning false. The final observation
c_j=1 holds exactly when some selected literal satisfies C_j. Therefore policy
completion is possible exactly when the 3-CNF is satisfiable. The construction has
polynomial size and one event per aspect. QED.

The reduction uses the standard NP-completeness of 3-SAT; no new complexity class
or generic SAT lower bound is asserted. It locates that hardness inside the
specific constant-overwrite fragment and the very small policy interface.

**Corollary T18.** Unless NP=coNP, there is no polynomial-size, polynomial-time
checkable refusal certificate for every infeasible policy in the unbounded finite
fragment. Otherwise infeasibility would be in NP and the complement of the
NP-complete problem of T17 would also be in NP.

For minimum collateral removal a separate graph construction is useful. For each
edge {u,v}, orient it with u<v and allocate a zero cell. The event of vertex u
observes zero on incoming edges and writes one on outgoing edges. Immediately
follow it by a reset aspect that writes zero on its outgoing edges. Remove all
reset aspects by policy. Then the retained vertices are exactly independent sets,
and removed optional vertices are vertex covers. This proves NP-hardness of
minimum collateral deletion and supplies a small exact-oracle experiment.

## 10. Certificate semantics and checker soundness

A successful outcome gives a retention, a final state, and a receipt for every
retained occurrence, in order. The checker recomputes every observation and
pre-value from the base, requires exact complement domains and values, checks the
final graph and state, and reverses the receipts to the base. T1--T3 establish the
mathematical meaning of these checks. The checker does not infer external
provenance or authenticity from internal consistency.

A raw failure cut identifies an observation, a bad source (an earlier write or
the base), and a partial retention. The reader is forced kept; a non-base bad
source's tag is forced kept; and every later write whose value satisfies the
observation has its tag forced removed. Other later bad writes need not be
excluded.

**Lemma L19 (cut soundness).** Every completion of a raw cut's partial retention
makes its ghost observation fail, and therefore cannot be a valid replay.

**Proof.** A bad value is present at the identified source. No subsequent retained
write can supply a good value, since all such writers are forced absent. Every
subsequent retained write, if any, is bad. Thus the final selected value before
the retained reader is bad. T6 excludes actual replay validity. QED.

A refutation tree branches on an unassigned tag. Its zero child forces removal,
and its one child retention. A leaf is a raw cut, or, for an optimality proof, a
cost lower-bound leaf. The latter is permitted when already forced optional
removals exceed the externally fixed better-than-candidate budget. The checker
supplies that budget, not the producer. The tree cannot split an assigned tag or
omit either branch.

**Theorem T20 (refutation soundness and finite completeness).** An accepted
refutation has no valid policy completion within its authorized budget. If no
such completion exists, a finite tree of this form exists.

**Proof.** Induct over the accepted tree. A cut leaf is sound by L19. A cost leaf
is sound because later decisions cannot undo forced removals. A split partitions
all completions into its two child assignments, both impossible by induction.
For completeness, branch until every tag is assigned. If the mask exceeds the
budget, a cost leaf is available. Otherwise it is invalid. Pick a failed ghost
observation and its last retained writer, or the base if there is none. That
source is bad, and all later good writers are absent, giving a raw cut. QED.

With m tags, the complete binary tree has at most 2^(m+1)-1 nodes. At m<=12 that
is 8,191, below the checker's 10,000-node ceiling. This exponential bound is not
misrepresented as a polynomial certificate guarantee.

For a candidate of cost c, the checker validates its outcome and a refutation of
all completions of cost at most c-1. These two facts prove minimum collateral
cost. No lower bound based on the producer's own search counters is trusted.

For an infeasible policy Q, a minimum conflicting subpolicy C of size k is certified
by a refutation for C plus one valid witness for every (k-1)-element subpolicy of
Q. The checker enumerates the required subpolicies itself and rejects missing or
duplicate witnesses.

**Theorem T21 (cardinality-minimum policy obstruction).** These checks prove that
C is an infeasible subpolicy of Q and no smaller subpolicy of Q is infeasible.

**Proof.** Refutation proves infeasibility. Every smaller subpolicy can be extended
inside Q to size k-1; a provided valid witness for that extension is also a witness
for the smaller subpolicy. Hence all smaller subpolicies are feasible. Conversely,
if C is cardinality-minimum, every (k-1)-subpolicy is feasible and suitable
witnesses exist. This proves completeness of this bounded certificate form. QED.

For local minimum cardinality the executable checker deliberately uses neither
normalization nor the compiler's clauses. It evaluates the selected ghost
observation on all 2^m masks. Relative to the queried mask M, mark each difference
set having a good completion. A subset-OR transform records, for each set Z,
whether any good completion differs from M only within Z. A fact set S forces
failure exactly when the entry for the complement of S is false. Enumerating all
S and comparing their cardinalities establishes minimum cardinality independently
of T10's construction. The transform's induction invariant is the disjunction of
entries whose differences use a subset of already processed bit positions; after
all bits it is exactly subset closure. This is bounded executable checking, not
a general proof-assistant certificate.

## 11. Information that cannot simply be discarded

Observation omission is unsound as a uniform abstraction. Start at zero, write
one with A, write zero with B, and let R either observe {0} or {0,1}. Both complete
traces have identical base, writes, intermediate states, complements, and final
state. Retaining A and R but not B fails the first observation and passes the
second. Therefore write/snapshot data without observations cannot decide every
query in this calculus.

Order omission remains unsound even if per-occurrence old values are retained.
Take four blind writes A:0->1, B:1->0, D:0->1, E:1->0, followed by R observing 0.
The orders A,B,D,E,R and D,E,A,B,R have the same base, final state, named writes,
old values, and reader observation. Retain only A,E,R. The first order ends at
zero and passes; the second ends at one and fails. Unordered receipt records
therefore do not suffice uniformly.

These indistinguishability arguments concern classes of omitted information.
They do not say that every field of every concrete trace is necessary, that the
whole trace is an information-theoretically minimum encoding, or that no semantic
compression is possible. Last-occurrence normalization is itself a useful
observation-specific compression.

## 12. Limits

The semantics is not a claim about unrestricted model transformations, external
side effects, implicit reads, arbitrary multi-cell predicates, unbounded allocation,
rematching, or deployed repositories. An equality test between two changing cells
is not in general a conjunction of unary tests; it must either be excluded or
represented by explicit singleton observations with the corresponding stronger
stability requirement. The fixed catalog can represent finite graph edits but
not arbitrary fresh-name generation. Local clause optimality concerns flat CNFs
without auxiliary variables. Local minimum explanations and globally minimum
policy conflicts have different quantifiers. The footprint confluence fragment
is conservative. General results above are mathematical arguments; actual
executable evidence is bounded by the artifact admission limits.

## 13. Exact Boolean expressivity without hidden aspect variables

Let M2 be the Boolean functions expressible as a conjunction of non-tautological
clauses, each with one or two negative literals and at least one positive literal.
The empty conjunction is allowed. Variables are exactly the visible aspect tags;
there is no existential projection of auxiliary tags in this definition.

**Theorem T22 (expressivity).** The valid-retention functions of the scalar
constant-overwrite calculus with unary observations and an executable full trace
are exactly M2. Boolean scalar cells suffice for the converse construction.
The same upper bound holds with the declared graph-presence typing rule.

**Proof.** In the forward direction, T6 and T8 express validity as a conjunction
of local clauses. Each has the negative reader literal and at most one additional
negative writer literal. Since the full retention is valid, every clause has at
least one positive literal: an all-negative clause would be false at full
retention. No variable occurs in both polarities in one normalized local clause.
This gives an M2 representation. Static type preservation introduces no extra
retention restriction beyond enabledness, by T1, so the upper bound also holds
for the typed graph fragment.

For the converse, allocate one fresh Boolean cell, initially zero, for each
clause, and concatenate its event gadget with the other clause gadgets. For a
clause (not r OR p_1 OR ... OR p_k), let each p_j write one to the fresh cell, then
let r observe one. Its exact validity condition is the given clause. For a clause
(not r OR not b OR p_1 OR ... OR p_k), first let b write one, let every p_j write
zero, and finally let r observe zero. Its exact condition is again the clause.
There are no other observations and no other writes to this cell. Tags may be
shared between gadgets, but cells are fresh, so T6 makes their conjunction exact.
At full retention the last positive writer establishes the observation in either
gadget, so the original full trace is valid. Empty conjunctions use no events.
The number of cells is the number of clauses and the number of events is linear
in the total literal count. All effects are Boolean constant writes. QED.

This is an expressivity statement about a specific trace language, not the
invention of the Boolean clause class or a general new knowledge-compilation law.
In particular, it does not follow just from satisfiability being NP-complete.

**Corollary T23 (strict expressivity boundary).** Not every Boolean retention
function true at both the empty and full retention can be expressed without
additional aspect variables. One excluded function on four tags is

    not a OR not b OR not c OR d.

**Proof.** Any non-tautological implicate of a single clause must contain that
clause: otherwise falsify the proposed implicate and satisfy a missing literal
of the original clause. Thus every non-tautological implicate of this function
has at least three negative literals. An equivalent M2 conjunction would have
an M2 clause as an implicate, which is impossible. The clause is true on the
all-zero and all-one assignments, so the two endpoint conditions alone do not
explain the exclusion. QED.

## 14. A sharp one-write/two-write boundary

The number of writes to a cell counts event occurrences, including idempotent
writes; it is not the number of distinct written values or distinct tags. The
following results keep the event order fixed and preserve recorded observations.

**Theorem T24 (one-write fragment).** If every cell is written at most once in
the entire trace, valid retentions are defined exactly by binary requirements
r implies a. A policy has a unique maximum valid completion when feasible. It can
be found by reachability/closure propagation, gives minimum unit-cost collateral
deletions, and every infeasible consistent policy has a two-fact minimum core.

**Proof.** Consider an observation of a cell. If there is no earlier writer,
full-trace validity says its base value satisfies the observation, so it imposes
no restriction. If its earlier writer has the same tag as its reader, retaining
the reader necessarily retains that writer; again there is no restriction.
Otherwise the only possible observed values are the base value and the unique
earlier writer's value. Full-trace validity says the written value is accepted.
If the base value is accepted too, the observation is unconditional. If not,
retaining reader r requires retaining writer a. These are exactly all local
conditions, and T6 proves exactness of their conjunction.

Given forced-keep P and forced-remove D, start by blocking D and repeatedly block
r whenever r requires a blocked a. Let Z be the resulting closure. Every valid
policy completion must exclude Z, by induction over this propagation. Conversely,
A minus Z satisfies every requirement: if it contained r but omitted a, propagation
would also have blocked r. Thus A minus Z is the unique largest possible valid
retention. It is a policy completion exactly when it contains P. When feasible,
any smaller completion removes at least one additional optional aspect; with
unit positive costs, A minus Z is also the unique minimum-collateral completion.

If infeasible, some p in P reaches some d in D through the requirement relation.
The two facts keep(p) and remove(d) already conflict. Neither any single keep
fact nor any single remove fact conflicts: the full trace witnesses the former
and the empty trace the latter. Hence two is exactly minimum. Consistency of P
and D excludes the uninteresting same-tag contradictory pair. A search from D
in the reverse requirement graph both decides feasibility and extracts a path.
The graph construction and reachability take linear time in the graph size after
scanning the trace. QED.

Aspect occurrences may interleave, so the requirement relation can have cycles.
If each aspect is one contiguous block, every requirement points to an earlier
block and the relation is acyclic. Neither case changes the closure argument.

**Theorem T25 (two-write hardness).** Policy feasibility is NP-complete even if
all cells are Boolean, each cell is written at most twice, each aspect has exactly
one event, and the policy contains exactly one forced-keep and one forced-remove
aspect. Every nontrivial local prime obstruction then has at most three literals.

**Proof.** Begin with the construction in T17 for a nonempty 3-CNF formula; pad
short nonempty clauses by repeated literals to length three. The x_i cells have
two writers, p_i and d; the y_i cells have two writers, p_i and n_i. Replace each
clause cell, which could have three writers, as follows. For C_j with literals
L_1,L_2,L_3, introduce initially-zero root and child cells c_j and b_j. The aspect
for L_1 writes c_j=1; the aspects for L_2 and L_3 write b_j=1. Add one fresh
optional aspect q_j, whose single event observes b_j=1 and writes c_j=1. Put all
q_j events after the variable events and before the final reader. That reader
observes c_j=1 as before. Repeated literals merely coalesce writes within a single
event; no cell has more than two writer occurrences.

The all-retained trace is valid: every child has at least one literal writer,
so every q_j runs and every root is one. The policy still keeps only the final
reader and removes only d. As in T17, exactly one of p_i,n_i is retained for each
variable. If the policy is feasible, a root being one means either L_1 was chosen
or q_j was retained. In the latter case its child observation requires L_2 or
L_3 to have been chosen. Thus every clause is satisfied. Conversely, given a
satisfying assignment, retain exactly its chosen variable aspects and retain q_j
exactly when at least one of L_2,L_3 is chosen. Every retained q_j is enabled,
and every root is one because either L_1 or one of the other literals is true.
This supplies a valid completion. The construction is polynomial, and membership
in NP is direct replay.

For the local bound, normalization leaves at most two representative writers.
A base clause has the reader and at most two positive writers. A bad-writer
clause has the reader, one bad writer and at most one later good writer. Anchor
normalization can only remove representatives. Thus all local prime clauses
have at most three literals. QED.

This strengthening separates the semantic writer-count threshold from the
standard NP-completeness result used as its starting point. It does not rely on
interleaving several occurrences of an aspect or on unbounded domains.

**Theorem T26 (large global cores with ternary local obstructions).** For every
k at least two, there is a valid Boolean trace with 2k-1 aspects, one event per
aspect and two writes per cell, whose local prime clauses have size three, but
whose designated policy has minimum conflicting subpolicy size k+1.

**Proof.** Take a full binary tree with k leaves. Allocate one initially-zero cell
for each internal vertex. The aspect of each non-root vertex writes one to its
parent's cell. An internal-vertex aspect additionally observes its own cell to
be one. Order events from children to parents. Each internal cell is written
exactly twice, once by each child; each aspect occurs once. At full retention
all observations hold. The local clause at an internal vertex v is precisely
not v OR left(v) OR right(v), of size three.

Force the root retained and every leaf removed. Any retained internal vertex
needs a retained child. Following such a child must eventually reach a retained
leaf because the tree is finite, which contradicts the policy. If the root-keep
fact is removed, the empty retention is a witness. If a particular leaf-removal
fact is removed, retain exactly that leaf and its path to the root. Every retained
internal vertex has a retained child; no other leaf is retained. This is a valid
witness for deleting that one policy fact. Hence every proper subpolicy is
feasible (it lies below one such single-fact deletion), while all k+1 facts
conflict. They constitute a cardinality-minimum global core. QED.

The construction shows why a bound on local explanations does not bound global
policy explanations. It also distinguishes cardinality-minimum from merely
inclusion-minimal: here every proper subpolicy is feasible, so both notions
coincide for a proved reason, not by terminology.
