# Aesop syntax

Aesop is the only supported surface syntax, the native frontend lives in `compiler/native/`, the previous `next` name and legacy compatibility modes are retired

this is the source syntax reference, older SDK archives do not implement this revision

## function declarations

```text
func size :: @b values[i64], etc[i64] {
    return vector_length(values) + vector_length(etc);
};

func main[i64] {
    print("hello from Awl");
    return 0;
};
```

```text
func NAME[RESULT] :: PARAMETERS { BODY };
func NAME[RESULT] { BODY };
func NAME :: PARAMETERS { BODY };
func NAME { BODY };
```

- optional `[RESULT]` follows the function name, before `::`, omitted results are inferred from the body
- `::` introduces at least one parameter, omit it for parameterless functions
- parameters are comma-separated and do not use surrounding parentheses
- function bodies use braces and terminate with `};`, statements inside require semicolons
- calls retain parentheses, for example `size(values, etc)`
- a non-unit function must return the declared type on every reachable exit path
- the executable entry point takes no parameters and returns `i64`, explicitly as `func main[i64] { ... };` or by inference as `func main { return 0; };`

### return-type inference

```text
func size :: @b values[i64], etc[i64] {
    return vector_length(values) + vector_length(etc);
};
```

both length calls return `i64`, so the body above infers `i64`, the parameter types alone do not choose the result type

- all value-returning branches must agree on one type, no silent widening between different return types
- bare `return;` contributes `unit`, mixing bare and non-unit returns is an error
- no value-returning statements infers `unit`, including mutually recursive unit-only functions
- a non-unit result still requires every reachable exit path to return a value
- forward calls, nested helpers and exported/imported functions participate in inference
- unresolved cycles require an explicit `[type]` on enough functions to break the type dependency, annotated recursion remains supported
- resource results require explicit `[type]` or `[@o type]`, the compiler does not guess ownership transfer
- an explicit result is checked against the body, it is not merely a suggestion

explicit annotations remain useful for public interfaces and for intentional numeric context such as `[f64]`, inference does not turn two different branch types into a new common type

### result types

```text
func greeting[text] { return "hello"; };
func ready[bool] { return true; };
func ratio[f64] { return 1.5; };
func pair[[i64;2]] { return [3,4]; };
func reset[unit] { return; };
func notify { print("done"); };

func make[@o vector<i64>] {
    @s values vector<i64>: vector.new<i64>(0);
    return move values;
};
```

an owned result puts `@o` inside the result brackets, ownership transfer and supported resource/type restrictions are unchanged, brackets do not add generic type parameters or relax lifetime checks

qualified named results such as `[Library.Result]` use ordinary imported-type resolution, array results retain nested type brackets such as `[[i64;2]]`

### parameters

| declaration | meaning |
| :--- | :--- |
| `count:i64` | a scalar parameter |
| `values[i64]` | a dynamic-vector parameter, not a fixed array |
| `@b values[i64]` | an explicitly borrowed dynamic vector |
| `@o values[i64]` | an owned vector argument, transferred by `move` at the call site |
| `lines:view<text>` | a checked runtime view |
| `items:[i64;2]` | a fixed array |
| `@m item:Record` | a mutable struct parameter where supported |

vector parameters use `name[T]`, the former `name:vector<T>` parameter spelling is rejected, local variables and function results still use `vector<T>`

an unmarked resource parameter is not implicitly borrowed, a scoped owner cannot be passed through it as though it were `@b`, the `etc[i64]` parameter in the opening example therefore requires an argument allowed by those existing ownership rules

### rejected forms

```text
func main: i64 { return 0; };
func size :: values[i64]: i64 { return 0; };
func size(values:i64) -> i64 { return values; };
function main()->i64 return 0 end
```

there is no fallback grammar, the optional explicit selector is `--syntax aesop`, `next` and `legacy` selectors and manifest values are rejected

## bindings and control flow

```text
func main[i64] {
    @p name: "owl";
    @p remaining: 3;
    while remaining > 0 {
        remaining: remaining - 1;
    };
    if name != "owl" {
        print("different name");
    } elseif remaining == 0 {
        print("hello ${name}");
    } else {
        print("still working");
    };
    return 0;
};
```

`@p count: 3;` declares a private binding, `count: count - 1;` assigns it, the colon must be adjacent to the preceding name/type token, `=` is not an assignment operator

if/elseif/else chains, while loops and for loops use braces, commands and complete control-flow statements require a trailing semicolon, enum declarations and match expressions retain their documented `end;` grammar, match arms use `case ... then`

## names and modifiers

identifiers match `[A-Za-z_][A-Za-z0-9_]*`, reserved keywords cannot be names, subtraction is unambiguous because hyphens are not identifier characters

| form | meaning |
| :--- | :--- |
| `@p name: value;` | ordinary private binding |
| `@s name type: initializer;` | scoped resource owner |
| `@b` | borrowed argument |
| `@o` | owned argument or owned function result |
| `@m` | mutable struct argument where supported |
| `@r` inside `exports{...}` | readonly exported member |
| `@w` inside `exports{...}` | writable exported variable |

`move` expressions and `defer` commands keep their names, readonly exports are access permissions, not purity annotations

## modules and Packages

```text
use Library.aw as lib;

exports{
    @r func answer[i64] { return lib.answer(); };
    @w count: 0;
};

func main[i64] {
    print(answer());
    return 0;
};
```

functions are private unless explicitly exported, defining-module private context survives exported calls, canonical imports share a module instance, paths and aliases are case-sensitive

`use NAME;` loads a local Package through `packages/NAME/NAME.awpkg`, it does not download from a server, see [Packages](PACKAGES.md)

## text and builtins

`"hello ${name}"` interpolates a scalar identifier, arbitrary expressions or dotted paths do not belong inside these placeholders, use concatenation for expressions such as `"sum "..(a+b)`, `\${name}` produces literal placeholder text

`..` is left-associative with the same precedence as `+`, `1..2` is concatenation, `1.2` is an f64 literal, resource/vector/aggregate values are not implicitly formatted

category calls such as `vector.length(values)`, `spool.new(16)` and `map.get(table,key)` are the normal builtin spelling, `vector_length(values)` is also accepted as the explicit vector-length alias used in the requested declaration example, this does not restore the old grammar or all underscore builtin aliases

runtime ownership, bounds, overflow, resource and view-staleness checks are unchanged by the declaration migration
