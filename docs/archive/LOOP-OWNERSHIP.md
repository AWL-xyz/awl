# Entry-state-preserving ownership loops (0.18)

A while body may consume/refill eligible outer spool owners if every
continuing backedge restores their abstract entry state. Both maybe-moved and
definitely-empty facts must match for each visible outer owner, by lexical symbol.
Live entry → consume → refill → live is accepted. Empty entry → refill → consume
→ empty is accepted. Live → empty or empty → live backedges are rejected (E225).
If/match arms compose; paths returning from the function need no backedge proof.

```
scoped b:spool=make(0)
while i<100000 do
    finish(move b)
    b=make(i+1)
    i=i+1
end
```

The condition is checked under entry ownership state without consuming permission.
The invariant makes that state valid at every subsequent condition evaluation.
After the loop, entry ownership is retained: zero iterations are possible. No
constant-condition pruning is performed, including for while false. An all-return
body has no continuing backedge but still leaves the zero-iteration path.

Nested loops each independently prove their own invariant. Local/pattern shadowing
cannot hide an unrestored outer owner. Fresh iteration-local owners clean up each
iteration and need not survive the backedge. Refill keeps the original lexical
cleanup registration; final carried owner releases outside the loop. Unavailable
handles can cycle; this concerns ownership, not allocation-success inference.

Checker and read-only verifier independently reconstruct and compare states.
There is no new runtime flag/copy/refcount/cleanup registration. This is a bounded
entry-invariant rule, NOT arbitrary fixed-point/widening or changing-invariant
inference. No break/continue, live-owner replacement, move-expression refill,
owned aggregates/other resources, owned strings, general references or trap unwind.
See examples/loop-owners and tests/test_loop_owners.py.
