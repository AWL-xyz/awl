# Next-syntax module scalar variables and exports

Experimental production source candidate, `--syntax aesop`, not a new accepted release.

```Awl
-- Template.aw
@p version: 128.59;
@p calls: 0;
exports{
    @r label: "Template";
    @w count: 1;
    @r func get_version(): f64
        @p func helper(): f64
            calls: calls + 1;
            return version;
        end;
        return helper();
    end;
};
```

```Awl
-- main.aw
use Template.aw as t;
func main(): i64
    print(t.label);
    t.count: t.count + 1;
    print(t.get_version());
    return 0;
end;
```

## Storage and visibility

A top-level `@p` binding is private module storage, not a function local. One storage instance exists per canonical imported file per program; importing the same file through two aliases does not duplicate state. State lasts for that program execution, not across process restarts or on disk.

- `@p version: ...;` outside a function is private; defining-file functions and their helpers can read or change it.
- **`@r` and `@w` are valid only within `exports{...}`.** They are not standalone declarations at file scope or inside functions.
- `@r` variables can be read by importers but assigned only from their defining module. Exported setter functions may deliberately change them.
- `@w` variables can also be assigned by importers through their alias.
- Exported funcs use `@r func`; `@rw func` is an error. Unexported funcs remain private.
- Local bindings shadow module variables. A helper that refers to an enclosing local still requires an explicit capture environment, which is not implemented. The compiler rejects this instead of accidentally substituting a same-named module variable. Pass a value explicitly as a parameter for now.
- Defining-file context is preserved across exported calls. An importer's own `version` does not replace Template's private `version`.

## Initialization, types and current limits

Current module storage supports **scalars only**: integers, bool, text/string and f64. Owned resources, arrays, aggregate storage and closure environments remain deferred.

Initialization runs once, dependencies before importers, declarations in source order within a module, before main. Import cycles are rejected. This first implementation permits scalar literals, earlier initialized module variables, pure arithmetic/conversions and the built-in math calls. Forward/self reads and arbitrary user/platform function calls in initializers are explicitly rejected. No silent zero-value read, literal substitution, fake function-local storage or hidden reinitialization per call is used.

Functions can read module variables declared later in the file because all initialization completes before main. Initializers themselves cannot do so. Runtime failures/abort do not imply exception unwinding or transactional initialization.

Source resolution and an independent verifier enforce ownership of module declarations, readonly/private access, reference symbols, initializer type/order/coverage, dependency ordering and safe initializer forms. C emission verifies again. These are language access rules, not filesystem sandboxing or authenticated source provenance.

Case-sensitive project-file imports, aliases, canonical deduplication and cycle detection remain active. **Installed Package lookup/install is deferred until after the command-line tool/ASDK.**

`examples/exports` is now executable by the experimental production path, not just the structural checker. New evidence is in `tests/module-numeric-*`; old reports and captures are historical. Native Windows-host/complete successor release acceptance is not implied by Linux development gates.
