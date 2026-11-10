# Awl native Windows x86-64 — engineering preview (0.23)

**Not yet an accepted Windows release.** Real Windows build/run acceptance is
pending. Linux acceptance is separate; the Windows preview does not replace its release.

This is a complete Windows-host distribution, not a Linux-to-Windows cross-link
example: native bin/kcc.exe, complete checksum-pinned Windows Zig0.15.2 compiler,
linker/libc/headers/startup resources, licenses, Awl sources and examples. Users do
not run Python, install MinGW/Visual Studio/SDKs, use WSL, or download a backend.

## Windows10/11 x86-64 preview workflow

Extract the complete archive (including libexec), with an xz-capable archiver;
Windows tar may be used if the installed version supports xz. Do not copy kcc.exe
alone. From PowerShell in the extracted Awl directory:

```
.\bin\kcc.exe --version
.\bin\kcc.exe check .\examples\hello.aw
.\bin\kcc.exe run .\examples\hello.aw
.\bin\kcc.exe build .\examples\apps\intstats\main.aw -o .\intstats.exe
.\intstats.exe 42 -7 19 0 42
```

Build output defaults to source stem plus .exe in current directory; explicit -o
is used literally. Compiler arguments/source paths are converted from UTF-16 to
UTF-8; process execution uses CreateProcessW and CRT-compatible argument quoting,
not shell interpolation. Ordinary spaces and non-ASCII path tests are in the
Windows gate. Console rendering/fonts may still affect non-ASCII display. Native
integer argv APIs intentionally reject non-ASCII numeric text.

The Win32 driver finds its installation via GetModuleFileNameW; invokes ONLY its
bundled zig.exe with an explicit executable path and a restricted backend
Unicode environment (no system tool fallback). Runtime programs inherit caller
environment. Global cache uses LOCALAPPDATA/Awl; temporary compilation uses a
random user+SYSTEM-only directory. Output is exclusively staged in the destination
directory, validated as an x86-64 PE executable, and published via MoveFileExW.
Source/import identity checks reject overwriting source, including existing hard
links. Destination directory and installation should be trusted/user controlled.

Children start suspended, enter a non-inherited kill-on-close Job Object, then
resume. Job memory is bounded for builds (--build-memory-mib); build/run wall
timeouts return124; Ctrl-C/Break supervision returns130. Descendants are terminated
and accounted for before normal cleanup. Unhandled abnormal NT exception status
maps to2; ordinary0..255 program exit status is propagated. Windows has different
resource limits from Linux: no equivalent RLIMIT_FSIZE or file-descriptor limit
here; oversized generated PE is rejected AFTER backend completion. This is process
supervision, not a security sandbox or hostile-program execution boundary. Parent
termination/job semantics, cancellation, nested jobs and memory limits require real
Windows validation, not inference from Wine behavior.

## Actual evidence / limits

The Windows compiler cross-builds with warnings-as-errors, executes its frontend
under Wine10, and can emit C/check source. Generated Windows PE programs can be
cross-built and executed under Wine independently. Dedicated fake-backend driver
fixtures exercise process launch/staging/timeouts; **a fixture is not real backend
acceptance**. The unmodified pinned upstream Windows Zig fails `zig env`/`zig cc`
in this Wine environment with `unable to find zig self exe path: Unexpected`;
that reproduces without Awl. No production/real-Windows test claim follows.
A separate Windows-host CI workflow builds/extracts the exact complete archive,
then runs actual installed kcc.exe check/build/run/intstats and failure cases with
an empty tools PATH. Its configuration is included; no remote run is claimed.

Language/runtime scope: integer and strict Unicode text CLI, regular-file I/O,
binary kcopy/UTF8 textinfo (see FILES.md), modules, vectors/builders and supported core
semantics. Windows clock/sleep/buffers and framebuffer windows now use native APIs.
The USER32/GDI window implementation and Pixelboard app are described in
WIN32-GUI.md. This is a small framebuffer/event API, not production desktop
readiness, a widget/IME toolkit, networking/browser/general streams or ARM support. Full frontend regression/sanitizer coverage on Linux remains separate.

Pixelboard drawing files/save/load: see PIXELBOARD-FILES.md. The0.23 platform.kind
intrinsic reports OS family only; keyboard text/layout/IME normalization is not
provided. Windows installed-backend acceptance remains a separate gate.
