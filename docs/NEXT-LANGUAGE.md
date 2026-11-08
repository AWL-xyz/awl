# next syntax, clean-syntax revision

this revision defines the current `next` surface syntax in compiler source and the `0.26.0-dev` Linux SDK, explicit legacy compatibility keeps its separate grammar

```text
exports{
    @r func size :: @b values[i64], etc[i64]: i64 {
        return vector.length(values) + vector.length(etc);
    };
    @w total: 0;
};
func main: i64 {
    @p name: "owl";
    @s values vector<i64>: vector.new<i64>(0);
    @s etc vector<i64>: vector.new<i64>(0);
    @p remaining: 3;
    while remaining > 0 {
        vector.push(values, remaining);
        remaining: remaining - 1;
    };
    if name != "owl" {
        print("different name");
    } elseif remaining == 0 {
        print("hello ${name}, "..size(values, etc).." values");
    } else {
        print("still working");
    };
    return 0;
};
```

## blocks and declarations

- exports use `exports{ ... };`, members require `@r` readonly or `@w` writable, funcs/enums require `@r`, private defining-file context is preserved, these are access permissions rather than purity annotations
- functions use `func name :: param1, param2: ReturnType { ... };` when they take parameters, and `func name: ReturnType { ... };` when parameterless, omitted return annotations (`func name :: param { ... };` or `func name { ... };`) mean `unit`, owned results use `: @o ReturnType`, parenthesized parameter lists `func name(...)` and `end;` function endings are rejected in `next` syntax
- if uses `if condition { ... } elseif other { ... } else { ... };`, zero or more elseif branches, optional else, exactly one semicolon after the whole chain
- while uses `while condition { ... };`, parentheses around conditions are optional ordinary expression grouping
- enums and matches retain their `end;` grammar, match cases still use `then`
- commands require semicolons, declarations/assignment retain adjacent colon rules, `@p count: 3;` initializes, `count: count - 1;` assigns

## names and modifiers

names match `[A-Za-z_][A-Za-z0-9_]*`, no spaces, leading digits, hyphens, Unicode letters or punctuation inside a name, reserved keywords can't be names, subtraction remains unambiguous, `a-b` means `a - b`

| form | meaning |
|---|---|
|`@p name: value;`|private ordinary binding, inferred type|
|`@s name type: initializer;`|scoped resource owner|
|`@b name:type`|borrowed function argument|
|`@o name:type`|owned function argument, explicit move at call sites|
|`: @o type`|owned function result|
|`@r` inside exports|readonly exported member|
|`@w` inside exports|writable exported variable|

readonly/readwrite would both start with r, so writable uses w, source `@rw`, `@p scoped`, `borrow` and ownership-modifier `own` are replaced, `move` expressions and `defer` commands aren't variable modifiers and keep their names

## function argument types

```text
func size :: @b values[i64], etc[i64]: i64 {
    return vector.length(values);
};
func render :: lines:view<text>, first:i64 {
    print("first ${first}");
};
```

`::` introduces a comma-separated parameter list without parentheses, and is omitted when a function takes no parameters, `name[T]` is a dynamic vector argument, not a fixed array, `@b result[i64]` replaces `borrow result:vector<i64>`, vector args with the old colon/generic spelling are rejected, scalar/resource/view args retain explicit colon types, fixed arrays retain `name:[T;N]`, locals/results still use explicit `vector<T>` types

borrow/own checking and runtime view lifetime rules are unchanged, shortening a modifier doesn't weaken ownership or permit resource payloads

## strings

`"hello ${name}"` inserts a scalar variable/module binding, name placeholders only for this first implementation, arbitrary expressions, calls, whitespace or dotted paths inside placeholders are rejected, use `..` with an ordinary expression for those cases

`"count "..count.."!"` converts scalar values and concatenates, `..` has the same precedence as `+` and is left-associative, parenthesize arithmetic, `"sum "..(a+b)`, `1..2` is concatenation, `1.2` remains f64

text is unchanged, bool is true/false, integer formatting is exact decimal including full u64/i64 ranges, f64 uses the existing17-significant-digit display convention, vectors/views/resources/arrays/enums aren't implicitly formatted

`"literal \${name}"` produces literal `${name}`, existing escapes/UTF-8/embedded NUL remain supported, interpolation and concatenation evaluate left-to-right through checked IR, allocations retain the bounded immutable string-region limits, no reclaimable string ownership is claimed

## structs

`struct Name { field:type; other:i64; };` declares a value type, top level and unmarked is private to its file, `@r struct` inside `exports{ ... };` exports it so an importer can name the type, construct it and pass it around

fields are `name:type;` one per semicolon, types are scalars, text, a nested struct or an enum, a struct may not contain itself, owned resources and arrays are rejected as fields so no field needs a destructor

`Row(1,"first")` constructs positionally in declaration order, exactly like an enum variant, `row.weight` reads a field and `row.weight: 4;` assigns through the same adjacent-colon rule as a local, `nested.inner.value` and `rows[0].name` both work, mutation of one variable never touches a copy, construction and assignment copy by value

