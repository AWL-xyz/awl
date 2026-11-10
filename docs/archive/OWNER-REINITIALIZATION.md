# Definitely-empty owner reinitialization (0.17)

After an eligible scoped/own spool binding is definitely consumed, it can
adopt a fresh spool.new call or a direct owned-result call by assignment:

```
finish(move b)
b=make()
```

The original binding symbol and cleanup slot are reused. The new descriptor is
released by that original lexical normal-exit cleanup registration, not at the
assignment's position. This matters for LIFO release order. No extra cleanup
registration, payload copy, reference count or runtime liveness flag is added.

The checker and independent verifier reconstruct two facts: maybe-moved and
definitely-empty. At if/match joins, maybe-moved is a union; definitely-empty is
an intersection over continuing paths only. A returning path does not contribute.
If all paths refill, the binding becomes usable again; if only some refill, both
use and another overwrite remain rejected. Pattern/local shadowing tracks unique
symbols, including hidden outer emptiness. E224 rejects unsafe or unsupported
reinitialization. Live-owner overwrite and borrowed-binding assignment remain
E220. Refill RHS is fresh allocation or owned call only: not a manual descriptor,
name/alias, or move expression. Unavailable fresh handles can be adopted safely.

Loop barriers remain: an outside owner cannot be consumed OR reinitialized from
inside a while, even if it appears empty before the loop. Fresh iteration-local
owners can reinitialize within that iteration. Loop-carried ownership needs a
separate backedge analysis. No general resource replacement, owned aggregates,
other owned resources/strings, general references, exceptions or trap unwinding.
See examples/reinit/main.aw and tests/test_reinit.py.
