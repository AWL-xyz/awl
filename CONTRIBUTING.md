# contributing

thanks for helping improve Awl, this is an experimental compiler and language, small focused changes with reproducible checks are easiest to review

## setup

the contributor workflow currently requires Linux, Python 3, a C++20 compiler, a C compiler for generated programs and Node.js for the offline editor checks

```sh
python3 compiler/build_native.py --standalone --strip
python3 compiler/test_native.py
python3 tests/aesop.py --acc compiler/native/bin/acc
python3 tests/awl_editor.py --acc compiler/native/bin/acc --report /tmp/aesop-editor.json
```

## pull requests

- keep the sole native frontend in `compiler/native/` and preserve the current source syntax
- add a focused test in the matching current harness before changing checker, verifier or emitter behavior
- regenerate embedded C helpers with the matching `compiler/generate_*.py` script and run `--check`
- update `docs/API.md` when built-in signatures or surface names change
- describe the exact commands and reports used, do not describe planned features as shipped
- keep private planning notes, historical capsules and generated compiler binaries out of commits

## reports

source-bound reports belong in `tests/` with the current harness, historical reports belong in `tests/archive/`, never overwrite a historical report to claim new acceptance

open an issue before large grammar, ABI or SDK changes so the scope and acceptance criteria stay clear
