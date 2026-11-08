#!/bin/bash
# Actual CLI execution, displayed in xterm and captured from Xvfb. No mock UI.
set -u
cd /home/user/Awl/build/files-demo
printf 'Awl 0.22 | Native files + strict UTF-8\n'
printf 'Exact extracted Linux bundle; no host compiler or Python in the apps.\n\n'
printf '$ ./kcopy input-utf8.txt copied-utf8.txt\n'
./kcopy input-utf8.txt copied-utf8.txt
printf '\n$ ./textinfo copied-utf8.txt\n'
./textinfo copied-utf8.txt
printf '\n$ ./textinfo invalid-utf8.bin\n'
./textinfo invalid-utf8.bin
printf 'exit status: %s\n' "$?"
printf '\n$ ./kcopy input-utf8.txt copied-utf8.txt\n'
./kcopy input-utf8.txt copied-utf8.txt
printf 'exit status: %s (existing destination preserved)\n' "$?"
printf '\n$ cmp input-utf8.txt copied-utf8.txt\n'
cmp input-utf8.txt copied-utf8.txt
printf 'byte comparison exit status: %s\n' "$?"
printf '\n$ ./discard-results\n'
./discard-results
printf '\nRegular-file I/O, not atomic replacement. Pixelboard is still in-memory.\n'
