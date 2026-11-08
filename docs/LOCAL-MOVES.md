# Restricted local builder ownership moves — 0.12.0-dev

```Awl
scoped building:spool=spool_new(32)
if spool_valid(building) then spool_append(building,"ready") end
scoped ready:spool=move building
if spool_valid(ready) then spool_print(ready) end
```

`move name` transfers a scoped builder descriptor into a NEW scoped binding in
**the same lexical block**. The source is consumed even if allocation was
unavailable. Any later use, validity check, assignment or second move of that
source is rejected with E221. The destination retains the payload/capacity/ID and
becomes the sole scoped owner. Ownership is not copied or manually adopted.

## Exact first-slice contract

- Only a direct `scoped destination:spool=move source` initializer.
  Chaining into further NEW same-block scoped bindings is allowed.
- Source must be an unmoved scoped owner declared in this exact block, not an
  ordinary manual builder, borrow/by-value parameter, aggregate field, index,
  returned resource, expression or already-moved binding.
- Both source and destination scopes must be the same lexical block. Moving an
  outer owner inside if/while/match/another block is rejected, including when a
  new inner binding shadows that outer owner's name. No path-merge/loop-move
  inference is claimed. This intentionally conservative rule also rejects moves
  from an outer block in a statically false branch/zero-trip loop.
- Owners freshly declared inside a loop body or match arm can move within that
  body/arm. Each iteration creates a fresh binding. Ordinary borrows before the
  move remain permitted; later borrows must use the new binding. Synchronous
  borrowed helper calls finish before the next move statement.
- No moving into an existing owner, manual local, function argument, return,
  array/aggregate, or arbitrary expression. No owning parameters/returns,
  cross-scope transfer, reassignment/reinitialization of moved slots, general
  reference/exclusive-borrow system or ownership of other resources yet.
- `move` is a contextual prefix when followed by an identifier; existing
  `function move(...)`, qualified `geometry.move(...)` and ordinary bindings
  named `move` remain usable. Legacy byte/token parsing remains unchanged.
- An unavailable descriptor may move; its new owner is still unavailable and
  safely leaves scope. Zero-capacity builders are valid. Validity/allocation
  failure checks remain explicit before operations requiring an available handle.
- Each destination registers cleanup at its declaration point. Thus cleanup
  follows the NEW owner's LIFO position, not the old creation position. It still
  interleaves with defer and normal scopes/returns. Source cleanup registrations
  remain guarded but see an empty descriptor. Combined cleanup budgets remain
  64registrations/scope and256/project; moves count even though they do not
  allocate another payload or consume a live runtime builder slot.

## Lowering and independent verification

The parser emits `move` with one name child. Only scoped-initializer checking can
consume it; general expression checking rejects it. Checker derives movable and
moved state from declarations and statement order. The same-block restriction
means this slice does not need to guess a merged moved state across branches or
loops; outer ownership cannot change through a move in a nested block.

The independent verifier reconstructs that state from the typed arena, checks
source eligibility BEFORE inserting the destination into its declared-name set,
and checks all later uses. Inserting the destination first could let an inner
same-name shadow masquerade as a local source. This was caught during review,
fixed before release, and covered by a private forged-arena regression. It does
not trust a serialized moved/movable bit or only the checker result.

Emission snapshots the verified descriptor, clears the original variable to
`(KSpool){0}`, then initializes the destination and registers its guarded
normal-exit release. Existing borrowed C descriptor representation and runtime
intrinsics remain unchanged; no payload copy, allocation or reference count is
added by the move. Exact release-order instrumentation verifies one free for the
original ID and the destination's LIFO position. This is not a formal proof or
universal zero-cost claim.

## Validation and remaining limits

`tests/test_moves.py`:16methods cover100k create/move/return/release calls atO0/O3,
chains, borrowing before/after, use-after-move across contexts, manual/borrowed
source rejection, invalid expression/return contexts, cross-block shadow attacks,
loop-local moves, independent outer shadowed ownership, unavailable/zero capacity,
exact release ID/order, early return/unit fallthrough, modules/alias conflicts,
cleanup budgets and deterministic C.12new private verifier cases bring total219;
a positive legacy move-identifier regression is included. Existing geometry.move
module regression exposed an initially reserved keyword; contextual prefix parsing
restored compatibility, with an additional positive function/local-name test.
Final regression/sanitizer/benchmark/archive results are recorded in
moves-validation.json and moves-release-validation.json; Windows cross-link is
not Windows execution and remote CI remains unexecuted.

Ordinary manual aliases retain runtime checks and can still be mismanaged. No
abort/signal/forced-exit cleanup, automatic immutable string reclamation, general
ownership transfer, dynamic containers, thread safety or production security
certification is added. See SCOPED-OWNERS.md and BUILDER-BORROWS.md.

Conditional accepted planning credit: memory/resources/errors maturity14→15.5 at
unchanged20-point weight, +0.30points;16.95→17.25 (~17.3%). Subjective roadmap
judgement, not measured universal completeness. No credit for the explicitly
unimplemented general transfers/path merges/owned aggregates/string reclamation.

## Local benchmark

Seven alternating-order warm full builds compare scoped builders with and without
one local move before return: medians99.212/98.540ms. Whole-process100k
create/append/format/return/release runtimes37.636/36.870ms; checksum1088890.
Tiny local samples do not establish a general speedup/zero-cost or memory/RSS
contract. Optimizers may remove the empty source's guarded cleanup. See
benchmarks/moves-latest.json for all samples and limitations.

0.13extends explicit moves to declared owning builder parameters in restricted direct-call contexts. The same-block local move contract above remains; owning function RESULTS are still unsupported. See OWNING-PARAMETERS.md.
