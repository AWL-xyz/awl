# Conditional builder ownership (0.15)

Native projects can move a visible eligible builder owner within either `if`
branch, into a scoped destination or as an explicit owning-call argument.

```
scoped b:spool=spool.new(32)
if use_helper then
    finish(move b)
else
    scoped ready:spool=move b
    spool.print(ready)
end
```

Each branch starts from the same incoming ownership state. At the join, an owner
is unavailable if **any continuing branch** consumed it. A branch that always
returns does not contribute to the continuing state. An omitted else is a real
continuing path. No constant-condition reasoning is performed, even for true or
false literals. A later borrow/move/reassignment of a possibly moved owner is
rejected (E221). This is conservative: no conditional liveness query or recovery.

Cleanup remains guarded and lexical. On a nonconsuming path the outer owner
releases normally; on a consuming path its descriptor is cleared and the new
owner releases. No payload copy, reference counting or extra runtime join flag.
The checker and independent verifier reconstruct states from control flow.
Consumed state is keyed by unique binding symbol, not just source spelling;
shadowing must neither resurrect a moved outer owner nor consume an unrelated
outer binding.

A `while` body remains a consumption barrier for owners from outside that loop,
including through nested ifs. An owner allocated within an iteration can be
consumed by that iteration's branches. Match-arm outer ownership transfers and
loop-carried moves/reinitialization remain unsupported. Existing terminal owned
returns can move a visible owner because that path exits the function.

Owning calls remain direct statements/new-local initializers/direct returns,
not conditions, binary/short-circuit expressions or nested arguments. Borrowing
and consuming one owner in a call remains rejected. Only spool is covered;
not other resources, owned aggregates/strings, general references, exceptions or
trap unwinding. This is an if-join milestone, NOT complete ownership analysis.
