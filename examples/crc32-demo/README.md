# Streaming CRC-32 from stdin

This example reads raw bytes from stdin with a reusable 64 KiB buffer and prints the CRC-32/ISO-HDLC checksum as eight lowercase hexadecimal digits. It reads until EOF rather than loading the whole input. It does not decode UTF-8 or drop line endings.

From the repository root, with the [source-built toolkit](../../README.md#quick-start-from-source) on Linux x86-64:

```sh
(cd examples && printf '%s' 123456789 | awl run crc32-demo --cc "$(command -v cc)")
(cd examples && awl test crc32-demo --cc "$(command -v cc)")
```

The first command prints `cbf43926`. Use stdin redirection to checksum a file; the demo takes no program arguments. It returns `2` for unexpected arguments and `3` for reported input, output or allocation errors.

This project includes an unmodified vendored copy of the local Package. For other projects, run `awl add /path/to/awl/packages/crc32/crc32.awpkg` and import `use crc32;`. See [CRC-32 semantics and the streaming API](../../docs/CRC32.md).
