# Awl 0.5: exact-width integers and checked conversions

**Implemented in 0.5, partial M1.** This document records that increment;
[NATIVE-COMPILER.md](NATIVE-COMPILER.md) describes the subsequent 0.6 host migration. The fixed-width integer family is now complete at
8, 16, 32 and 64 bits. This is not completion of the whole language: references,
ownership, allocation, modules, generics, floats, GPU and a custom optimizing
backend remain unimplemented.

## Run it

```sh
python compiler/kcc.py run examples/integers.aw
python compiler/kcc.py run examples/integers.aw --sanitize
python -m unittest discover -s tests -v
python tests/sanitizer_matrix.py
python benchmarks/run.py --case integers
```

The example prints `4097`, `-128`, `32767`, `2147483647`, `255`, on separate lines.
The standalone sanitizer matrix requires a GCC/Clang host with ASan and UBSan;
it is separate from the regular suite because not every platform supports them.

## Types and literals

| Type | Minimum | Maximum |
|---|---:|---:|
| i8 | -128 | 127 |
| i16 | -32768 | 32767 |
| i32 | -2147483648 | 2147483647 |
| i64 | -9223372036854775808 | 9223372036854775807 |
| u8 | 0 | 255 |
| u16 | 0 | 65535 |
| u32 | 0 | 4294967295 |
| u64 | 0 | 18446744073709551615 |

Every width and signedness is a distinct static type. Decimal literals accept
an explicit suffix: `42i8`, `1024i16`, `65536u32`. An unsuffixed literal remains
i64; it is **not** inferred from the destination. `local b:u8=1` is rejected;
write `1u8`. The explicit `i64` suffix is supported as well.

All positive literal magnitudes must fit their chosen type. A direct minus plus
a signed minimum magnitude is folded before type checking, so `-128i8` and
`-2147483648i32` work. `-(128i8)` is rejected because the inner positive literal
does not fit i8. Negating a valid minimum value at runtime traps normally.
Leading zeroes are decimal, not octal. Hex, binary, separators, exponent syntax,
i128, floats and usize/isize are not part of this release.

Numeric tokens require a separator before a following identifier/digit beyond
the suffix. `1u128`, `1u8oops` and `1_u8` now produce a lexical diagnostic rather
than being interpreted as adjacent numeric/name tokens. Decimal integer tokens
remain capped at 256 digits before suffix processing.

## Operations

`+ - * / %` require exactly matching integer types and return that same type.
`< > <= >= == !=` require matching operand types and return bool. There are no
C-style integer promotions, implicit widening, mixed-signedness comparisons, or
boolean-to-integer conversions. Unary minus accepts signed integers only;
`not` continues to require bool. `print` accepts any integer type or bool.

The arithmetic rules are invariant across optimization levels:

- Addition and multiplication overflow trap.
- Subtraction outside the type's range traps, including unsigned underflow.
- Division/remainder by zero trap.
- Signed MIN/-1 division **and remainder** trap at every signed width.
- Signed division truncates toward zero; remainder has the dividend's sign.
- Negating a signed minimum traps.

For example, `255u8+1u8` traps even though C would promote both operands and could
represent 256 in an int. `127i8*2i8` also traps. Operations do not silently wrap
or change their result type. Explicit wrapping/saturating APIs and bitwise/shift
operators are still unimplemented, not implied by support for integer widths.

## Explicit conversions

A builtin integer type name in expression position is a checked conversion:

```lua
local small:u8 = 200u8
local wide:u64 = u64(small)
local signed:i16 = i16(small)
local byte:u8 = u8(signed)
```

`TargetType(expression)` requires exactly one integer expression. The source
is evaluated once, in normal left-to-right effect order. If its mathematical
value is outside the destination range, the conversion terminates with the
existing arithmetic trap. Otherwise the value is preserved exactly.

| Source → destination | Required check |
|---|---|
| Signed → signed | Check lower/upper limits when narrowing |
| Unsigned → unsigned | Check upper limit when narrowing |
| Signed → unsigned | Reject negatives; check upper limit if needed |
| Unsigned → signed | Check signed maximum unless widening is sufficient |
| Identical type | Preserve value; no range check needed |

Negative-to-unsigned conversion never reinterprets bits. Narrowing never truncates.
Boolean, unit, struct and union values cannot be converted with these builtins.
There is no generic cast, bitcast or pointer cast API yet.

An invalid literal such as `256u8` is a **compile-time error**. An explicit
conversion `u8(256)` is well typed but **traps when evaluated**. The checker does
not currently perform constant/range propagation or reject every predictably
failing conversion. It must not silently turn a conversion in an unexecuted
branch into an unconditional trap. A future fallible conversion API can return
an explicit union instead of aborting; it does not exist in this release.

