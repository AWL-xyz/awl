# Awl Software Development Kit [Beta]0.25.0-dev

Linux x86-64 complete successor SDK, native commands `check`, `emit-ast`, `emit-checked-ast`, `emit-c`, `build` and internal `run` now default to next syntax, public awl still exposes init/build only

`--syntax legacy` explicitly selects compatibility parsing, manifests can still declare `syntax: legacy`, no source sniffing or fallback to another grammar, the low-level legacy C ABI and Python reference parser retain their explicit legacy role

exported enums and nested cross-module typed results from the preceding source milestone are now included, configcheck is a useful shipped multi-file JSON settings validator, Awl Board source/assets and third-party notices are included, the shared WASI host and original owl branding are retained

62 default/override/error/preservation/casing/workload checks,187 exported enum/configuration native/sanitizer checks and107 native/107 WASI exported-result oracles bind this compiler, exact complete-archive offline qualification is external to avoid a circular archive hash

historical rename-* reports shipped under validation bind the previous0.24 compiler, not this one, the new manifest marks next as the default, production compiler source and unchanged upstream backend resources are inventoried

Windows0.24 remains an older, unaccepted native-host preview, no claim it contains the0.25 compiler changes, no native Windows qualification, arbitrary generics, concurrency, TLS/auth or general DOM target is added

practical capability stays24.4%=11/45, changing a default and shipping a previously qualified language feature don't earn another workload stage
