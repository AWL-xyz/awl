# Sort lines from stdin

`ksort` is a bounded UTF-8 line sorter written in Awl. Run it from the repository root with a [source-built toolkit](../../../README.md#quick-start-from-source) on Linux x86-64:

```sh
printf 'owl\nant\nowl\n' | awl run examples/apps/sort/main.aw --cc "$(command -v cc)" -- --unique
```

```text
ant
owl
```

Omit `--unique` to keep duplicates. Omit `--cc` if using a complete, matching SDK. To keep an executable instead of rebuilding on each run, enter this example directory and run `awl build --cc "$(command -v cc)"`; the executable is `build/sort`.

- Input is at most 1 MiB and 32,768 lines. Invalid UTF-8 or input over either limit is rejected before any sorted output is written.
- LF separates lines; an unterminated last line is accepted and output lines end with LF. Other bytes, including CR and embedded NUL, are preserved.
- Sorting is stable and lexicographic by UTF-8 bytes, not locale-aware. `--unique` collapses byte-identical rows only.

The example shows checked byte search, a typed vector of text, a local module with an exported stable merge sort, and buffered output that handles short writes. See the [before/after benchmark](../../../docs/PERFORMANCE.md#current-source-sorting-utf-8-lines).
