# CSV order summary

This example reads a UTF-8 CSV table from stdin. It expects an `item,quantity` header and exactly two fields per order. `csv.parse` handles quoted commas, doubled quotes and multiline item names; the application checks quantities with `string.i64valid` and `string.toi64` and totals them. Quantities must be between 0 and 1,000,000,000, and input is limited to 1 MiB.

From the repository root, with the [source-built toolkit](../../README.md#quick-start-from-source) on Linux x86-64:

```sh
(cd examples && awl run csv-demo --cc "$(command -v cc)" < csv-demo/orders.csv)
(cd examples && awl test csv-demo --cc "$(command -v cc)")
```

```text
Orders: 3
Total quantity: 15
```

Use `awl test csv-demo --list` or `awl test csv-demo --check` from `examples/` if you don't have a C backend. The example has a vendored copy of the Package. To use the same code in your own project, run `awl add /path/to/awl/packages/csv/csv.awpkg` from its project directory, then `use csv;` in your source.

See the [CSV API](../../docs/CSV.md) for limits, error positions, row indexes and `csv.encode`.
