# Fixed-size typed arrays — 0.9.0-dev

Implemented native **filesystem project** feature, not dynamic arrays, slices,
heap collections, generics, borrowing or an ownership model.

```Awl
function doubled(input:[i64;4])->[i64;4]
    local result:[i64;4]=input
    local i:i64=0
    while i<array.length(result) do
        result[i]=result[i]*2
        i=i+1
    end
    return result
end
function main()->i64
    local original:[i64;4]=[3,7,11,15]
    local result:[i64;4]=doubled(original)
    print(original[0]) -- 3: parameter/local assignment copies values
    print(result[0])   -- 6
    return 0
end
```

## Type and value rules

`[T;N]` is a structural value type: same element type and count means the same
array type. N is a decimal compile-time constant from1 to1024, canonicalized in
typed IR. Zero-length arrays/empty literals, inferred locals, inferred lengths,
variable lengths, repetition initializers and generic type parameters are absent.
The array type is limited to128 canonical characters, including resolved module
names; existing depth/source/token/arena budgets still apply.

`[e1,e2,...]` evaluates elements left-to-right once, requires identical non-unit
value types and infers `[T;count]`. No implicit numeric promotions. Elements may
be integers, bools, immutable strings, resource descriptors, structs, unions or
nested arrays. Arrays may appear in fields, union payloads, locals, parameters and
returns, including module-qualified nominal elements. Different nominal structs
from different modules remain different types even if their layouts match.

Assignment, parameters and returns copy arrays by value, recursively. Updating a
copy does not update the original array. **Resource descriptor elements still
alias their resources** (like resource fields in existing structs); copying an
array neither clones resources nor transfers ownership. Strings retain their
existing immutable region-backed storage policy. No automatic element destructor
or whole-array release is added. Use explicit/deferred releases appropriately;
static ownership/borrow/escape checking remains unfinished.

Array equality, arithmetic, implicit conversion, ordinary whole-array print,
concatenation, resize, iterators and views are deliberately absent. Explicit loops
and element operations are available. These limitations are type errors, not
implicit pointer/C array behavior.

## Indexing, stores and length

`a[index]` requires an **i64** index. Negative values, values≥N and extreme i64
indices abort with `Awl array bounds trap`, without accessing storage. No unchecked
access/implicit unsigned conversion is exposed. These traps are not recoverable
Result values and do not unwind deferred cleanup.

`a[index]=value` requires a mutable local-rooted place (including nested field/
index chains), with exactly matching element type. Temporary array values cannot
be assignment roots. Base/index computations are sequenced once, left-to-right;
every target index is checked before the right-hand expression executes. Nested
updates such as `rows[1].points[2].x=42` are permitted when the types match.
Read indexing evaluates the base array value, then index. Chained field/index
selection binds more tightly than arithmetic/comparison.

`array.length(a)->i64` returns the fixed element count. The argument is still
evaluated once, even though length is known from its type; side effects are not
skipped. It is an intrinsic special type rule, not a user-overloadable function or
an entry in the fixed-signature platform registry. It is reserved for declarations/
module resolution like print. It counts array elements, never UTF-8 bytes/scalars.

Awl uses explicit expression grammar, not newline-as-semicolon insertion. When
an expression statement beginning with `[` follows another expression, a `;` may
be required to distinguish a new array literal from postfix indexing of the
previous expression (e.g. `local x:i64=0; [1,2][0]=x` parses, then fails because the
store root is temporary). A trailing comma in an array literal is not accepted.

## Layout and limits

Each array is a generated C11 struct wrapper with one N-element data member, so
it can be copied/passed/returned by value without C array-to-pointer decay. Array
size is element size×N and alignment is element alignment. Arrays participate in
the existing nominal aggregate dependency order; nested/nominal layouts and value
cycles are checked independently by checker and typed arena verifier. An array
inside a recursive by-value struct does not make that recursion legal.

Each array/aggregate value is limited to1MiB and layout height64. Multiplication
is checked before computing layout size. These are per-value/compiler budgets,
**not a whole-program stack/memory safety guarantee**. Large by-value temporaries,
large frames and recursion can exhaust the native stack. The initial read lowering
can copy the base array to a temporary; optimizing compilers may remove copies,
but no zero-copy or O(1) whole-operation performance guarantee is made. Logical
indexed access after obtaining a value is constant-time; value-copy cost scales
with its size. No heap allocation is added by the array representation itself.

Only the project scanner accepts `[`/`]`; legacy scanner/byte/token parser paths
keep their earlier quote/bracket error behavior. Python reference retains its older
subset. Existing opaque C parser ABI remains1; typed arena node kinds are extended
(`array`, `index`;0.9.1adds `array_repeat`), not a stable cross-version interchange format.

## Validation and accepted milestone

`examples/arrays/main.aw` exercises function/struct value copies, checked updates
and nested arrays. `tests/test_arrays.py` includes all integer widths/bools,
strings/resources, aggregate layout/union cases, unused nested runtime types,
cross-module types/returns, effect ordering, read/write bounds, invalid lvalues,
count/layout/recursive budgets, deterministic emission and40seeded matrix updates
atO0/O3. Native verifier corruptions check literal/index/length-call metadata and
shapes separately from Checker; sanitizer and final-artifact/offline reports
record actual executed acceptance. No formal safety proof or audited container
library is claimed.

Planning credit: this closes the fixed-array/literal/indexed-place/value-integration
submilestone, raising the core-language maturity estimate35→38 on the existing
20-point category (+0.60 planning points), **only on accepted implementation/test
completion**. It does not credit unfinished dynamic collections or ownership.
The resulting broad estimate is~15.5%, not measured universal language completeness;
see ROADMAP.md. The user requested work milestones worth at least0.25planning points;
failed gates earn no credit, and progress updates do not manufacture percentages.

0.9.1adds `[seed;count]`; see REPEATED-ARRAYS.md for once-only evaluation, copy/alias rules and new validation. The0.9.0milestone credit above is historical; current overall planning estimate is~15.8%.
