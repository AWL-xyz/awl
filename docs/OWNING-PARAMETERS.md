# Restricted owning builder parameters — 0.13.0-dev

```Awl
function finish(own b:spool)->i64
    spool_print(b)
    return spool_bytes(b)
end
function main()->i64
    scoped building:spool=spool_new(32)
    if not spool_valid(building) then return 1 end
    spool_append(building,"ready")
    local count:i64=finish(move building)
    print(count)
    return 0
end
```

The caller explicitly transfers a unique scoped builder. The callee owns its
parameter and conditionally releases it on normal lexical exit/return. The old
caller binding is consumed; later reads, validity checks, borrows, assignment or
second transfer are E221. The descriptor/payload is not cloned. No extra live
builder slot, heap cleanup closure or reference count is added by transfer.

## Deliberately restricted first contract

- Only `own name:spool` in native filesystem-project parameter lists.
  Other owned parameter types/owned aggregates/windows/buffers are not provided.
  `own` remains an ordinary function/binding identifier outside the parameter
  prefix, including a normal parameter named own. Legacy parsing is unchanged.
- Every owning argument must be `move name` from an unmoved scoped owner declared
  in the CURRENT lexical block. Ordinary manual handles, borrowed parameters,
  unbound allocations and outer-block owners cannot be adopted as unique owners.
- A transfer is accepted only in a DIRECT call used as an expression statement,
  a new ordinary local's initializer, or the direct return expression. Other
  ordinary arguments may compute normally, but nested consuming calls, conditions,
  loop tests, binary/short-circuit expressions, assignment/store right sides and
  aggregate initializers are rejected. Bind a status result first, then branch.
  This is not a path-sensitive general ownership/control-flow analysis.
- Owning parameters are considered owners declared at the function body's entry;
  they can be forwarded to another owning helper or moved into a new scoped local
  in that body. Root-body rebinding/shadowing of the owning parameter is rejected.
  Nested scopes may borrow but cannot transfer that outer owner. Loop-local owners
  can transfer within their iteration. Direct recursive forwarding is supported.
- Callee-owned parameters have the same no-copy/no-escape/no-manual-free/no-reassign
  rules as scoped locals (E220). Returning that descriptor, including `return move
  b`, is NOT implemented: there is no owned-result function contract yet. Status,
  numeric and independent string-snapshot results may return. A fresh unrelated
  manual allocation can return under existing manual semantics; this is not an
  ownership-returning API or automatic management of unrelated manual handles.
- A call cannot borrow AND consume the SAME owner, nor consume it twice. Borrow
  before consume is explicitly rejected E222; use after an earlier consuming
  argument is E221. Distinct borrowed and owned builders in one call are supported.
  This closes a transient-alias route where a callee could forward/free its owned
  formal and then use a still-borrowed alias. Existing shared-borrow-only calls
  remain allowed. Arbitrary manual callers retain their prior runtime alias caveats.
- E222 diagnoses invalid consuming contexts/sources. E221 still diagnoses moved
  bindings; E220 covers other restricted-owner escapes and invalid owned types.
- Parameters register cleanup in declaration order BEFORE body-local registrations.
  Body locals clean first, then owning parameters in reverse parameter order,
  interleaved with existing defer. Return expression is evaluated BEFORE cleanup.
  A parameter transferred onward is emptied, so its former cleanup is skipped.
- Unavailable descriptors transfer safely and are skipped on free. Zero-capacity
  builders remain valid. Validity/allocation failure checks remain explicit before
  operations requiring available storage. Normal-return cleanup is NOT abort,
  exception, signal or forced-termination unwinding.
- Combined own-parameter/scoped/defer cleanup budgets:64per function-root or lexical
  scope,256per project, including unused functions. There is no total-stack or
  recursion-depth safety guarantee. Slots/allocator/immutable-string limits remain.

## Architecture and independent validation

Parser emits own_param; checker builds per-position consuming modes before checking
any function bodies. Direct-call contexts supply the current block's eligible
owners, validate explicit moves left-to-right, reconstruct consumed state and
reject borrowed/consumed symbol overlap. Callee entry reconstructs restricted,
movable owned bindings and cleanup-budget usage. No serialized ownership flag is
trusted. The independent read-only verifier separately derives the same signature
and entry facts, checks source state/context/alias disjointness, and validates all
bodies, including recursion/unused functions, before C emission.

C ABI stays by-value opaque builder descriptors. Existing move lowering snapshots
and clears the caller; the verified callee registers validity-guarded normal-exit
cleanup at entry. There are no foreign calls/first-class function values introduced
here. Built-in borrows must remain synchronous and non-retaining. This is a
restricted source-language guarantee under that runtime boundary, not a formal
proof, general reference type system or production security certification.

`tests/test_own_params.py` has16methods:100k module handoffs atO0/O3, direct unit/
status/return-call contexts, recursion, after-call use/assignment/double move,
manual/borrowed/temporary adoption rejection, callee copy/free/escape rejection,
local relocation/borrow, alias and duplicate arguments, every parameter position,
nested/control-flow/cross-block rejection, loop-local transfer, unavailable/zero
capacity, exact release ID/LIFO order, module alias/contextual own names, type and
scope/project budgets, unused runtime dependencies and deterministic C. Private
verifier corruptions and final sanitizer/regression/archive results are recorded
in own-params-validation.json and own-params-release-validation.json. Cross-link
is not Windows execution; remote CI remains unexecuted.

## Remaining ownership work

Owned function results, transfer into existing slots, branch/loop moved-state
joins, resource-bearing aggregates, more resource types, owned strings and dynamic
containers remain separate gates. Synchronous descriptor borrowing is not exclusive
or general reference borrowing. Snapshots still use the bounded process-lifetime
string region. Manual resources can still be leaked or mismanaged; freed payload
returns to the allocator, not necessarily the OS/RSS.

Conditional accepted credit: memory/resources/errors maturity15.5→17.5 at fixed
20-point weight adds+0.40planning points:17.25→17.65 (~17.7%). Subjective roadmap
judgement, not measured universal completeness. No credit for owned results or the
explicitly unimplemented ownership/control-flow/container work.

## Local measurements

Seven alternating-order warm builds compare borrowed helper/caller cleanup against
owning helper/explicit handoff/callee cleanup, otherwise equivalent100k create/
append/format/helper/return/release calls, checksum1088890. Median full builds
97.191/101.291ms; whole-executable runtimes44.613/40.425ms. These tiny local samples
include startup/output and optimizer inlining/elimination of empty caller cleanup;
not a general speedup/zero-cost/RSS/allocator/large-application contract. Full data:
benchmarks/own-params-latest.json. Windows console example cross-links only; not run.
