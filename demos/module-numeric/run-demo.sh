#!/bin/bash
set -eu
cd /home/user/Awl
mkdir -p build/module-numeric
export XDG_CACHE_HOME=/home/user/Awl/build/module-numeric-cache
exec > >(tee build/module-numeric/transcript.txt) 2>&1
printf '\033[2J\033[H'
printf 'Awl: ACTUAL module variables, unquoted f64 numbers and math -- experimental, not a release\n\n'
compiler/native/bin/kcc --version
printf '\n$ cat examples-next/modules/Library.aw\n'
cat examples-next/modules/Library.aw
printf '\n$ cat examples-next/modules/main.aw\n'
cat examples-next/modules/main.aw
printf '\n$ env PATH=/no-host-tools build/Awl-linux-x86_64/bin/kcc run examples-next/modules/main.aw --syntax next\n'
env PATH=/no-host-tools build/Awl-linux-x86_64/bin/kcc run examples-next/modules/main.aw --syntax next
printf '\n$ attempt to assign readonly lib.fixed from importer\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp examples-next/modules/Library.aw "$tmp/Library.aw"
printf 'use Library.aw as lib; func main()->i64 lib.fixed: 7; return 0; end;\n' > "$tmp/main.aw"
if compiler/native/bin/kcc check "$tmp/main.aw" --syntax next; then exit 9; fi
printf '\n$ cat tests/module-numeric-normal.txt tests/module-numeric-sanitized.txt\n'
cat tests/module-numeric-normal.txt tests/module-numeric-sanitized.txt
printf '\nPrivate version128.59 is REAL module storage, not importer999.0 or literal substitution.\n'
printf '@r/@rw INSIDE exports only; initializers pure/ordered; owned module state/captures pending.\n'
printf 'sin/cos/sqrt/atan2 +pi/tau are builtins. Packages AFTER CLI.0.23 archives protected.\n'
touch build/module-numeric/window-ready
read -r _ || true
