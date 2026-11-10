# Restricted scope-owned text builders — 0.10.0-dev

```Awl
scoped b:spool=spool.new(64)
if spool.valid(b) then
    spool.append(b,"hello")
    spool.print(b)
end
```

This is an opt-in, statically restricted resource lifetime, not merely shorthand
for a freely aliasable `local` plus `defer`. The owner is created here, cannot
escape, and is conditionally released on normal lexical exit or return. The
function return expression is evaluated before cleanup. Inner scopes clean
first; registration order is reversed within a scope, including ordinary defer.
Loops clean on each iteration; match arms and unit fallthrough are supported.
No heap cleanup stack/closure allocation is added.

## Enforced contract

- Native filesystem projects only. `scoped` is contextual to that grammar;
  legacy byte/token parser compatibility remains separate.
- Only `spool` and a direct `spool.new(capacity)` initializer (or a0.12same-block scoped move; see LOCAL-MOVES.md) are
  accepted. Helper-returned builders and arbitrary existing handles are rejected.
- The binding cannot be reassigned or copied, including into locals, structs,
  unions, literals/repeated arrays, element stores, ordinary by-value function arguments or returns. Explicit0.11borrow parameters are an exception.
- It can be used as the first argument of exactly11 synchronous built-in builder
  operations: valid, clear, capacity, bytes, length, append, codepoint, i64, u64,
  print and snapshot (all with the `spool_` prefix). Those calls temporarily
  use the descriptor; none returns/retains that descriptor. Since0.11, user functions may declare explicit `borrow` parameters; see BUILDER-BORROWS.md. Future intrinsics are NOT auto-approved.
- Explicit free and deferred free of this binding are rejected, preventing a
  second release. Diagnostic E220 identifies ownership-policy violations.
- Snapshot returns independent immutable string storage under the existing string
  region policy; it may leave the scope. Numeric/status values may also escape.
- Allocation is still recoverable through `spool.valid`: unavailable
  descriptors are not freed on exit. Negative/oversized capacity or exhausted
  slots yield unavailable descriptors. Zero-capacity builders ARE valid. Check
  validity before operations that require an available builder.
- Combined scoped/defer budgets:64registrations per lexical scope,256per project,
  including unused functions. E210 rejects excess before emission. Shadowing in
  inner scopes is permitted; unique resolved symbols preserve the outer owner.

## What is not provided

This is **restricted scope ownership**, not general ownership/borrowing/moves,
resource-bearing aggregate ownership, general reference borrowing, transfer,
reference lifetimes, shared ownership, or ownership of byte buffers/windows.
Ordinary `local` builders retain manual copyable-alias semantics. It does not
retroactively make all Awl programs statically lifetime-safe. There is no cleanup
on bounds/arithmetic/resource abort, signal, forced termination or exception.
The runtime is single-threaded. Freed payload returns to the allocator, not
necessarily the OS; automatic release is not an RSS/allocator-performance promise.
Snapshots still use the bounded process-lifetime string region (64MiB/65536
allocations). Safe general string reclamation and dynamic containers remain open.

## Independent checking and validation

Parser creates `scoped_local`, resolving it through the normal module/type/symbol
pipeline. Checker derives owned-binding state. The independent read-only verifier
reconstructs that state from declarations, validates freshness and explicitly
rechecks borrowing contexts and budget/type/shape constraints; it does not trust
a serialized owner bit or the checker result. Emission uses the verified immutable
symbol and existing lexical cleanup machinery, guarded by validity for allocation
failure. Intrinsic non-retention behavior is part of the trusted runtime boundary,
not a formal proof. No unrestricted native FFI exists in this feature.

`tests/test_scoped_owner.py` has16methods covering all allowed operations,
returned snapshots/status values,100k create/use/return/release calls, nesting,
LIFO interleaving, branches/matches/unit fallthrough, zero/invalid capacity and
slot exhaustion, modules/import-alias conflicts, cleanup budgets, and rejected
copy/return/aggregate/array/helper escape/free/reassign cases.12new private verifier
corruptions bring the targeted total to194. Native frontend ASan/UBSan/fuzz and
122emitted-C resource/platform sanitizer methods pass;388tests per compiler
configuration pass without skips. See scoped-owner-validation.json and the final
exact-archive report for release evidence. Remote CI is configured, not executed
here. Windows console example cross-links, but has NOT been run on Windows.

## Measured trade-off

Seven alternating-order warm full builds of equivalent manual/defer/scoped
programs measured medians85.893/82.707/94.046ms. Whole-executable runtimes for
100k create/append/format/return/release calls measured31.186/31.845/30.675ms;
all checksums1088890. Scoped adds valid-guarded cleanup versus direct manual/defer
free. Tiny workload/local samples do not establish a general speedup, zero-cost,
large-application throughput, peak memory, or production-readiness claim.
`benchmarks/scoped-owner-latest.json` records all samples and scope.

Conditional accepted planning credit: memory/resources/errors maturity8→11 at
unchanged20-point weight, +0.60points;15.75→16.35 (~16.4%). This is a subjective
roadmap estimate, not measured universal completeness. No general ownership,
dynamic-container or string-reclamation credit is awarded. Final distribution
acceptance is required before awarding this milestone.

0.11extends this original contract with nonescaping builder borrow parameters; see BUILDER-BORROWS.md. Original0.10test counts/credit above are historical.

0.12adds restricted same-block scoped-to-scoped moves with E221 use-after-move checks. Other cross-scope/function transfer remains unimplemented; see LOCAL-MOVES.md.

0.13permits explicit handoff into owning builder parameters; callee takes normal-exit cleanup responsibility. No owned return contract/general path merges yet. See OWNING-PARAMETERS.md.
