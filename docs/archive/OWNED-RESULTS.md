# Owned builder results (0.14 development)

Native projects may declare `function make()->own spool`. Return an
existing owner explicitly with `return move name`, or forward a direct call to
another owned-result function. Callers must adopt the result into a new
`scoped` binding or directly forward it as their own owned return.

```
function transform(own b:spool)->own spool
    spool.append(b," / returned")
    return move b
end
```

The return snapshots and clears the source descriptor before normal-exit
cleanup. The adopted destination registers its own guarded cleanup. Ownership
moves, not payloads; no clone, reference count or second allocation is required.
An unavailable handle remains unavailable and can still be transferred.

Discarding an owned result, adopting it into a manual local, passing it as a
borrow, or returning it through an ordinary result is rejected (E223). Manual
and borrowed handles cannot become owners. Allocate into a scoped binding
before returning it; `return spool.new(n)` is not an owned return.

A terminal `return move` can transfer a visible outer owner from a nested
branch or loop: that execution path exits the function. This does NOT allow
nonterminal cross-block moves or establish general branch/loop state joins.
Consuming arguments to direct owned-result calls remain same-block only.
Other resources, aggregates, general references, trap unwinding, owned-string
reclamation and dynamic containers are not covered. Ordinary manual builder
results retain their previous manual semantics.

See examples/owned-results and tests/test_owned_results.py. Development tests
are not a substitute for exact archive/offline acceptance.
