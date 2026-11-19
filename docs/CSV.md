# CSV Package

`csv` is a source Package for bounded UTF-8 comma-separated tables. It doesn't infer headers, column types, or fixed row widths. From a project directory, install it offline:

```sh
awl add /path/to/awl/packages/csv/csv.awpkg
```

## Read a table

`csv.parse(source, fields, rows)` takes valid `text` and two live, empty vectors: `vector<text>` for the fields and `vector<i64>` for exclusive row-end indexes. The first row starts at `0`; each subsequent row starts at the previous row's end. For `a,b\nc`, the fields are `a`, `b`, `c` and the row ends are `2`, `3`.

```text
use csv;

func main {
    @s fields vector<text>: vector.new<text>(0);
    @s rows vector<i64>: vector.new<i64>(0);
    @p report: csv.parse("item,quantity\r\n\"Owl, large\",+0007", fields, rows);
    if report.code != 0 { return 1; };
    @p first: vector.get(rows, 0);
    print(vector.get(fields, first));
    @p quantity: vector.get(fields, first + 1);
    if not string.i64valid(quantity) { return 2; };
    print(string.toi64(quantity));
    return 0;
};
```

The function returns `csv.Result`, with `code` and `offset` fields:

| code | meaning |
| ---: | :--- |
| `0` | Success. The offset is the scalar length of the source. |
| `1` | Invalid CSV syntax. The offset is the offending scalar, or the end of input for an unclosed quote. |
| `2` | More than 1 MiB of input, 8,192 fields, or 4,096 rows. |
| `3` | Invalid or nonempty output vectors, or a builder/vector storage failure. |

Offsets are zero-based Unicode scalar indexes, not bytes. `-1` means no particular input position applies. On a reported parse failure, initially empty outputs are empty again; if the vectors weren't empty to begin with, they're left untouched. Fields are immutable text snapshots. The runtime's process-wide text budget still applies across calls; clearing vectors does not reclaim snapshots and exhausting the text region can trap.

### CSV rules

- Outside quotes, commas separate fields and LF or CRLF ends a row. A bare CR outside quotes is invalid. A last record needs no final newline. Empty input has no records, an empty line has one empty field, and a final newline does not create a phantom row.
- An opening `"` must be the first character of a field. Inside quotes, `""` means a literal quote; commas and line breaks are preserved. After a closing quote, only a comma, a row ending, or EOF is valid.
- Spaces, tabs, embedded NULs and a UTF-8 BOM are literal data, not trimmed or stripped. A trailing comma adds a final empty field. Uneven rows are allowed. When reading bytes, validate UTF-8 before converting them to `text`.

## Write a table

`csv.encode(fields, rows, sink)` borrows those same vectors and a live `spool`. It appends canonical CSV: each field is double-quoted, internal quotes are doubled, and every row ends in LF. Row ends must be strictly increasing and cover exactly the field vector. Two empty vectors append nothing.

The encoder respects the row and field caps and appends at most 1 MiB per call, also bounded by the spool's remaining capacity. It returns `false` for invalid inputs, malformed row ends or insufficient space; on failure, the sink's earlier contents are preserved. It doesn't snapshot or print the result. Use `spool.snapshot` to obtain text if needed.

See the [order-summary demo](../examples/csv-demo/) for stdin input, quantity validation and a runnable `awl test` suite. This is an in-memory table API, not a streaming reader, spreadsheet importer, or schema validator.
