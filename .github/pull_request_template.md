## summary

<!-- what changed and why -->

## validation

<!-- exact commands, reports and hashes, include generated-program and sanitizer results when behavior changed -->

```sh
python3 compiler/build_native.py --standalone --strip
python3 compiler/test_native.py --sanitize
python3 tests/aesop.py --acc compiler/native/bin/acc
python3 tests/awl_editor.py --acc compiler/native/bin/acc --report /tmp/aesop-editor.json
```

## checklist

- [ ] current source syntax and `compiler/native/` frontend preserved
- [ ] focused test added or updated
- [ ] embedded C helpers regenerated and checked when runtime text changed
- [ ] docs/API.md updated when signatures or surface names changed
- [ ] no private notes, historical capsules, credentials or generated compiler binaries committed
- [ ] limitations and platform qualifications stated plainly