`examples/integers.aw` demonstrates a concrete `ByteResult` and `try_byte` function
that checks an i64 range before calling `u8(x)`. This is ordinary user code, not
an automatically generated generic Result or a new exception mechanism.

The entry point remains `main()->i64`; a different-width result requires an
explicit conversion before return. Type names are reserved identifiers. Programs
that previously used newly reserved names such as `i8` as function/local names
must rename them; compatibility is not frozen in this bootstrap series.

## Compiler and native semantics

The type checker and read-only IR verifier now handle the whole integer family.
Numeric literal nodes retain `literal_type` separately from their checked `type`,
so suffix/range metadata and a forged result annotation can be checked separately.
The `convert` node carries a target type and one operand. The serialized schema
is `KIR0-structured-v0.5`; no stable serialized IR loader is provided.

The C11 backend uses stdint exact-width types. Checked signed 8/16/32-bit
add/subtract/multiply operations use int64 intermediates, which can represent
all intermediate products of two signed 32-bit inputs. Narrow unsigned arithmetic
uses uint64 intermediates; even the product of two maximum u32 values fits uint64.
Results are range checked before narrowing. The i64/u64 operations retain guarded
full-width arithmetic, without requiring compiler extensions such as int128.

Division/remainder explicitly check zero and the type-specific signed MIN/-1
case before C can execute an invalid operation. Conversion helpers compare ranges
before any out-of-range signed narrowing; signed/unsigned transitions never rely
on implementation-defined C conversions to establish the language result.
Printing explicitly widens arguments to int64/uint64 and uses matching inttypes
format macros, rather than depending on narrow variadic argument promotions.

Only integer helpers referenced by the generated program are emitted. The emitter
collects dependencies while lowering expressions and prefixes those helper bodies
before generated functions. Shared trap/boolean scaffolding can remain. This
reduces unnecessary generated C and unoptimized helper bodies; it is not a KIR
optimizer, whole-program dead-code eliminator, vectorizer or runtime performance
proof. Repeated uses share the same generated helper.

Aggregate size budgets now account for 1/2/4/8-byte scalar widths. Natural alignment
is estimated as the scalar width, as appropriate to the current x86-64 bootstrap
host model. C determines actual native layout. These remain compiler resource
estimates, not exported ABI/packing/sizeof or cross-target guarantees.

## Validation evidence

196 unittest methods pass locally with GCC 14.2.0, Linux x86-64, Python 3.13.16:

- All 158 previous tests remain passing; 38 methods were added.
- Every integer type's literal extrema, native parameters and returns are tested.
- 512 new seeded arithmetic/comparison expressions are checked against Python
  values at O0 and O3; earlier 400 scalar cases and 150 union matches remain.
- Every source/destination conversion pair (8×8 = 64) is checked at boundary values
  in both optimization modes. Additional tests cover representable source values
  outside each destination's range and require a runtime arithmetic trap.
- Overflow, underflow, negation, zero division and MIN/-1 trap tests run at O0/O3.
- IR mutation tests corrupt literal signedness, ranges, annotations and conversion
  targets/arity. Helper-dependency tests check selective C emission.
- 500 new source mutations bring the total to 2,750 cases.

The separate `tests/sanitizer_matrix.py` run passed 348 valid-value checks under
ASan and UBSan with `-fno-sanitize-recover=all`: 140 arithmetic boundaries plus
208 conversion values spanning all 64 type pairs. The integer example also passed
a sanitizer smoke run. This is not exhaustive testing of all integer values, all
invalid operations under sanitizers, a formal soundness proof, or an audit.

Logs: `tests/latest.txt`, `tests/validation.json`,
`tests/integer-sanitizer-matrix.json`, `tests/integers-sanitizer-smoke.txt`.
Linux Clang and Windows MinGW CI is configured but has not run in this workspace.

## Benchmark

`python benchmarks/run.py --case integers` executes 5,000,000 bounded state updates
with u16 state, u32 arithmetic and u64 accumulation. Each iteration explicitly
widens before computation and narrows after a modulo that bounds the result.
The C baseline uses equivalent stdint types and the same algorithm. Python checks
the final total and state outside timing. Expected output:

```
163800614844
10277
```

Local O3 medians over seven warmed-up process launches: Awl **21.514 ms**, C
**21.697 ms**, ratio **0.992×**. Raw samples: `benchmarks/integers-latest.json`.
The workload's values are bounded, so omitting checks in the C baseline cannot
cause overflow. Process startup is included; cores/frequency are uncontrolled
and run order is fixed. Small ratios around one do not establish a speedup or
language-wide performance parity. This does not benchmark SIMD or GPU behavior.

## Remaining gates

M1 is still incomplete: full expression ranges, broader coverage-guided fuzzing
and executed cross-platform CI evidence remain. Fixed-width integers, structs and
finite tagged unions are now implemented. Modules, owned memory, ownership-aware
MIR and borrowing remain separate subsequent work.