`print` and `..` still only accept scalars, comparing two structs with `==` isn't available yet, structs are not allowed as vector elements, map values or module variables, and there is no method block, the field list is the whole type

## mutable borrows

`func grow :: @m row:Row, by:i64 { row.weight: row.weight + by; };` takes the caller's struct in place, the parameter is an alias rather than a copy, so field writes inside the callee are visible at the call site when it returns

the rule is deliberately narrow, `@m` parameters must be a struct type, the argument must be an existing local, field or element and never a temporary such as `Row(1,2)`, and one local cannot be borrowed twice inside a single call, `@m` on `i64`, on `text` or on a container is rejected with `E229`

ordinary parameters stay by value, an `@m` parameter and a by-value copy of the same struct can both be live in one function, and there is still no borrow checker, no aliasing proof and no lifetime inference, the compiler checks the shape of the call and nothing more

`return;` with no value is valid in a `unit` function, it runs the scope cleanup before leaving

## diagnostics

errors name the source file, line and column of the offending token, and the message prefers the declared name over the internal lowered symbol, so an importer sees `Shape.aw:Box` rather than a module-mangled identifier

typo recovery is built in, an unknown field, function, local, module variable or enum variant within edit distance two of a real declaration gets `, did you mean 'count'?` appended, `E229` covers mutable-borrow misuse, `E220` to `E225` cover ownership and loop-state violations

## loops

`for i in 0..n { ... };` walks `i` from `0` up to but not including `n`, both bounds are `i64` expressions and `i` is a fresh `i64` binding per iteration

`for value in collection { ... };` iterates a `vector<T>`, a `view<T>`, an `int_vector`, a fixed array `[T;n]`, a `map<K,V>` (yielding keys) or a `set<T>` (yielding elements), the element is a copy of the slot, containers are borrowed rather than moved

`break;` and `continue;` work in `for` and `while` loops, both run the cleanup of every scope they leave, so `@s` owners created inside the skipped body are still released in order, `break` and `continue` outside a loop are rejected

loop bodies must restore the entry ownership state of any `@s` owner they touch, exactly like `while`, and a loop binding can't reuse a name already declared in the same block

## maps and sets

`map<K,V>` takes an integer, bool or text key and a scalar or text value, `set<T>` takes the same key element set, both are 8-byte handles to bounded runtime storage owned by an `@s` binding and released at scope exit

`map.new<text,i64>(4)` and `set.new<text>(4)` take an initial capacity, the api is `map.valid`, `map.length`, `map.set`, `map.get`, `map.has`, `map.remove`, `map.clear`, `map_keys`, `map.values` and the set side is `set_valid`, `set.length`, `set.add`, `set.has`, `set.remove`, `set_clear`, `set.values`, every call except `map.new`/`set.new` takes the container first

keys and text values are copied into the container, a text value read back is a fresh immutable copy, `map.get` on a missing key traps like `vector.get`, `map.remove` returns whether the key was present, `set.add` returns whether the element was new

iteration order is hash order and never insertion order, `map_keys`/`map.values`/`set.values` return a new `vector<T>` the caller owns, growth rehashes, removal leaves a tombstone that later inserts reuse

## migration and evidence

`compiler/migrate_next.py FILE.aw ...` is a one-way contributor tool for valid previous next source, not a compatibility parser mode, back up source first, it escapes literal embedded `${...}` so browser template strings don't change meaning

47 current source files migrated,21 executable entries emitted byte-identical C across the function declaration syntax migration, modules retain permission/ownership behavior, see tests/return-migration.json.gz

structs, loops and hash containers are language surface, they don't move the workload rubric on their own, score remains26.7%=12/45, native Windows acceptance remains deferred until language completion

`tests/next_features.py --sdk DIR --report FILE` builds and runs `examples-next/structs`, `examples-next/loops` and `examples-next/containers` with the bundled SDK and compares exact stdout, `tests/next_examples.py` structurally checks all38 example sources


## struct equality, text iteration, string search, resource structs

struct `==`/`!=` is field-wise for structs made only of scalar/text/f64/nested comparable structs, enum and container fields are still E200

`for ch in text` yields each codepoint as `u32` in linear time, `string_find(s,needle)` returns a scalar index or -1, `string_contains`, `string_starts_with`, `string_ends_with` return bool, `string_replace(s,from,to)` replaces every non-overlapping match and traps on an empty `from`

`"${a.b.c}"` accepts dotted field paths of plain identifiers, calls and other expressions are still rejected

a struct with a `map`/`set`/`vector`/`spool` field, or a field that is itself such a struct, is a resource struct, it is an `@s`-only owner built with `Bag(move c, ...)` (owner fields need explicit `move`), borrowed with `@m` or by field (`map.set(bag.counts,k,v)`), returned with `@o`, and freed field by field at scope exit, copies, by-value parameters, owner-field assignment, enum payloads and arrays of resource structs are rejected, vectors of containers are not implemented, `examples-next/resource-structs` is the example
