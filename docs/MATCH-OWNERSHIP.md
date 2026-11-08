# Exhaustive match ownership (0.16)

Native project match arms may consume an eligible visible spool owner:
move it into a scoped local, pass move name to an owning parameter, or forward
an owned result. Each arm begins from the SAME incoming state. Exhaustiveness
and duplicate-arm checks remain mandatory; no guard or constant-tag pruning.

At the join, an owner is unavailable if any continuing arm consumed it. Arms
whose bodies always return do not contribute to the continuing state. Nested
if/match joins compose. The state tracks unique lexical symbols rather than
names: a numeric pattern binder named b shadows, but does not consume, an outer
owner named b. Moving then shadowing the outer name cannot resurrect its owner.

Cleanup remains lexical and guarded. A retained owner releases in its outer
scope; a moved owner releases at its destination or owning callee. The original
descriptor is cleared before handoff; there is no payload clone, runtime join
flag, reference count or new allocation. Checker and read-only verifier derive
states independently. See examples/match-joins/main.aw and test_match_joins.py.

This extends 0.15 if joins; it is NOT general ownership. While bodies remain a
consumption barrier for outside owners, including nested match/if routes. Fresh
loop-local owners can dispatch within an iteration. Loop-carried moves,
reinitialization, owned aggregates/other resources, general/exclusive references,
owned-string reclamation and trap unwinding are still unsupported. Terminal
owned returns can move a visible owner because that path leaves the function.
Ordinary manual descriptors retain their manual aliasing/cleanup semantics.
