current source uses `@b name:spool` and now supports explicit reserve/scalar truncation, see [BUILDER-GROWTH.md](BUILDER-GROWTH.md), the0.11 examples below are historical legacy spelling

# Nonescaping builder borrow parameters — 0.11.0-dev

```Awl
function label(borrow b:text_builder,n:i64)->i64
    text_builder_clear(b)
    text_builder_append(b,"frame=")
    text_builder_i64(b,n)
    return text_builder_bytes(b)
end
function main()->i64
    scoped b:text_builder=text_builder_new(64)
    if not text_builder_valid(b) then return 1 end
    print(label(b,42))
    text_builder_print(b)
    return 0
end
```

A declared `borrow` parameter grants a synchronous helper temporary use of a
builder descriptor without transfer or release. The helper can use the11approved
builder intrinsics and forward the descriptor to other declared borrow parameters.
It cannot copy it into a local/array/struct/union, store it elsewhere, return it,
reassign it, free/defer-free it, or pass it to an ordinary by-value parameter.
E220 rejects those uses, including in unused functions. Forward/recursive and
cross-module calls work; every function body is checked, not trusted as an
unchecked annotation. Numeric/status results and independent string snapshots
may return. Fresh independent manual allocations may return; that is not transfer
of the borrowed input.

## Exact limits and alias semantics

- Only `borrow name:text_builder`, only native filesystem project parameters.
  Primitive/string/array/nominal/other resource borrow types are not implemented.
  Legacy byte/token APIs keep `borrow` as an ordinary identifier. Project parser
  reserves it contextually; this is not a new reference/pointer type.
- No named reference lifetimes, general references, moves/ownership transfer,
  returned borrowed references, closures, async or exclusive-borrow checking.
- These are **shared, synchronous mutable descriptor borrows**, not exclusive
  Rust-like references. Passing the same builder to two borrowed parameters is
  allowed; operations execute in source order. Nested argument calls run
  left-to-right before the helper body. No data-race/thread-safety claim.
- A scoped owner is allowed only in declared borrow parameter positions. It is
  still invalid in another ordinary parameter of the same call. The original
  scope remains responsible for normal-exit cleanup. Callees do NOT add cleanup
  for borrow parameters and cannot explicitly free them.
- Ordinary manual handles/expressions can be passed too. That does not make their
  other aliases lifetime-safe: another manual parameter/alias could free the
  resource, leading to an existing runtime stale-handle trap. The callee contract
  restricts uses of the borrowed formal, not every alias in an arbitrary manual
  caller. Unavailable descriptors can be borrowed for validity checks. No implicit
  ownership is created for a temporary allocation passed to a helper; use a scoped
  binding when automatic lifetime management is intended.
- Validity checks/allocation failure remain explicit. Abort/signal/forced exit
  does not unwind scoped cleanups. Snapshot storage still uses the bounded
  process-lifetime string region; no safe general string reclamation is added.

## Architecture / trust boundary

Parser emits `borrow_param` rather than pretending a normal parameter transfers
ownership. Checker builds per-parameter modes before checking any bodies, records
restricted bindings, and grants use only in explicit safe argument contexts.
The independent verifier reconstructs modes from validated declaration kinds,
validates borrowed type/project syntax, and repeats the call-site and body rules.
It never trusts a serialized borrow flag or skips checking a recursive callee.
The normal whole-project verifier still checks graph/provenance/type/symbol/layout
budgets before C emission.

Native C ABI representation remains a by-value opaque descriptor; borrow is a
compile-time use restriction, not a heap wrapper or new runtime reference-count.
Module resolution, declarations, unused runtime types, all argument positions
and deterministic emission include the new kind. There is no unrestricted FFI
or first-class callable value in this feature. Trusted built-in operations must
remain synchronous/non-retaining; this is not a formal safety proof.

## Executed validation

-16new borrow methods: modules/forward calls/recursion, parameter positions,
  duplicate borrows, manual callers, snapshots/fresh returns, all copy/escape/free/
  reassignment paths, wrong modes/types, unavailable handles, nested sequencing,
  shadowing and deterministic C.13new private verifier mutations bring total207;
  positive legacy `borrow` identifier regression retained.
-408methods per compiler configuration, no skips;125resource/array/owner/borrow
  emitted-C ASan/UBSan methods plus13actual platform methods. Native frontend
  ASan/UBSan/fuzz/provenance/driver and integer oracles pass. Final full archive
  isolation and extracted tests are recorded separately. No Windows runtime,
  remote CI, broader kernel/distro/ARM acceptance or formal proof claimed.
- Replaced feature-test release allowlists with tested minimum-version selection
  (4new selection-policy tests). Initial3platform skips exposed old sub-test gates;
  corrected. During gate refactoring2literal helpers were accidentally removed,
  causing3fixture errors; restored and reran all3full suites successfully.
- Seven alternating warm full builds compare a manual local+defer/by-value helper
  against a scoped owner+borrow helper, both reusing ONE builder across100k calls:
  medians91.080/96.969ms build,8.850/8.655ms whole-executable runtime,
  checksum1088890. Tiny local optimizer/startup-dependent samples do not prove a
  general speedup, zero-cost, heap/RSS or large-application performance contract.
  See benchmarks/borrows-latest.json. Windows example cross-links PE32+ only.

Conditional accepted roadmap credit: memory/resources/errors maturity11→14 at
unchanged20-point weight gives+0.60points:16.35→16.95 (~17.0%). Subjective planning
estimate, not measured universal completeness. No credit for general references,
exclusive borrowing, ownership transfer, dynamic containers or string reclamation.
