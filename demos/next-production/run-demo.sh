#!/bin/bash
set -eu
cd /home/user/Awl
mkdir -p build/next-production
export XDG_CACHE_HOME=/home/user/Awl/build/next-production-cache
exec > >(tee build/next-production/transcript.txt) 2>&1
printf '\033[2J\033[H'
printf 'Awl: experimental production native pipeline -- not a language release\n\n'
compiler/native/bin/kcc --version
printf '\n$ cat examples-next/native/Library.aw\n'
cat examples-next/native/Library.aw
printf '\n$ cat examples-next/native/main.aw\n'
cat examples-next/native/main.aw
printf '\n$ env PATH=/no-host-tools build/Awl-linux-x86_64/bin/kcc run examples-next/native/main.aw --syntax next\n'
env PATH=/no-host-tools build/Awl-linux-x86_64/bin/kcc run examples-next/native/main.aw --syntax next
printf '\n$ cat tests/next-production-normal.txt\n'
cat tests/next-production-normal.txt
printf '\nACTUAL typed parser -> independent verifier -> C -> bundled native backend -> executable.\n'
printf 'Own-module bonus1, not importer bonus1000. No mock output, no host compiler in this run.\n'
printf 'Module variables, captured closures, Package lookup and runtime redesign remain pending.\n'
printf 'Published0.23 downloads protected; Linux development evidence is not native Windows acceptance.\n'
touch build/next-production/window-ready
read -r _ || true
