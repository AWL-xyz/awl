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

Alternatively, enter this example directory and run `awl test --cc "$(command -v cc)"`. Omit `--cc` with a complete, matching SDK. Change an expected value in `Totals.test.aw` to see the failure message and nonzero exit. The runner keeps no executable. See [test discovery and timeouts](../../docs/ASDK.md#testing-a-project).
