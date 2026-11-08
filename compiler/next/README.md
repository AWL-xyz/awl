# Experimental next-syntax checker

**Development prototype, NOT KCC0.24 or an executable Awl implementation.**
Released0.23 syntax/compiler/bundles remain unchanged. Latest design supersedes
previous global/local suggestions: [NEXT-LANGUAGE.md](../../docs/NEXT-LANGUAGE.md).

Build with a contributor C++20 compiler (not an installed Awl dependency):

```
c++ -std=c++20 -O2 -Wall -Wextra -Werror compiler/next/syntax.cpp -o compiler/next/bin/Awl-next-syntax
compiler/next/bin/Awl-next-syntax examples-next/tour/main.aw
python3 tests/next_examples.py --binary compiler/next/bin/Awl-next-syntax --report tests/next-examples.json
```

The retained binary is a Linux development utility linked against the host C++
runtime, NOT a new standalone end-user toolchain bundle. Windows-host prototype
validation is pending. Production0.23 remains the independently validated bundle.
Python runs contributor tests/screenshots only; the checker itself is C++.

Implemented: bounded strict-UTF8 scanning, expression STRUCTURE, required `;`,
`end;`/`);`, @p/colon binding and restricted assignment forms, exports @r/@rw,
function-local lexical scopes, original-module resolution, namespaced use/as,
exact-case filesystem traversal, graph deduplication/cycle chains and relevant
access/duplicate/missing-name diagnostics. `use` targets load from disk on
demand, one bounded cycle-guarded pass, so a single file argument checks the
whole import graph. Installed-Package test staging accepts
`--packages DIR` with `DIR/PackageName/main.aw`; no registry/ASDK is implemented.

Not implemented: typing/call-signature checks, initializer execution/order,
code generation, closures/helper activation, production AST/verifier integration,
general paths/slices/math/graphics/strings/concurrency or all legacy constructs,
and it checks structure only, never types, ownership or runtime behaviour. It does
accept the current surface, structs, `for`/`break`/`continue`, `map<K,V>`, `set<T>`
and `map_new`/`set_new`. Read the full limits in NEXT-LANGUAGE.md before using the checker.

Evidence:34 real example sources via tests/next_examples.py plus the built-in
13 negative checks, and the older 200 seeded structural mutations, normal and
ASan/UBSan. tests/next_syntax.py still holds the pre-revision fixtures and is
stale until migrated. The structural graph benchmark is ONLY this checker, not full native
compilation. Actual terminal capture/provenance: demos/next-syntax/.

Next: production strict dialect/AST migration, module storage/export permissions,
lexical nested-function lowering and independent verification; execute cross-file
private helpers before claiming the requested semantics. Preserve old release
archives until a corresponding complete successor passes exact gates.
