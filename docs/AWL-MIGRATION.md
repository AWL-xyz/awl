# Awl migration and qualification

## public contract

- product name `Awl`, full toolkit name `Awl Software Development Kit [Beta]`
- canonical executable `awl`, linux ships all eight ASCII case spellings as relative links to the same native compiler executable
- `init`/`build` and help/version accept mixed case, no shell/Python wrapper or path-string command construction was added
- sources `.aw`, project manifests `.awproj`, imports, discovery, diagnostics, examples, editor, native and reference tooling use those extensions
- project names, namespace aliases and import path components retain their existing exact-case rules, source paths and names are not passed through the command-folding helper
- `-o` and `-O` still mean different things, source extensions and manifest syntax were not made case-insensitive

## implementation details that matter

source suffix validation no longer assumes a two-character extension, implicit import namespaces trim at the final extension separator rather than subtracting a fixed byte count

an extension rename must not rewrite AST field access, the browser runtime's internal `.k` field is still an AST discriminator, not a source-file extension, executable browser/import/function/worker/canvas tests catch that distinction

UTF-8 demos now use correct scalar/byte counts for the shorter product name, the string demo derives the rocket's index from the prefix's actual scalar length rather than a marketing-name byte constant, bounds checks were retained

command folding is intentionally limited to ASCII public verb selection, it never touches project paths, initializer names, source contents, identifiers, aliases or option values

[the Python pathlib reference](https://docs.python.org/3/library/pathlib.html) documents platform-specific path semantics and the distinction between pure computation and filesystem access, this migration keeps those concerns separate rather than lowercasing filesystem identifiers to make a command name convenient

## evidence and downloads

`tests/rename-checkpoint.json` is the current authority, `tests/checkpoint_awl.py` checks report/artifact/source bindings and the whole-home budget

`compiler/package_sdk.py` independently verifies the pinned upstream archives, every upstream resource file and link, the complete source/resource inventory, and each emitted archive member, bundles are complete distributions rather than overlays

the linux archive is exercised in a fresh unprivileged clean root with no Python, shell, host compiler or external network inside it, both successful execution and missing-resource/error/relocation behaviour are tested

the windows preview is freshly cross-built, its PE imports, source, complete upstream resources and archive integrity are checked, none of those checks is native windows-host acceptance, that work stays deferred until language completion

fresh browser workbench tests cover native/Node/Chromium parity, an independent JSON oracle, exact i64 enum arithmetic, host rejections, worker cancellation/deadline and opaque sandbox execution, the standalone editor remains an explicitly limited JavaScript subset

actual terminal/browser captures are opened for inspection, no generated images or drawn terminal stand-ins are used

## preserved history

`history/pre-rename-evidence.tar.xz` contains the original source, compiler, reports, photos and helper files as unchanged bytes with a per-file SHA-256/size index, historical names inside that immutable capsule are original provenance, not active branding

unmodified upstream resources, third-party legal authors and legitimate OS names are not product-name substitutions, old public downloads are retired only after their complete successors validate at their stated platform qualification level

## honest scope

this migration adds real command-case usability and publishes the current language/runtime in complete SDKs, it does not establish a new workload stage, the assessment remains **22.2%, 10/45**

public beta still exposes init/build only, no public run/install/Packages/registry commands were added, native Windows acceptance, arbitrary owned generics/borrowed views, exported/generic/resource enums, concurrency, broader networking/security, widgets/media/accessibility and substantial full-stack/real 3D workloads remain future work
