# Awl Software Development Kit [Beta]0.26.0-dev

Linux x86-64 complete successor SDK, current next syntax ships in the published bundle, `func size :: @b values[i64], etc[i64]: i64 { ... };` replaces the parenthesized parameter and `end;` function forms, `func main: i64 { ... };` is the parameterless shape

the awk `: type` result annotation, `exports{...};` permissions, `@p/@s/@b/@o/@r/@w` modifiers, braced `if`/`elseif`/`else`/`while`, `name[T]` vector arguments and `${name}` interpolation are the published grammar, `--syntax legacy` still selects the explicit compatibility parser

new single-file `editor/awl-editor.html`, the `awl.` editor, ships with the owl mark, the current next-syntax highlighter/structural aid and a source-level JavaScript interpreter for the supported subset, every bundled example is checked by `kcc check` in `tests/awl-editor.json`

`editor/Awl-studio.html` remains the older deliberately limited legacy-subset playground with its own bundled sources, it is not the native compiler and isn't newly requalified

bundled resources are inherited byte-for-byte from the 0.25 archive and re-verified by the successor builder, no host compiler, end-user Python or extra backend download is required

public beta commands remain `init` and `build`, `kcc` stays internal compiler tooling, no public run/install/Packages/registry command is added

Windows0.24 remains an older, unaccepted native-host preview, native Windows acceptance stays deferred until language completion

practical capability stays26.7%=12/45, shipping the revised syntax and a new editor doesn't earn a workload stage, current authority is `tests/default-checkpoint.json` and `tests/awl-editor.json`
