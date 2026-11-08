# taskrun, bounded native batch supervisor

requires the current subprocess/view-capable compiler source candidate, not the published Linux0.25 SDK, contributor compiler builds must stay separate from qualified release binaries

```sh
awl build apps/taskrun/main.aw -o taskrun
./taskrun tasks.json 1000
```

```json
[["/bin/echo","hello; literal argument"],["./my-program","--check"]]
```

the second CLI argument is a per-job timeout of1..60000ms, jobs run sequentially with fail-fast behavior, stdout/stderr are separately labeled, a fully validated plan is required before the first child starts

at most16 jobs,128 arguments per job excluding the program,4096 bytes per string and captured stream,16384 manifest bytes and512 JSON tokens globally, these joint limits can prevent using every per-job maximum simultaneously, empty plans/jobs/programs, nested/nonstring arguments and NUL arguments are rejected

relative executable paths resolve from the inherited working directory, paths aren't searched in PATH, no implicit shell, stdin is EOF, environments are inherited, jobs are trusted and may have side effects, output capture failure preserves no partial child logs in the freshly cleared builders

exit codes,0 all passed,1 child nonzero exit,2 usage/schema,3 plan read,4 timeout,5 capture/signal failure,7 captured-log output failure,9 resource exhaustion, ordinary print I/O retains existing trap semantics

`Process.aw` exposes typed exported outcomes, `Plan.aw` uses the existing source JSON parser, vendored `File.aw` and `vendor/Json.aw` preserve their originals, not installed Packages

executed normal/sanitized real compiler-build→program-execution batches use the bundled SDK with no host-tool PATH, this is a bounded process-supervision workload, not resumable/durable/distributed scheduling or a production service manager

see ../../docs/SUBPROCESSES.md and ../../tests/process-capture.json
