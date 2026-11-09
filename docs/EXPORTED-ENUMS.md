# exported enums and reusable typed results

## delivery status

implemented and qualified in the **Linux0.25 SDK**, including no-flag Aesop-syntax compiler commands, the earlier0.24 binaries and Windows preview don't contain exported-enum support, Windows native-host qualification remains deferred

private enums keep their existing behavior, an exported enum is explicitly declared inside `exports{...}`

```Awl
exports{
    @r enum Outcome
        Value(value:i64);
        Missing();
    end;
    @r func find(): Outcome
        return Outcome.Value(42);
    end;
};
```

an importing file uses the same module alias for the type, constructors and exhaustive patterns

```Awl
use Lookup.aw as lookup;
func main(): i64
    @p outcome: lookup.find();
    match outcome then
        case lookup.Outcome.Value(value) then print(value);
        case lookup.Outcome.Missing() then print("missing");
    end;
    return 0;
end;
```

function parameters/returns can name `lookup.Outcome`, canonical aliases retain one nominal type identity, identically shaped enums from different defining modules remain different types

## semantics and trade-offs

- only `@r enum` inside exports, `@rw enum` and standalone access modifiers are rejected
- exporting an enum exposes all of its variants for construction and exhaustive matching, not mutation of its declaration, values retain ordinary local assignment rules
- default-private enums remain private, exported functions retain their defining-file context
- scalar, immutable text and nonrecursive enum payloads can cross module boundaries, nested payload types from other exported modules resolve through their actual import aliases
- private enum values can already cross a public function boundary as opaque inferred values, this doesn't grant outside constructor/pattern access, no new private-type naming permission is introduced
- missing/duplicate arms, incompatible nominal types, wrong payload types/arity, invalid access modes, recursive layouts and resource payloads are rejected
- this isn't arbitrary generics, resource-bearing enum ownership, per-variant visibility, re-exports, an ABI guarantee or separate object linking

implementation reuses the existing tagged-union IR and C emitter, the parser attaches the readonly export mode to the enum declaration, project resolution recognizes that permission, the independent read-only verifier separately checks the permitted annotation and cross-module variant access, no new unchecked casts or runtime tag representation are added

text retains process-lifetime storage, scalar/text/nonrecursive enum payloads avoid introducing new ownership holes, existing128-variant/128-field/64-depth/1MiB aggregate-layout bounds remain

## useful multi-file workload

`examples/exported-enums/configcheck.awproj` is a native JSON settings validator, `File.aw` returns nested exported read/error enums, `Config.aw` returns typed settings, JSON/schema/resource failures or the original typed file issue, `main.aw` handles every public variant from both defining modules

it accepts exactly `host`, `port` and `debug`, host is nonempty and control/space-free with at most253 UTF-8 bytes, this is a display/configuration field rather than a DNS validator, port is an integer from1 through65535, debug is a JSON boolean

input files are bounded to16384 bytes, JSON retains its512-token/16-level/4096-byte decoded-string limits, no environment mutation, network connection, dotenv Package or secret management is claimed

success prints host/port/debug on separate lines, exit0, missing/I/O/oversize errors exit3, malformed JSON exit4 with byte offset, schema errors exit5 with field name, resource failures exit9, arguments exit2

## contributor build

use a complete extracted SDK as the staging directory, not the protected published archives, compile the new frontend from this checkout into that staging directory

```sh
c++ -std=c++20 -O2 -Wall -Wextra -Werror -s -static \
  compiler/native/klex.cpp compiler/native/kparse.cpp \
  compiler/native/kcc.cpp compiler/native/kbuild.cpp \
  -o /path/to/staged-Awl/bin/kcc
/path/to/staged-Awl/bin/awl build examples/exported-enums/main.aw -o /var/tmp/configcheck
python3 tests/exported_enums.py --sdk /path/to/staged-Awl --report /var/tmp/exported-enums.json
```

this is contributor tooling, it intentionally requires a host C++ compiler, it doesn't change the no-host-compiler requirement for published end-user SDKs, those archives are unchanged

## acceptance and assessment

see `tests/exported-enums*.json*` and the source checkpoint,187 new module/configuration checks,54 private-enum feature/rejection cases plus450 calculator oracles each native/sanitized,7 targeted exported-enum independent verifier checks,11 broader compiler sanitizer phases, application compatibility and legacy reports carry their actual compiler hashes

the board's emitted C is byte-identical between the accepted0.24 compiler and this candidate, existing board application/archive evidence isn't relabelled as evidence for the new frontend

capability remains **24.4%=11/45**, a useful configuration validator strengthens existing CLI stage2 and typed results unlock reusable language code, neither establishes another cumulative workload stage, native Windows, broader containers/lifetimes, concurrency and general DOM integration remain open

primary reference reviewed before implementation, <https://doc.rust-lang.org/reference/items/enumerations.html>, nominal associated-value types and constructor namespaces informed the design, Awl keeps its own exports/semicolon syntax

final additional gates,107 independent configuration cases each native/WASI using the same cross-module exported-result source,564 legacy tests in each of reference/native-parser/native-frontend modes with zero skips,10 focused application regression groups passed, including62 SDK cases, the compatibility setup required restoring snapshot-lost executable bits and supplying optional Xvfb/python-xlib fixtures, no language safety rule was relaxed

reproduction helpers are `tests/exported_enums.py`, `exported_enums_wasm.py`, `exported_enums_native.py`, `exported_enums_legacy.py` and `exported_enums_regressions.py`, the legacy bridge accepts `Awl_LEXER_LIBRARY` pointing to a freshly built candidate shared frontend, the independent exported verifier is `compiler/native/kexport_test.cpp`, compile it with `klex.cpp` and ASan/UBSan
