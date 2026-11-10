# security policy

Awl is experimental source, the compiler emits C and the generated runtime includes bounded resource checks, it is not a production sandbox

## reporting

please report suspected vulnerabilities through a private GitHub security advisory for this repository, include a minimal `.aw` source, compiler command, generated C if relevant, host platform and expected versus observed behavior

do not include credentials, private notes or historical capsules in a report, please allow time for a fix before public disclosure

## scope

in scope for current source:

- memory safety or undefined behavior in generated C
- checker or independent-verifier bypasses
- ownership, bounds, resource trap and integer conversion failures
- path traversal or unsafe behavior in local Package resolution

out of scope for current source:

- older protected SDK archives, which are immutable historical distributions
- third-party Zig, libc or browser dependencies, report those upstream as well
- claims requiring native Windows-host acceptance, which remains deferred

a complete source-current SDK qualification and native Windows-host acceptance are not claimed by this policy
