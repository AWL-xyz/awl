# Experimental next-syntax f64 and math

Source candidate only, opt-in `--syntax next`; not contained in protected 0.23 downloads.

```Awl
func scale(value:f64): f64
    return value * 2;
end;
func main(): i64
    @p version: 128.59;
    print(version);
    print(scale(128.59));
    print(sin(pi / 2));
    print(cos(0));
    print(sqrt(81));
    print(atan2(1, 1));
    print(tau);
    return 0;
end;
```

- `128.59` is a numeric **f64** literal. `"128.59"` is text. No quotes are needed for numeric input arguments, bindings, assignments or expressions.
- Current decimal grammar requires digits on both sides of an adjacent dot: `0.5`, not `.5`, `1.` or `128 . 59`. Scientific notation and `f64` literal suffixes are not part of this first slice. Decimal payloads are bounded to 257 characters and must parse to a finite value. `1.0.0` is not a number: use text for semantic versions.
- f64 is binary floating point, **not exact decimal/fixed-point money**. Some decimals are approximated. Printing uses up to 17 significant digits; do not use printed trailing digits as a guarantee of exact decimal arithmetic.
- Arithmetic `+ - * /`, unary minus, comparisons and equality work for matching f64 operands. Float remainder `%` is rejected. Math follows the target C double/libm behavior: domain results such as `sqrt(-1)` may be NaN; floating arithmetic can produce infinity. No universal bit-identical transcendental accuracy across platform libraries is promised.
- `sin(x)`, `cos(x)`, `sqrt(x)` return f64; `atan2(y, x)` takes the **y** coordinate first. Angles and `pi`/`tau` use radians. Constants and built-in math names are not installed Packages.
- Plain integer literals acquire f64 context when used as an f64 binding/assignment/return, f64 function argument, math argument, or alongside an f64 arithmetic operand. Thus `sqrt(81)` and `scale(2)` work directly. Explicitly typed integer literals/variables do not silently widen: use `f64(value)` when needed. Unchecked float-to-integer casts are not implemented.
- Arbitrary incompatible literals are not accepted just because a variable is accepted: e.g. `sin("1")` and assigning `128.59` to an i64 binding remain errors.

The native checker and separate read-only verifier both enforce types and allowed math signatures. Numeric literal payloads are validated before C emission, not pasted as unchecked C. Existing integer overflow/bounds checks remain separate and unchanged in the legacy dialect.

Examples: `examples-next/numeric/main.aw`, `examples-next/modules/`. Current evidence lives in `tests/module-numeric-*`; earlier func/next reports predate these features. Native Windows-host and complete successor artifact acceptance remain separate gates.
