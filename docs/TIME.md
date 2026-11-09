# local `time` Package

Awl is the language, `time` is a local Package that exposes two distinct clocks through the native compiler's checked intrinsics, `now` comes from the monotonic clock and `wall` comes from the UTC wall clock, the wall clock is a timestamp source and must not be used for timeouts

this Package is source-current, older distributed SDK archives do not contain it, a contributor build is not a complete SDK release

## layout and API

```text
use time;
```

| function | result | meaning |
| :--- | :--- | :--- |
| `time.now()` | `i64` | monotonic milliseconds from an unspecified origin, useful inside one process only |
| `time.wall()` | `i64` | milliseconds since the Unix epoch, UTC, may jump when the system clock is adjusted |
| `time.elapsed(since)` | `i64` | monotonic milliseconds since `since`, clamped to `0` for invalid or future origins |
| `time.deadline(timeout)` | `i64` | monotonic target `timeout` milliseconds from now, saturates at `9223372036854775807` |
| `time.remaining(deadline)` | `i64` | milliseconds until `deadline`, `0` once expired, never negative |
| `time.expired(deadline)` | `bool` | whether a monotonic deadline has passed |
| `time.sleep(ms)` | `bool` | sleeps `0..600000` milliseconds in bounded chunks, rejects out-of-range requests without trapping |

```text
func main[i64] {
    @p started: time.now();
    @p stamp: time.wall();
    if not time.sleep(20) { return 1; };
    print(time.elapsed(started) >= 1);
    print(stamp > 0);
    print(time.expired(started));
    return 0;
};
```

`examples/time-demo` installs a byte-identical copy under `packages/time/` and checks with `acc check examples/time-demo/main.aw`, generated native execution and a wall-clock delta against the host are covered by `tests/aesop_time.py`

## implementation

`clock_millis` uses `CLOCK_MONOTONIC` on POSIX and `GetTickCount64` on Windows, `wall_clock_millis` uses `CLOCK_REALTIME` on POSIX/WASI and `GetSystemTimePreciseAsFileTime` on Windows, the helper is emitted only into generated programs that call it so existing generated C stays byte-identical

the Windows `FILETIME` value is converted from 100-nanosecond intervals since 1601 UTC by subtracting `116444736000000000` and dividing by `10000`, the POSIX conversion checks the `timespec` nanoseconds and the full `i64` millisecond limit before multiplying, malformed clocks and numeric overflow trap instead of wrapping

the offline editor implements the same signatures with a virtual monotonic clock and `Date.now()` for wall time, that interpreter is not native-compiler equivalence

## limits

- wall time can move backwards and is unsuitable for elapsed measurements or deadlines
- monotonic values have an arbitrary origin and only make sense in one running program
- there is no timezone, calendar, ISO formatting, timer cancellation, async sleep or sub-millisecond API
- `sleep` accepts at most ten minutes, wraps the existing `0..60000` intrinsic in chunks and has no cancellation
- native Linux execution and generated-program sanitizers are checked, the Windows helper branch passes C11 source syntax with stubbed Win32 types, the Windows implementation is source-level only and native Windows-host acceptance remains deferred
- `db`, `websocket` and `fetch` remain unfinished, this Package does not add a registry or server install command

## primary references

- [POSIX.1-2024 `clock_gettime`, `CLOCK_REALTIME` and `CLOCK_MONOTONIC`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/clock_gettime.html)
- [Microsoft `GetSystemTimePreciseAsFileTime`](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getsystemtimepreciseasfiletime)
- [Microsoft `FILETIME` definition and `time_t` conversion constant](https://learn.microsoft.com/en-us/windows/win32/sysinfo/converting-a-time-t-value-to-a-file-time)
- [wasi-libc `clock_gettime` realtime/monotonic mapping](https://raw.githubusercontent.com/WebAssembly/wasi-libc/main/libc-bottom-half/cloudlibc/src/libc/time/clock_gettime.c)
