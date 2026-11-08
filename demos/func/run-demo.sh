#!/bin/bash
set -eu
cd /home/user/Awl
mkdir -p build/func
export XDG_CACHE_HOME=/home/user/Awl/build/func-cache
exec > >(tee build/func/transcript.txt) 2>&1
printf '\033[2J\033[H'
printf 'Awl: func declarations and project-file imports -- not a language release\n\n'
compiler/native/bin/kcc --version
printf '\n$ cat examples-next/native/Library.aw\n'
cat examples-next/native/Library.aw
printf '\n$ cat examples-next/native/main.aw\n'
cat examples-next/native/main.aw
printf '\n$ env PATH=/no-host-tools build/func/Awl/bin/kcc run examples-next/native/main.aw --syntax next\n'
env PATH=/no-host-tools build/func/Awl/bin/kcc run examples-next/native/main.aw --syntax next
printf '\n$ cat tests/func-production-normal.txt\n'
cat tests/func-production-normal.txt
printf '\nACTUAL typed parser -> independent verifier -> C -> bundled native backend -> executable.\n'
printf 'Own-module bonus1, not importer bonus1000. No mock output, no host compiler in this run.\n'
printf 'Project imports NOW. Installed Packages AFTER the command-line tool; module globals/captures pending.\n'
printf 'Published0.23 downloads protected; Linux development evidence is not native Windows acceptance.\n'
touch build/func/window-ready
read -r _ || true
