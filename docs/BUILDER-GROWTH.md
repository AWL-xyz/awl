# explicit UTF-8 builder growth and truncation, source candidate

```text
func edit :: @b value:spool: bool {
    if not spool.reserve(value, 4096) { return false; };
    if spool.append(value, "café 🦉") != 0 { return false; };
    return spool.truncate(value, 4);
};
```

`spool.reserve(builder,capacity_bytes): bool` grows explicitly, preserves bytes/scalars/identity, capacities at or below the current capacity succeed without shrinking/reallocating, negative/over16MiB requests and allocation/combined-budget failures return false unchanged, no realloc-to-zero case is used

`spool.truncate(builder,length_scalars): bool` retains a Unicode-scalar prefix and current capacity, negative/growing lengths fail unchanged, equal length succeeds unchanged, zero clears, this is O(retained-prefix bytes), not constant-time backspace or grapheme-cluster editing, combining marks are separate scalars

append remains fixed-capacity/atomic and never grows implicitly, snapshots remain independent immutable copies, raw pointers don't escape, current single-threaded borrow restrictions remain, reserve still obeys16MiB per builder/64MiB combined payload, truncating doesn't release capacity or reclaim immutable snapshots

`apps/logwindow` now starts its reusable line buffer at64bytes and explicitly doubles up to4096, a short-line file requests4032fewer initial builder payload bytes than the previous fixed4096 policy, this is requested capacity arithmetic, not whole-process RSS or a throughput claim, the input/line limits and errors are unchanged

500 seeded independently modeled operations produce2000 expected lines each on native, ASan+UBSan and real Node WASI, including ASCII/UTF8/NUL/combining marks, reserve failure/no-op and truncation boundaries, direct sanitizer fault tests force realloc failure, verify immutable snapshots, stale-handle traps and64MiB budget/reuse

108 normal/sanitized logwindow cases include exact4096-byte Unicode lines and4097-byte rejection,103 process/taskrun cases and the direct process fault/reuse oracle also passed under the current syntax,15 compiler sanitizer phases are now restored after migrating embedded next fixtures, including855 targeted verifier corruptions

historical reports and legacy parsing stay separate, the full historical564×3 legacy suite and general JavaScript editor weren't rerun/migrated in this increment, published SDK bytes are unchanged, current evidence tests/package-import-checkpoint.json, tests/polish-checkpoint.json is historical

no new workload stage, score remains26.7%=12/45, wider containers, reclaimable immutable strings, efficient editing, editor migration and complete successor SDK qualification remain open

primary allocation reference, [Linux malloc/realloc documentation](https://man7.org/linux/man-pages/man3/malloc.3.html), failed realloc preserves the old allocation, implementation updates metadata only after success
