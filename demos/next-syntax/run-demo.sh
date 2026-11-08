#!/bin/bash
set -eu
cd /home/user/Awl
printf '\033[2J\033[H'
printf 'Awl NEXT: native STRUCTURE/EXPORT prototype -- NOT executable language support\n\n'
printf '$ cat examples-next/exports/main.aw\n'
cat examples-next/exports/main.aw
printf '\n$ cat examples-next/exports/Template.aw\n'
cat examples-next/exports/Template.aw
printf '\n$ compiler/next/bin/Awl-next-syntax examples-next/exports/main.aw\n'
compiler/next/bin/Awl-next-syntax examples-next/exports/main.aw
printf '\n$ compiler/next/bin/Awl-next-syntax examples-next/exports/Template.aw\n'
compiler/next/bin/Awl-next-syntax examples-next/exports/Template.aw
printf '\n$ check an attempted write to t.var1 (@r)\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp examples-next/exports/Template.aw "$tmp/Template.aw"
sed 's/t.variable:/t.var1:/' examples-next/exports/main.aw > "$tmp/main.aw"
if compiler/next/bin/Awl-next-syntax "$tmp/main.aw"; then exit 9; fi
printf '\n0.26 RELEASE UNCHANGED. Math/arrays/graphics/strings/concurrency remain roadmap work.\n'
mkdir -p build/next
touch build/next/window-ready
read -r _ || true
