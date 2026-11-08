# Scoped resource cleanup — 0.8.4-dev

Implemented native **filesystem project** language feature. This is lexical,
normal-control-flow cleanup, not ownership/borrowing, exceptions or general defer.

```Awl
function report() -> i64
    local b: spool = spool_new(64)
    if not spool_valid(b) then return 1 end
    defer spool_free(b)
    if spool_append(b,"hello café") != 0 then return 2 end
    return spool_print(b)
end
```

## Exact semantics

- Syntax: `defer spool_free(expr)`, `defer buffer_free(expr)` or
  `defer window_close(expr)`. Exactly one argument, with the release intrinsic's
  existing type. Arbitrary expressions, print, user functions, resource mutation
  and other calls are rejected (E200). No new foreign-call escape hatch.
- The handle expression is evaluated **once, immediately at registration** and
  captured by value. The release is not run until exit. Reassigning the variable/
  field later does not change which handle is released. Side effects in argument
  expressions happen at registration, not at cleanup.
- Each function body, if/else body, while body and match arm is a lexical scope.
  Run that scope's registered releases in **reverse registration order** on normal
  exit. On return, run all active scopes from innermost outward, each in reverse
  order. An inner if's defer runs at the end of that if body, NOT the function end.
- A loop body's releases run at the end of **each iteration**. A false branch or
  loop that never executes does not evaluate/register its deferred operations.
- Evaluate/capture the return expression **before** cleanup. Unit-return expressions
  also execute first. Normal unit-function fallthrough runs its cleanup.
- Captures are hidden generated C locals. This first lowering uses no runtime
  cleanup stack/closure allocation; cleanup calls are emitted on the relevant
  exits. Repeated emission revalidates the arena and resets emitter scope state.

An unavailable builder or zero buffer/window handle must be checked BEFORE
registering its release. Release functions retain their existing invalid/stale/
wrong-kind traps. A second registration for the same resource or an explicit
release before the deferred release can still double-release and trap. Registering
cleanup does not transfer ownership, reserve a borrow or prevent aliases.

Returning a builder whose release is deferred returns a **stale descriptor**:
this is not a supported ownership transfer. Runtime access still guards against
freed storage, but the compiler does not yet reject the escape. Immutable snapshots
are independent copies and obey the existing process-lifetime string policy.

## Boundaries and budgets

Cleanup is guaranteed by this lowering for **normal lexical exits and returns**.
It is not an unwinding mechanism for abort/arithmetic/resource traps, signals,
run-timeout kills, OOM termination, crashes, process exit from external code or
future exceptions/cancellation. If a cleanup itself traps, remaining cleanups are
not guaranteed to run. OS process-resource reclamation is distinct from deferred
language cleanup. No break/continue syntax is added by this milestone.

At most64 static defer statements per lexical scope and256 per loaded project
(E210). Limits count source registrations, not executed loop iterations. The
independent arena verifier separately checks scope/project budgets, project mode,
node shape/annotations and permitted release signatures. Existing source/arena/
depth and64MiB emitted-C limits still apply. Cleanup code can be duplicated across
return paths, trading code size for simple explicit lowering; no general zero-cost
or performance-optimal claim is implied.

`defer` is contextual project syntax/reserved as a declaration identifier in
project parsing. Legacy filesystem-free byte/token parser entry points retain
older grammar (including `defer` as an ordinary identifier). They do not opt into
this syntax. Python reference compiler does not implement it. Existing release
intrinsics/signatures and C scanner ABI are unchanged.

## Evidence and next steps

`examples/cleanup/main.aw` performs100,000 function calls with cleanup on every
return and demonstrates nested scope cleanup. `tests/test_cleanup.py` covers early
returns, capture timing/reassignment/field capture, LIFO order via a test-only
emitted-C trace, conditional registration, loop iterations, unit fallthrough/
returns, match arms, buffer payload reclamation, stale returned descriptors,
invalid expressions, budgets/provenance and deterministic emission. The desktop
fixture cycles100 actual authenticated X11 windows with scoped close, checking
that resources remain live within the scope and the16-live-window cap is not
exhausted. Native verifier corruption and sanitizer evidence is recorded with the
release validation; no general ownership/safety proof is claimed.

Next: explicit ownership transfer, destruction of owning values on all exits,
borrowing/escape checks, safe reclamation for ordinary strings and typed containers.
The general-purpose1.0 estimate remains~15% (subjective rubric in ROADMAP.md).
