# bounded native subprocesses, source candidate

current compiler source adds synchronous trusted-command supervision, not async tasks, a sandbox, general concurrency or a published SDK feature, Linux0.25 download/root binaries and the older Windows preview remain unchanged

```text
@p scoped arguments vector<text>:vector.new<text>(0);
vector.push(arguments,"hello; literal argument");
@p scoped out spool:spool.new(4096);
@p scoped err spool:spool.new(4096);
@p code:process.capture("/bin/echo",vector.view(arguments,0,1),out,err,1000);
```

`process.capture(program:text,args:view<text>,out:spool,err:spool,timeout_ms:i64): i64`

both builders are borrowed, must be distinct and remain valid, argument views are checked before use, inputs are copied into a bounded argv arena, no mutable pointers or process handles escape

| result | meaning |
|---|---|
|0..255|actual normal exit status|
|-1|invalid limits/arguments, aliasing builders or unsupported SIGCHLD disposition|
|-2|executable/interpreter missing|
|-3|allocation/setup/spawn failure, including permission/format failures|
|-4|execution/capture deadline reached|
|-5|either output exceeds remaining builder capacity|
|-6|captured output is not valid UTF-8|
|-7|capture/clock/wait failure|
|-8|unsupported target, explicitly returned by real WASI|
|`-1000-signum`|child terminated by a signal|

normal and signal termination append both complete UTF-8 byte streams atomically to the existing builders, all other failures preserve both builders, embedded NUL output is preserved, argv/program NUL is rejected, output appends rather than clearing

## limits and lifecycle

- exact executable path, no PATH search or implicit shell, metacharacters remain ordinary argv data, explicitly launching a shell is still the caller's choice
- at most128 arguments excluding argv0,4096 bytes per argument/program and65536 combined argv bytes including terminators
- deadline1..600000ms, monotonic clock, capture uses both pipes concurrently so a full stderr pipe cannot deadlock stdout reading
- inherited working directory/environment, stdin is `/dev/null`, child signal mask/defaults are reset, unrelated descriptors are closed via a bounded `/proc/self/fd` scan, at most4096 open descriptors considered
- each child starts in a new process group, completion/error cleanup sends SIGKILL to the group and separately to the leader, the leader is reaped, successful completion doesn't leave cooperative background group members running
- WNOWAIT retains the leader's identity until cleanup, preventing PID-reuse group kills, a nondefault SIGCHLD disposition is rejected, no other thread/handler may reap these children
- Linux pidfd notification removes the earlier10ms polling delay, older/unavailable kernels use a10ms bounded polling fallback, both modes have failure tests
- output scratch buffers temporarily allocate each builder's remaining capacity plus one byte, bounded by existing16MiB-per-builder limits, these temporary bytes are additional to the builders'64MiB combined allocation budget

trusted cooperative jobs only, descendants can deliberately leave a process group, descendant zombies belong to their new parent/init, only the direct leader is reaped here, this isn't hostile-process containment, a daemon/service manager, resource-limit/cgroup sandbox or automatic parent-death cleanup

timeouts aren't hard real-time guarantees, OS scheduling, spawn/file access, denied signals and uninterruptible kernel work can delay completion or cleanup, no arbitrary cancellation/stdin streaming/interactive terminal API is claimed

## useful native workload

`apps/taskrun` validates an entire bounded JSON plan before running any job, then sequentially supervises explicit argv commands, reports separate stdout/stderr, fails fast, handles nonzero/signal/timeout/quota errors and runs real bundled-SDK build-and-execute batches with host tools removed from PATH

this is Awl plan parsing, validation, scheduling, result matching and reporting backed by native process control, Python is a contributor test client, not the task runner implementation

see `apps/taskrun/README.md`, source modules are reused by vendoring the existing JSON/file helpers, not installed Packages

## qualification and measurements

`tests/process-capture.json` records103 normal/sanitized workload/runtime checks, including16-job and128-argument limits, descriptor closure, dual262144-byte streams, group and changed-leader-group cleanup, invalid UTF-8 and atomic rollback, real WASI returns unsupported rather than simulating execution

`tests/process-faults.json` records24 fault/lifecycle cases in each of four sanitizer modes, normal/fallback and open/closed standard descriptors,200 repeated captures per mode with no temporary allocations/fds/direct zombies retained, allocation/pipe/fcntl/spawn/clock/poll/read failures, EINTR retries, no leaked descriptors or unreaped direct children

`tests/process-native.json.gz` and `tests/process-checkpoint.json` bind independent verifier/full compiler sanitizer regression and exact source/report hashes, old checkpoints remain historical source bindings

local12-sample consumed process-inclusive capture latency median was1.263ms native and7.653ms sanitized, a30ms deadline returned in30.738ms and36.460ms respectively, the earlier polling prototype measured11.633ms native, shared-host/process noise applies, no universal speed or C++/Rust comparison is claimed

## primary references

- [POSIX2024 posix_spawn](https://pubs.opengroup.org/onlinepubs/9799919799/functions/posix_spawn.html), explicit argv, file actions, signal/process-group attributes and error handling
- [Linux waitpid/waitid](https://man7.org/linux/man-pages/man2/waitpid.2.html), WNOWAIT and reaping semantics
- [Linux poll](https://man7.org/linux/man-pages/man2/poll.2.html), simultaneous pipe readiness, EOF draining and EINTR
- [Linux pidfd_open](https://man7.org/linux/man-pages/man2/pidfd_open.2.html), process-exit notification and identity/reaping preconditions
