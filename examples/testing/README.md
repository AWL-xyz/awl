# Test an Awl project

`main.aw` and `Totals.test.aw` both import `Pricing.aw`. The test checks the same code the executable uses, without running the application's `main`.

From the repository root, with a [source-built toolkit](../../README.md#quick-start-from-source) on Linux x86-64:

```sh
(cd examples && awl test testing --cc "$(command -v cc)")
```

```text
Testing Totals.test.aw
PASS Totals.test.aw
Test result: 1 passed, 0 failed
```

Alternatively, enter this example directory and run `awl test --cc "$(command -v cc)"`. Omit `--cc` with a complete, matching SDK. Change an expected value in `Totals.test.aw` to see the failure message and nonzero exit. The runner keeps no executable.

Try `awl test --list` to see the suite or `awl test --filter Totals --check` to check just the matching source without a backend. For a new project of your own, `awl new Demo` includes a ready-to-run smoke test. See [test discovery and options](../../docs/ASDK.md#testing-a-project).
