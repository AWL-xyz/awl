# built-in API

Awl is the language, the source syntax is Aesop, grouped built-ins use `namespace.method(...)`, method names are lowercase and contain no underscores

old underscore spellings are rejected by the checker with `E102`, the editor subset reports unsupported groups plainly rather than pretending to emulate the native compiler

## conversions and type tests

every numeric type can be used as a namespace with `convert`, all primitive types can be used with `match`, `isnum` is a global type test

```text
func main[i64] {
    @p whole: i64.convert(1.5);
    @p ratio: f64.convert(whole);
    print(whole);
    print(ratio);
    print(isnum(ratio));
    print(i64.match(whole));
    print(f64.match(ratio));
    print(text.match("hello"));
    return 0;
};
```

| expression | result | meaning |
| :--- | :--- | :--- |
| `i64.convert(x)` and other integer targets | target integer | checked integer-to-integer conversion, or float-to-integer truncation toward zero with NaN to `0` and saturation at the target bounds |
| `f64.convert(x)` | `f64` | integer or float to `f64`, integer literals can also be coerced in explicit `f64` contexts |
| `isnum(x)` | `bool` | true when the static operand type is an integer or `f64` |
| `i64.match(x)` | `bool` | true when the static operand type is exactly `i64` |
| `f64.match(x)`, `bool.match(x)`, `text.match(x)`, `unit.match(x)` | `bool` | exact static type checks, `text` matches the compiler's `string` representation |

mixed integer and `f64` arithmetic remains strict, `i64 * f64` asks for `f64.convert(...)` or an integer `convert(...)` explicitly, there is no silent narrowing or widening

type tests are static predicates, they do not introduce a dynamic `any` type, the operand is evaluated once before the constant result is produced

## grouped calls

| group | surface examples |
| :--- | :--- |
| arrays | `array.length(a)` |
| arguments | `arg.count()`, `arg.text(i)`, `arg.i64(i)`, `arg.textvalid(i)`, `arg.i64valid(i)` |
| buffers | `buffer.new(n)`, `buffer.size(b)`, `buffer.get(b,i)`, `buffer.set(b,i,v)`, `buffer.free(b)`, `buffer.text(b,i,n)`, `buffer.textvalid(b,i,n)`, `buffer.writetext(b,i,s)` |
| clocks | `clock.millis()`, `clock.wall()`, `clock.sleep(ms)` |
| environment | `env.size(name)`, `env.read(name,b,i,n)` |
| files | `file.open(path,mode)`, `file.read(f,b,i,n)`, `file.write(f,b,i,n)`, `file.close(f)`, `file.size(f)`, `file.seek(f,i)`, `file.flush(f)`, `file.valid(f)`, `file.replace(dir,tmp,target)` |
| processes | `process.capture(argv,view,out,err,deadline)` |
| platform | `platform.kind()` |
| streams | `stdin.read(b,i,n)`, `stdout.write(b,i,n)`, `stdout.flush()`, `stderr.write(b,i,n)`, `stderr.flush()` |
| strings | `string.length(s)`, `string.bytes(s)`, `string.slice(s,i,n)`, `string.codepoint(s,i)`, `string.byteat(s,i)`, `string.fromcodepoint(c)`, `string.fromi64(v)`, `string.fromu64(v)`, `string.compare(a,b)`, `string.find(a,b)`, `string.contains(a,b)`, `string.startswith(a,b)`, `string.endswith(a,b)`, `string.replace(a,b,c)` |
| TCP | `tcp.listenloopback(port,backlog)`, `tcp.accept(h,timeout)`, `tcp.read(h,b,i,n,timeout)`, `tcp.write(h,b,i,n,timeout)`, `tcp.close(h)`, `tcp.port(h)`, `tcp.valid(h)` |
| typed vectors | `vector.new<T>(capacity)`, `vector.length(v)`, `vector.get(v,i)`, `vector.push(v,x)`, `vector.free(v)`, `vector.view(v,i,n)`, `vector.slice(v,i,n)` |
| views | `view.valid(v)`, `view.length(v)`, `view.get(v,i)`, `view.slice(v,i,n)` |
| int vectors | `intvector.new(n)`, `intvector.length(v)`, `intvector.get(v,i)`, `intvector.push(v,x)`, `intvector.free(v)` |
| builders | `spool.new(n)`, `spool.append(b,s)`, `spool.i64(b,x)`, `spool.u64(b,x)`, `spool.codepoint(b,c)`, `spool.snapshot(b)`, `spool.print(b)`, `spool.free(b)` |
| maps/sets | `map.new<K,V>(n)`, `map.get(m,k)`, `map.set(m,k,v)`, `set.new<T>(n)`, `set.add(s,x)` |
| windows | `window.open(w,h)`, `window.title(h,s)`, `window.pixel(h,x,y,rgb)`, `window.present(h)`, `window.width(h)`, `window.height(h)`, `window.poll(h)`, `window.key(h)`, `window.mousex(h)`, `window.mousey(h)`, `window.close(h)` |

the complete signature table is `compiler/native/platform-signatures.inc`, the compiler's independent verifier checks every signature and rejects forged result metadata

## evidence

source-current native and sanitizer checks live in `tests/aesop.py`, `tests/aesop_time.py` and `compiler/test_native.py`, the bundled editor subset is checked by `tests/awl_editor.py`

older reports and API notes are preserved under `tests/archive/` and `docs/archive/`, they are historical evidence and are not current API documentation
