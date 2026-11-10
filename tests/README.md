# current test gates

these are the source-current gates used by CI, all commands assume the repository root and a Linux contributor host

```sh
python3 compiler/build_native.py --standalone --strip
python3 compiler/generate_runtime.py --check
python3 compiler/generate_platform.py --check
python3 tests/aesop.py --acc compiler/native/bin/acc --report tests/aesop-checks.json
python3 tests/aesop.py --sanitize-programs --report tests/aesop-program-sanitizers.json
python3 tests/aesop_time.py --acc compiler/native/bin/acc --sanitize --report tests/aesop-time.json
python3 tests/awl_editor.py --acc compiler/native/bin/acc --report tests/aesop-editor.json
python3 compiler/test_native.py --sanitize --report tests/aesop-native.json.gz
```

- `aesop.py` checks declarations, generated native execution, CLI starters, ABI v2, conversion/type tests and rejection cases
- `aesop_time.py` checks the local time Package, generated C, wall-clock agreement, deadlines, bounded sleeps and shipped demo
- `awl_editor.py` checks the offline editor interpreter and checks every bundled example with `acc`
- `test_native.py` runs the native lexer, frontend, independent verifier, ownership, vector, enum, process and inference phases with ASan/UBSan
- `aesop-migration.json` records byte-identical emitted C for the preserved entry programs and Linux host-C links, it is not an execution claim for every application
- `sdk-source-current.json` records a locally built complete Linux SDK archive with inherited checksum-pinned resources, the archive itself is kept outside the repository and is not a published release

[`archive/`](archive/) keeps superseded harnesses and reports, those bind older compiler hashes and retired grammars, they are not current gates

current source evidence is written beside this file as `aesop-checks.json`, `aesop-program-sanitizers.json`, `aesop-time.json`, `aesop-editor.json`, `aesop-native.json.gz` and `aesop-migration.json`
