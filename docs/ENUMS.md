# associated-value enums

next syntax now has nominal enums, typed payloads and exhaustive statement matches, this is a native development feature, not an updated downloadable distribution

```Awl
enum Outcome
    Value(value:i64);
    Empty();
end;
func main(): i64
    @p result: Outcome.Value(42);
    match result then
        case Outcome.Value(value) then
            print(value);
        case Outcome.Empty() then
            print("empty");
    end;
    return 0;
end;
```

declarations are file-private and top-level, constructors and patterns are type-qualified, zero-field alternatives still use `()`, colons touch field names, variant declarations and `end;` require semicolons

every variant must appear exactly once, missing/duplicate cases, wrong constructor or pattern arity, wrong payload types, incompatible match types and unreachable statements are rejected, there is no catch-all that silently hides added variants, `_` discards one payload binding

bindings belong to their own arm, an outer binding can be shadowed without being overwritten, nested enums are matched in nested statements, the scrutinee is evaluated once, a match whose arms all return satisfies definite return analysis

## types and limits

payloads may contain scalar types, immutable text or other nonrecursive enums, compatible integer literals can initialize f64 fields, typed integer variables aren't silently converted to f64

resource handles, owners, vectors, arrays, recursive layouts, generic enum parameters, field selection and enum equality are not supported, exported enum types now have a separately qualified compiler-source implementation, see [EXPORTED-ENUMS.md](EXPORTED-ENUMS.md), the published0.24 binaries still support private enums only, immutable text keeps its existing process-lifetime storage policy, enum support doesn't solve reclaimable strings

existing verifier limits remain active, at most128 variants and128 fields per variant, maximum64 layout depth and1MiB aggregate layout, these are implementation limits rather than a stable ABI promise

legacy `union` syntax is unchanged, native enum parsing lowers to the existing nominal tagged-union IR and C backend, reusing established layout, matching and definite-assignment machinery, the independent verifier separately checks payload restrictions, module-name provenance and private constructor/pattern access rather than trusting parser output

## runnable workload and evidence

`examples-next/enums` contains `kcalc.awproj`, run `awl build` there, then `./build/kcalc + 40 2`, operators are `+`, `-`, `*` and `/`, quote `'*'` in a shell

nested result enums distinguish invalid input/byte position, signed-i64 parse overflow, arithmetic overflow and division by zero, division truncates toward zero, exits0 success,2 arguments/operator,3 parsing and4 arithmetic error

54 feature/rejection/module cases,450 boundary/random calculator oracle cases in each native/sanitized mode,16 independent verifier cases and500 seeded source mutations pass, all11 compiler sanitizer phases and564 legacy tests in each of3 modes pass, exact hashes and broader regression results are bound by `tests/enum-checkpoint.json`

actual terminal capture is `demos/enums/native-enums.png`, warm local build/process measurements are in `benchmarks/enum-latest.json`, these aren't enum-only throughput or speedup claims

67 example sources are embedded in the offline editor, enum source is browsable but not executable by its browser subset, windows remains deferred, protected0.23 archives are unchanged, that historical enum milestone stayed20.0%=9/45, the later browser foundation review is in BROWSER-WASM.md

primary reference, [rust reference, enumerations](https://doc.rust-lang.org/reference/items/enumerations.html), used to check nominal associated-value semantics, not to copy rust's surface syntax
