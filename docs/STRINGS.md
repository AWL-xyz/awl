# Native UTF-8 strings — 0.8.2-dev

Implemented experimental native project feature, not a complete language or production heap. Use the bundled `bin/kcc`, not the older Python reference compiler. `examples/strings/main.aw` is an executable example; strings work across native source modules, parameters/returns, locals, by-value structs and tagged unions.

```Awl
function main() -> i64
    local text: string = "Hello, 世界 🚀"
    print(text)
    print(string.length(text))
    print(string.bytes(text))
    print(string.slice(text,7,2))
    print("answer=" + string.from_i64(42))
    return 0
end
```

## Values and syntax

`string` is an opaque immutable sequence of valid UTF-8, not a NUL-terminated C string. It has no source-level pointer/byte-field access. Embedded U+0000 is allowed. Copying a string copies a descriptor, not its bytes. Unicode scalar counts are distinct from byte counts and from user-perceived characters/graphemes. There is **no implicit normalization, locale, case folding, grapheme segmentation or implicit integer/string conversion**. For example `"é" != "e\u{301}"`, and the latter has two scalars.

Double-quoted single-line literals support raw UTF-8 and `\"`, `\\`, `\n`, `\r`, `\t`, `\b`, `\f`, `\0`, `\u{hex}` escapes. Unicode escapes require 1–6 hexadecimal digits and a scalar (0–10FFFF excluding D800–DFFF). Actual CR/LF within a literal, unterminated literals and malformed escapes diagnose E102. Invalid UTF-8 source diagnoses E008 through the project loader. Each decoded literal is limited to 65,536 bytes (E103); aggregate source remains limited to 1 MiB. Literal contents do not act as comments, imports or generated source.

`+` concatenates two strings. `==` and `!=` compare exact UTF-8 bytes, including embedded NULs. `<`, `>`, other arithmetic and truthiness are not defined for strings. `print(s)` writes its exact bytes followed by a newline; string printing flushes stdout and checks stream errors. It does not replace integer/bool printing semantics or turn arbitrary byte buffers into text.

## Exact intrinsic signatures

| Function | Argument types → result | Meaning |
|---|---|---|
| `string.bytes(s)` | string → i64 | UTF-8 byte count, O(1) |
| `string.length(s)` | string → i64 | Unicode scalar count, O(1) |
| `string.byte_at(s,index)` | string,i64 → u8 | Zero-based byte access, O(1) |
| `string.codepoint(s,index)` | string,i64 → u32 | Zero-based scalar access, O(index) scan |
| `string.slice(s,start,count)` | string,i64,i64 → string | Checked scalar-based immutable view; no allocation, O(start+count) |
| `string.from_codepoint(cp)` | u32 → string | Encode exactly one checked scalar |
| `string.compare(a,b)` | string,string → i64 | Exactly −1/0/1, lexicographic UTF-8 byte order (same as scalar order for valid UTF-8), O(shorter byte length) |
| `string.from_i64(n)` | i64 → string | Exact base-10 signed integer, including minimum i64 |
| `string.from_u64(n)` | u64 → string | Exact base-10 unsigned integer, including maximum u64 |

Negative indices/counts, indices at/past the relevant length, invalid scalars and out-of-range slices abort with `Awl string trap`. An empty slice at the end is valid; bounds arithmetic avoids signed overflow. Errors are **not recoverable Result values yet**. Conversion from arbitrary byte buffers/files is intentionally absent until a checked decoding/error API exists.

Concatenation costs O(a.bytes+b.bytes), allocates unless one side is empty, and never mutates either input. Equality/compare can scan a common prefix. Repeated concatenation of an accumulating prefix can be quadratic: a future builder/owned-container API is needed; this milestone does not claim a performance-optimal general text library.

## Memory/lifetime contract — important limitation

The generated 64-bit descriptor is 24 bytes/alignment 8: read-only data pointer, byte count and scalar count. Generated C asserts that ABI; it is private implementation detail, not a stable public FFI. The checker and independent arena verifier both account for this layout in aggregates. Literal UTF-8/payload/shape/type/size and aggregate literal budgets are independently verified before emission. Every literal byte is hex-escaped in generated C, including NUL and quote/backslash bytes.

Literals have static storage. Dynamic strings use a **process-lifetime region** capped at **64 MiB cumulative payload and 65,536 allocations**; these caps are separate from byte-buffer/window limits and not a whole-process memory sandbox. Allocation metadata/allocator overhead and static literal storage are additional. The region is reclaimed by an `atexit` cleanup on normal exit; the OS reclaims process storage on abnormal termination. Allocation failure/cap exhaustion traps. Empty concatenations and slices reuse storage without allocation. Individual strings cannot be freed; dropping/reassigning a descriptor does NOT reclaim storage.

Consequently aliases, returned values and slice views remain valid, including after function return or replacement of another descriptor, but a long-running allocation-heavy app will exhaust the region. This deliberately bounded initial model is **not a tracing GC, reference counting, ownership/borrow checking, constant-memory long-running heap, or production resource-lifetime solution**. It avoids a false ownership claim while allowing native string workloads now. Thread-safe allocation/concurrency is not implemented.

## Window integration

`window_set_title(w: i64,title: string) -> bool` updates `_NET_WM_NAME`/`UTF8_STRING` and legacy `WM_NAME` bytes on the supported local X11 backend. At most 1,024 UTF-8 bytes, no embedded NUL. Empty title is valid. Closed windows, overlong/NUL titles and detected transmission failures return false; invalid/stale/wrong-kind handles still resource-trap. Success means requests queued, not that every window manager acknowledged/displayed them. This is title metadata, **not** font rendering, text input, IME or a widget toolkit. Native Wayland/Windows backends remain missing. Atoms are initialized before event handling so title changes do not consume pending input replies/events.

## Compatibility and evidence

The filesystem project path selects `Awl_lex_project` (string token flag4, unterminated status6). Legacy `Awl_lex` retains quote rejection and existing token/error behavior; byte/token parser APIs do not enable string-literal or qualified-project grammar. The native primitive type and intrinsic registry are extended; the Python reference subset is not. The C scanner ABI remains1 with an additive project-scanner entry point.

`tests/test_strings.py` exercises literals/escapes/NUL, Unicode boundaries, 40 deterministic randomized scalar/byte/slice/concat oracles at O0/O3, type failures, slice/scalar/heap traps, module boundaries, aggregate copies, returned views, formatting extremes, source columns and omission of unused runtime. Native scanner/arena corruption harnesses and emitted-C ASan/UBSan exercise the new boundary. Authenticated Xvfb tests read the actual UTF-8 title property and reject NUL/overlong updates. Local test logs/release report distinguish executed results from configured remote CI. No formal safety proof or cross-platform runtime certification is implied.

## Subsequent0.8.3 reusable storage

Typed text builders (SPOOLS.md) now support explicit reclamation and reusable text construction. They do not change this immutable-string lifetime contract. Nonempty snapshots copy into this same bounded region; use direct builder append/decimal/print in reuse loops.


## Next-syntax additions

`string_find`, `string_contains`, `string_starts_with`, `string_ends_with` and `string_replace(s,from,to)` are exact UTF-8 byte matches, find returns a scalar index, `for ch in text` iterates `u32` codepoints in O(n), `"${a.b}"` interpolates dotted field paths
