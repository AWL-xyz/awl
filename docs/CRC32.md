# Streaming CRC-32 Package

The local `crc32` Package computes CRC-32/ISO-HDLC, the same byte checksum as Python's `zlib.crc32`. It uses the reflected polynomial `0xEDB88320`, an initial word of `0xffffffff`, and a final XOR with `0xffffffff`. It is **not** CRC-32C or a cryptographic hash, and it does not authenticate data.

From an initialized project's directory:

```sh
awl add /path/to/awl/packages/crc32/crc32.awpkg
```

Import it with `use crc32;`. The Package is ordinary Aesop source, with no external library or network dependency. It requires an ACC build that supports the [`bits` namespace](API.md#unsigned-bit-operations).

| Call | Result | Meaning |
| :--- | :--- | :--- |
| `crc32.start()` | `u32` | Start a new, unfinalized checksum state. |
| `crc32.update(state, bytes, offset, count)` | `u32` | Update the state with `count` bytes from a buffer handle, starting at the zero-based `offset`. The handle, offset and count are `i64`. |
| `crc32.finish(state)` | `u32` | Finalize and return the checksum without modifying the state. |

Start once, keep the **unfinalized** word returned by each update, and call `finish` when you want the digest. Do not feed a finalized digest back into `update`. There is no shared state; you can keep separate words for multiple streams or finalize a copy to inspect the checksum so far.

The input buffer is not modified, retained, or freed. An empty range, including at the end of a live buffer, leaves the state alone. An invalid or freed handle, negative offset or count, or a range outside the buffer traps; the Package checks `count <= buffer.size(bytes) - offset` before adding the two. The bytes need not be UTF-8, and NULs and newlines count like any other byte. Each update takes linear time in the chunk length and uses constant scratch space with no heap allocation by the Package.

```text
use crc32;

func main {
    @p bytes: buffer.new(9);
    if bytes == 0 { return 1; };
    defer buffer.free(bytes);
    if buffer.writetext(bytes, 0, "123456789") != 9 { return 2; };

    @p state: crc32.start();
    state: crc32.update(state, bytes, 0, 4);
    state: crc32.update(state, bytes, 4, 5);
    print(crc32.finish(state)); -- 3421780262 (cbf43926 in hex)
    return 0;
};
```

The [CLI example](../examples/crc32-demo/) reuses one 64 KiB buffer, so the input does not need to fit in an Awl buffer. It prints eight lowercase hex digits and a newline. Empty input prints `00000000`.
