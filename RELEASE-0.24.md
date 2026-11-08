# Awl 0.24.0-dev

Awl Software Development Kit [Beta], canonical command `awl`, sources `.aw`, project manifests `.awproj`

all eight ASCII command-name casings and mixed-case init/build/help/version work, project names/import paths keep exact case, no option-value or source-identifier folding

## delivered artifacts

- complete Linux x86-64 SDK,57,444,588bytes, exact archive SHA-256 `b8d14d845a1b3c730fac028f775c0c8e276a5e49c8d4b76b56623db1b0f1a1df`
- complete Windows x86-64 preview,57,905,784bytes, exact archive SHA-256 `50d6a7a914b2c75639c95be645cfb36555996e906dee718178b8bf72ccc565ec`
- adjacent SHA-256 sidecars, full compiler/backend/libc/linker/headers/startup/legal resources, native source, examples, docs, offline browser files and validation snapshots

no end-user Python, host compiler, SDK or separate backend download is required, native Windows-host execution is still unaccepted and deferred, cross-build/resource/PE checks are not substituted for that acceptance

## qualification

Linux exact archive passed107commands in an unprivileged clean root with no Python/shell/host compiler or external network, includes all eight public command casings, init/build, implicit .aw imports, program execution,348integer checks, error preservation, traps, missing-resource failure and whole-prefix relocation

both platform resource trees match all18105files/links of independently downloaded checksum-pinned upstream distributions, every archived file is checked against the complete inventory, Windows PE imports are limited to OS/UCRT libraries

fresh native compiler SHA-256 `21856c691451f9c6b1483b4940878dc5f5c0993d7e7c9dbd740be8fb449742f1`

fresh gates include564legacy tests in each of3modes with zero skips,11native ASan/UBSan phases,12runtime regression groups,62SDK cases,45command/project cases,35vector operation/identity cases,12WASI vector/runtime cases including440078assertions,437native/437Node/437Chromium JSON cases,444enum/i64 oracle cases,8host rejections, cancellation/timeout/opaque-sandbox checks and9offline editor checks across69embedded sources

actual terminal/editor/workbench screenshots were opened, source/report/image hashes are bound in `tests/rename-checkpoint.json`, the whole-home audit is separate in `tests/rename-home-audit.json`

superseded public downloads were retired only after these exact successors qualified, original source/compiler/reports/photos/helpers remain unchanged in the indexed historical capsule

## honest scope

score remains22.2%,10/45, the rename, command-case support and fresh bundles don't earn a new workload stage, no new performance ranking is claimed

public beta remains init/build only, general browser editor remains a limited JavaScript subset, the JSON workbench has its own freshly compiled WASM/worker proof, native Windows qualification and broader language/runtime/application work remain incomplete
