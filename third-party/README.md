# Third-party provenance and notices

KERN's original compiler source is MIT licensed (root LICENSE). This does not
relicense third-party components.

## Native bundle

- **Zig 0.15.2, official Linux x86-64 distribution.** Pinned URL, size and SHA-256:
  `compiler/toolchain-lock.json` (copied into the bundle manifest). Zig's MIT notice
  and the entire upstream `lib/`/documentation/resources are shipped unchanged at
  `libexec/zig/`, including original component notices.
- **LLVM, Clang and LLD 20.1.2**, integrated in that Zig binary. LLVM's Apache 2.0
  license with LLVM exception is reproduced in `LLVM-LICENSE.txt`, fetched from
  https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-20.1.2/llvm/LICENSE.TXT.
- **musl libc/startup resources**: original notice at
  `libexec/zig/lib/libc/musl/COPYRIGHT`; bundled source retains notices. Outputs and
  the packaged KCC are static musl, not linked against host glibc/libstdc++.
- **libc++, libc++abi, libunwind/compiler runtime resources**: shipped upstream
  sources/notices under `libexec/zig/lib/`; LLVM notice/exception also supplied.
- The full upstream distribution includes resources for targets KCC does not
  support yet. Those resources retain their original licenses; their presence is
  not a claim of KERN target support.

The preview carries upstream source/notices and provenance; this is not a legal
compliance audit or cryptographically signed release infrastructure. The separate
GCC-built contributor frontend is not the binary shipped in the Linux bundle.

## Unicode data

`compiler/native/unicode_tables.inc` (bundle `src/unicode_tables.inc`) contains
range data generated using CPython `str.isalnum`/`str.isprintable`, pinned to Unicode
15.1.0. Unicode's notice is in `UNICODE-LICENSE.txt`, retrieved from
https://www.unicode.org/license.txt on 2026-11-05. The installed compiler loads
neither Python nor external Unicode data. Changing the database is an explicit
lexical-policy change, not an automatic dependency update.
