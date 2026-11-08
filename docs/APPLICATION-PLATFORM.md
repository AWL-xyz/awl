# Awl application-platform direction

Status: user requirement and roadmap. Update: the experimental0.8-dev checked byte-buffer/timing/native X11 window slice is implemented and tested; see NATIVE-WINDOWS.md. Native source modules/namespaces are also implemented/tested in0.8.1-dev (MODULES.md). Immutable native UTF-8 strings and X11 titles are implemented experimentally in0.8.2-dev (STRINGS.md), using a bounded process-lifetime region, not an owned heap. Other proposed APIs below are not implemented.

## Requirement

Awl is intended to be a general-purpose application language, not merely a scalar compiler or command-line demo language. A developer should be able to build native desktop applications, backend APIs, complete browser frontend/backend applications, and eventually applications in the complexity class of chat clients, browsers, image editors and streaming-media clients.

A real window API is a near-term priority. Transporting rendered pixels through a Python video helper does not satisfy that requirement. Existing 0.7.1 functionality and release archives are unchanged.

## Architectural direction (proposed)

Keep a small language core with shipped, versioned standard/platform libraries. Do not put HTTP, widgets, media codecs or browser engines into compiler syntax. Provide safe resource interfaces over native implementations; importing a platform module must not require Python or an unrelated application runtime.

The native-only download contract still applies: ship required development resources and libraries; no host SDK or package-manager fallback. Desktop applications inherently need a functioning OS display system and drivers. Document those runtime requirements separately from compiler/SDK dependencies. Do not promise a window on a headless kernel-only installation.

Use target-specific boundaries rather than pretending every OS/browser exposes identical facilities:

- Native desktop/server targets: OS APIs, windows/input, files, networking, threads, processes and GPU access as supported.
- Browser target: proposed WebAssembly code generation plus an explicit browser adapter for DOM/events/fetch, or another deliberately specified frontend target. Neither exists yet. JavaScript host glue is permissible as an explicit browser integration boundary, not a hidden dependency for native applications.
- Shared application modules: reusable types, validation and algorithms across supported targets; OS-only operations remain explicitly target-dependent.

Prefer mature, bundled native dependencies where appropriate. Reimplementing TLS, codecs or a browser engine from scratch is not a prerequisite for native Awl support, nor a sensible shortcut to production security. Dependency selection, licenses and security updates require explicit review.

## Incremental delivery gates

1. **Language/runtime foundations:** modules, strings, arrays/buffers, checked indexing and explicit resource lifetime/error handling. Add/test the minimal coherent subset needed for the next real application. Full ownership checking remains a separate, unfinished safety milestone.
2. **Real window vertical slice:** native window, lifecycle/event loop, close/resize, keyboard/mouse, monotonic timing and pixel-buffer presentation. Reuse the Awl pyramid renderer inside this window without Python or a separate rendering application. Test invalid handles, buffer extents and cleanup. Linux first; preserve a portable API boundary for Windows. Select/document the actual display backend before promising compatibility.
3. **Practical desktop foundations:** text/fonts, image decoding, clipboard, DPI, accessibility and GPU-backed rendering; a small paint application as acceptance workload. An initial framebuffer window is not a production UI toolkit.
4. **Backend foundations:** files, sockets, concurrency, HTTP, JSON, TLS integration, cancellation/timeouts, testing and observability. Validate with an actual API service and failure/load tests.
5. **Full-stack foundations:** browser target/integration, events/DOM, HTTP client, shared modules and repeatable frontend/backend builds. Validate with one working end-to-end app; do not claim browser support from native-only tests.
6. **Large application engineering:** packages/versioning, incremental compilation, debugger/profiler, storage, secure updates, sandbox boundaries, media, accessibility and platform validation. Broader application examples are targets, not completed capabilities or production-readiness claims.

The native-window pyramid acceptance workload now works using checked manual handles and byte-buffer primitives. This does not complete gate1: typed arrays/resource/error types and ownership remain next language foundations; native source modules and bounded immutable UTF-8 strings now exist. Operational hardening remains important but must not indefinitely displace application capabilities.

Update0.8.3: typed reusable UTF-8 builders now exist with explicit release and recoverable append errors (SPOOLS.md). They do not complete ownership/error/generic container semantics. General-purpose1.0 dependency order and the subjective~15% progress rubric are in ROADMAP.md. Packages registry/site/API/accounts/uploads are to-do only, deferred.
