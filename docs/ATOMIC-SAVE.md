# atomic local file replacement

new native intrinsic `file_replace(directory:text, temporary:text, target:text) -> i64`, Linux-qualified, Windows/other targets return-6, not a new public toolkit command or Package

## contract

finish writing and close all writers to the temporary file first, both names must identify files in the same trusted existing directory, single-writer use only

- directory is a nonempty UTF-8 path of at most4095 bytes, its final component is opened with O_DIRECTORY/O_NOFOLLOW/CLOEXEC
- names are1..255 UTF-8 bytes, no NUL or slash, not `.` or `..`, distinct names required
- source must be a regular non-symlink file, existing target must also be regular/non-symlink, same-inode hard-link aliases are rejected
- a held directory descriptor anchors relative open/stat/rename operations
- source file fsync and checked close happen before renameat
- successful rename publishes the new target atomically, then directory fsync and checked close are attempted

| result | meaning |
|---|---|
|0 | published, source and directory sync calls and checked closes succeeded |
|1 | published, but directory sync or close failed, durability is uncertain |
|negative | validation, preparation or rename reported failure, see existing file error mapping |

on qualified local filesystem failure tests, negative results leave the old target unchanged and the temporary file available, a result1 must **not** be treated as an unpublished operation or blindly retried

after successful publication, the temporary name disappears, existing readers of the old target descriptor retain the old inode, new opens see the replacement, the replacement inherits temporary-file metadata, not the old target's permissions/ownership/timestamps

EINTR retries apply to open/fsync, close isn't retried, rename isn't blindly retried, descriptors are released on all paths, existing manual file-handle slots aren't consumed

## limits and non-guarantees

atomic name visibility isn't an exactly-once transaction or hardware power-loss proof, crashes/lost acknowledgments can leave an application unsure which version was published, failed staging can leave a partial temporary file needing manual inspection/removal

trusted directory and ancestors are required, there is no lock, sandbox, race-proof defense against hostile concurrent directory changes, source must remain unchanged during publication, target metadata and multi-file transactions aren't preserved

native qualification is Linux local storage only, distributed/NFS rename-error ambiguity and filesystem/device crash behavior aren't qualified, existing full paths may traverse ancestor symlinks, final directory and file symlinks are rejected by this primitive

## real ksave workload

```sh
cd examples/apps/ksave
awl build
mkdir -p /var/tmp/settings
printf '{"port":5432}\n' | ./build/ksave /var/tmp/settings scratch config.json
```

current complete development toolchain required, protected0.23 downloads don't contain this intrinsic

ksave reads binary stdin in64KiB chunks into an exclusively created staging file, handles short transfers and checked close, then calls file_replace, at most512MiB input, an existing staging name is never truncated, target isn't opened destructively

stdout reports the publication status, exit0 published/syncs succeeded,2 arguments,3 staging create,4 input/write/close failure,5 publish failure,6 published but sync uncertain,7 status-output failure,9 buffer allocation, exit7 can occur after publication

relative temporary/target names only, argument validation precedes staging, CLI staging still uses the existing full-path file_open API, this isn't a filesystem sandbox, staging isn't automatically deleted on error

## executed gates

-72 normal/strict-sanitizer API and CLI cases, binary input, UTF-8 names, aliases/symlinks/FIFOs, existing open readers, concurrent old-or-new observations and checker diagnostics
-14 strict sanitizer fault/reuse cases, file/directory sync and close failures, rename failure, EINTR,400 replacements under32fd limit, embedded NUL rejection
-all10 native compiler sanitizer phases passed,695 targeted verifier corruptions/10000 structural cases,6 dedicated replacement verifier/emitter cases
-rebuilt compiler regressions,45 native+45 sanitizer networking,440 JSON+28 jget+275 graphics EACH native/sanitized
-actual terminal capture `demos/replace/native-replace.png`, measured warm native save workload in `benchmarks/replace-latest.json`, timings aren't production throughput

current compiler SHA256 `a5bd28995b866973a97e8969ae0cf4c6170663f3878e1237d3e8576a299ed3fe`, old checkpoints bind their old compiler bytes and stay historical, full three-mode legacy suite wasn't rerun for this change, no new release archive or native Windows acceptance

index stays20.0% =9/45, safer storage is meaningful language/runtime progress, not another cumulative workload stage

## research and preservation

https://man7.org/linux/man-pages/man2/rename.2.html informed atomic replacement, descriptor-relative names, old open readers and same-inode alias handling

https://man7.org/linux/man-pages/man2/fsync.2.html informed separate file/directory synchronization and explicit post-publication uncertainty

five historical full-isolation JSON reports were losslessly archived to `.json.gz`, original hashes and sizes are in `tests/replace-evidence-archives.json`, protected distributions and all evidence bytes remain intact
