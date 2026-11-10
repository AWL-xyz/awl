# bounded structured JSON and native jget

new reusable `examples/parsing/Json.aw` implements nested JSON parsing and JSON Pointer selection in Awl source, no Python parser, eval or host JSON library runs inside the application

this is a source-library feature, not a builtin generic DOM, associated-value enum, installed Package, browser implementation or new compiler release

## native configuration lookup

with the current complete development toolchain

```sh
cd examples/parsing
awl build
./build/jget config.json /database/port
./build/jget config.json /names/0
```

`jget FILE [POINTER]` validates the entire UTF-8 JSON file before selecting a scalar, omitted/empty pointer selects the root, stdout contains the decoded string or exact number/boolean/null spelling followed by a newline, strings can include embedded newlines and NUL, output isn't re-encoded JSON

input is never modified, diagnostics go to stderr, input reads and output writes handle short transfers, input close and stdout flush are checked

| exit | meaning |
|---|---|
|0 | selected scalar written successfully |
|2 | bad arguments or invalid pointer/index syntax |
|3 | file open/read/close or output failure |
|4 | invalid UTF-8, JSON syntax or document limit |
|5 | missing path, ambiguous duplicate member or other selection failure |
|6 | selected object/array, scalar output only |
|9 | initial resource allocation failure |

## parser API

```Awl
use Json.aw as json;
func main(): i64
    @s tokens vector<text>: vector.new<text>(0);
    @s result vector<i64>: vector.new<i64>(0);
    if not vector.valid(tokens) or not vector.valid(result) { return 9; };
    if not json.parse("{\"port\":5432}", tokens, result) { return 4; };
    @p selected: json.locate("/port", tokens, result);
    if selected < 0 { return 5; };
    print(vector.get(tokens, selected));
    return 0;
end;
```

`parse(source, borrow tokens, borrow result) -> bool`

- success replaces tokens and result only after complete syntax validation and output capacity preflight
- failure preserves token length/content, result becomes `[code, byte_offset]`
- code1 syntax/unpaired surrogate,2 explicit limit,3 resource allocation
- if allocating the initial two diagnostic slots fails, false is returned without a new diagnostic, check result length before reading
- success result starts `[0, consumed_byte_length]`, then one `(kind, source_byte_offset)` pair for each token
- numeric tokens preserve exact spelling, no f64 conversion, overflow or rounding hidden in parsing

| kind | token payload |
|---|---|
|1 /2 | object / array open, empty payload |
|3 /4 | object / array close, empty payload |
|5 | decoded string value |
|6 | original number text |
|7 /8 /9 | true / false / null literal text |
|10 | decoded object member name |

member order and duplicate names are preserved, parser acceptance doesn't imply an application's configuration schema is valid, callers must choose their own duplicate/type/range policies

all JSON scalar/container forms, whitespace, escapes and decimal/exponent grammar are handled, surrogate pairs decode to Unicode scalars, isolated surrogates are deliberately rejected for interoperable UTF-8 text, byte order marks/comments/trailing commas/NaN/Infinity aren't accepted

limits are16384 source bytes,16 container nesting levels,512 total tokens including names and delimiters,4096 decoded UTF-8 bytes per string/name, initial builder capacity isn't treated as a limit, decoded byte counts are checked explicitly

failed parses can still allocate immutable intermediate strings in the runtime's process-lifetime region, this doesn't provide reclaimable strings or globally recoverable text allocation, resource-handle cleanup and128 repeated parse/failure/replacement cycles were tested

## pointer API

`locate(pointer, borrow tokens, borrow result) -> i64`

returns the selected token index, including containers, requires an intact successful parse tape with matching metadata, callers mustn't forge or mutate kind/nesting data

- `-1` absent value or traversal through a scalar, array `-` never selects an element
- `-2` invalid pointer/index syntax or pointer limit
- `-3` multiple matching decoded object names, no silent first/last-wins policy
- `-4` failed/mismatched tape shape
- `-5` pointer helper allocation failure

plain JSON Pointer form only, empty string is the document, `/` selects an empty object name, `~1` decodes slash and `~0` tilde in one pass, Unicode names compare exactly without normalization, array indexes are unsigned decimal without leading zeros, huge indexes fail missing without overflowing

syntax escapes are checked before traversal, URI fragment form and percent decoding aren't implemented, pointer limits4096 bytes/16 segments, the CLI can't pass embedded NUL through argv even though the library's text model supports it

## executed evidence and qualification

- `tests/json-parser.json`,440 cases each bundled-native and strict generated-C ASan/UBSan, independent Python event/byte-offset oracle, random valid documents, malformed mutations, numbers, Unicode, limits, pointers and repeated reuse
- `tests/jget.json`,28 cases each native/sanitized, real nested configuration lookup, exact numeric output, missing/ambiguous selections, invalid UTF-8, unchanged input and `/dev/full` output failure
- `demos/json/native-json.png`, actual Xvfb/Xterm capture of toolkit build, scalar lookup and byte-offset error
- parser timing in the report includes process startup, file reads and token output, not parser-only throughput, no speedup claim

compiler unchanged, old native compiler gates bind those same bytes, new source tests aren't new end-user distribution acceptance, native windows and browser execution remain unqualified

practical capability remains20.0% =9/45, CLI/backend were already stage2, this removes a real reusable parsing gap but doesn't satisfy another domain stage, no points for function/test counts

## primary-source decisions

https://www.rfc-editor.org/rfc/rfc8259.html informed grammar, UTF-8, escaping, exact number preservation, duplicate-name interoperability and the isolated-surrogate rejection policy

https://www.rfc-editor.org/rfc/rfc6901.html informed pointer escaping, empty names, array-index syntax, missing-path errors and ambiguous duplicate-name handling

historical `tests/persistence-windows-gui-development.json` was losslessly archived as `.json.gz` to keep the whole workspace below128MB, decompressed SHA256 remains `d59ac8802b08e92f7769a21f25edaa1fb13b95af2b98322370e3315b1befa105`, this changes no acceptance claim or protected distribution

`tests/files-windows-gui-development.json` was likewise losslessly archived as `.json.gz`, decompressed SHA256 remains `10312a0afbe585e81f5f0154f68c5c32bb3e814c6632901cdaff7077a884b218`, both byte identities are checked by the new checkpoint
