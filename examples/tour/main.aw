-- main.aw, the whole next-syntax tour, one program, everything it does
--
-- quick grammar card
--   func name :: param, param: Result { ... };     parameters, result annotation
--   func name[Result] { ... };                     no parameters
--   func name :: param { ... };                    result omitted means unit
--   @p name: value;                                private binding, inferred type
--   @p name type: value;                           private binding, explicit type
--   @s name type: value;                           scoped owner, released at scope exit
--   name: value;                                   assignment, same colon, no `=`
--   if cond { ... } elseif cond { ... } else { ... };
--   while cond { ... };
--   match value then case Union.Variant(bind) then ...; end;
--   enum Name Variant(field:type); Other(); end;
--   struct Name { field:type; other:i64; };            value type, fields mutate with `:`
--   Name(1,2)                                         constructor, same shape as an enum variant
--   for i in 0..n { ... };                            range loop, i is a fresh i64
--   for v in values { ... };                          iterate a vector, view, map, set or array
--   break; continue;                                  loop control, both run scope cleanup
--   map<K,V> set<T>                                   hash containers, @s owned, for yields keys
--   use File.aw as alias;   exports{ @r x: 1; @w y: 0; @r func f ... };  @r enum E ... end;
--   func f :: @b v[i64]      borrowed vector, @o b:spool owned resource
--   func f: @o spool  owned result, caller moves it into an owner
--   func f :: @m v:Name       mutable borrow, the callee edits the caller's struct
--   defer expr;              runs at scope exit, move x transfers an owner
--   -- line comment, statements end with `;`, every brace block and chain too
-- reserved words cannot be names, that covers func enum match use exports if elseif else while
-- then end return defer move and or not true false pi tau, the integer widths, f64,
-- bool unit string text spool vector view int_vector and @p @s @b @o @r @w
-- absent on purpose, no structs yet, no closures, no exceptions, no classes,
-- generics exist only as vector<T>/view<T>, integer types never convert implicitly

use Library.aw as lib;

-- private top-level state, visible to this file only
@p total_runs: 0;

-- a private enum of this file, exported enums live inside exports{...}
enum Report Ok(message:string); Warn(message:string); None(); end;

-- a plain value type, nested structs and enum fields are both fine
enum Badge Level(name:string); None(); end;
struct Row {
    badge:Badge;
    weight:i64;
};
enum Event Item(name:string,enabled:bool); Ping(); end;   -- several payload fields per variant

-- borrowed vector parameter, borrowed view parameter, owned resource parameter
func summarise[text] :: @b values[i64], window:view<i64>, label:text {
    @p sum: 0;
    @p i: 0;
    while i < vector.length(values) {
        sum: sum + vector.get(values,i);
        i: i + 1;
    };
    if view.valid(window) {
        sum: sum + view.get(window,0);
    };
    return label.." sum="..sum;
};

-- borrowed resource parameter, the caller keeps ownership
func log :: @b sink:spool, message:text {
    spool.append(sink,message);
};

-- owned parameter, the callee takes the resource and releases it
func drain[i64] :: @o scratch:spool {
    @p n: spool.length(scratch);
    return n;
};

-- owned result, caller must move it into an owner
func make_builder[@o spool] :: slots:i64 {
    @s b spool: spool.new(slots);
    spool.append(b,"owned ");
    spool.i64(b,2026);
    return move b;
};

-- unit result, no annotation at all
func announce :: message:text {
    print("announce "..message);
};

-- mutable borrow, no copy and no result, the caller's struct changes in place
func grow :: @m row:Row, by:i64 {
    row.weight: row.weight + by;
};

func classify[Report] :: n:i64 {
    if n < 0 {
        return Report.Warn("negative");
    } elseif n == 0 {
        return Report.None();
    };
    return Report.Ok("positive");
};

func main[i64] {
    total_runs: total_runs + 1;

    -- integers, every width, explicit suffixes, checked arithmetic
    @p tiny i8: -128i8;
    @p small u8: 255u8;
    @p medium i16: -32768i16;
    @p portish u16: 65535u16;
    @p wide i32: -2147483648i32;
    @p wider u32: 4294967295u32;
    @p big i64: -9223372036854775808;
    @p biggest u64: 18446744073709551615u64;
    @p plain: 42;                                  -- defaults to i64
    print(tiny); print(small); print(medium); print(portish);
    print(wide); print(wider); print(big); print(biggest); print(plain);

    -- conversions are explicit, i64(...) u8(...) f64(...), out of range traps
    @p narrowed: u8(i64(200));
    @p widened: i64(medium);
    print(narrowed); print(widened);
    print(i64(7) / 2);                             -- 3, integer division truncates
    print(i64(7) % 2);                             -- 1
    print(i64(7) * 2 + 1);                         -- precedence: 15
    print(lib.limit - 3);                          -- exported @r variable, read only

    -- f64 literals, constants and math
    @p ratio: 2.5;
    @p area: pi * ratio * ratio;
    print(area);
    print(tau);
    print(sqrt(81.0));
    print(sin(pi / 2.0));
    print(cos(0.0));
    print(atan2(1.0,1.0));
    print(f64(plain) / 4.0);                       -- explicit int to float

    -- booleans and comparisons
    @p ready: true;
    @p quiet: false;
    print(ready and not quiet);
    print(ready or quiet);
    print(plain == 42);
    print(plain != 42);
    print(plain <= 42);

    -- strings, interpolation, concatenation, escapes, UTF8 helpers
    @p name: "owl";
    @p count: 3;
    print("hello ${name}");                        -- ${identifier} inserts a scalar
    print("count "..count.." of "..lib.limit);     -- .. joins any scalars and text
    print("literal \${name} stays put");
    print("tab\tnewline\nescaped quote \" ok");
    print(string.length("héllo"));                 -- unicode scalars
    print(string.bytes("héllo"));                  -- utf8 bytes
    print(string.slice("héllo",1,3));              -- start, count
    print(string.codepoint("é",0));
    print(string.from_codepoint(233u32));
    print(string.byte_at("é",1));
    print(string.from_i64(big));
    print(string.from_u64(biggest));
    print(string.compare("a","b"));
    print(name == "owl");                          -- text equality
    print("a" + "b");                              -- `+` also joins text
    print(string.bytes("a\0b"));                  -- embedded NUL is valid text data

    -- fixed size arrays, declared and indexed with [], length is part of the type
    @p grid [i64;3]: [10,20,30];
    @p zeros [i64;2]: [0;2];                       -- [value;count] repeats the value
    zeros[0]: grid[2];
    print(grid[0] + grid[1] + grid[2]);
    print(zeros[0] + zeros[1]);

    -- generic vectors, element type inside <>, growth, insertion, copying slices
    @s values vector<i64>: vector.new<i64>(2);
    vector.push(values,7);
    vector.push(values,8);
    vector.push(values,9);
    vector.set(values,0,6);
    vector.insert(values,1,5);
    print(vector.length(values));
    print(vector.get(values,0));
    print(vector.capacity(values));
    print(vector.valid(values));
    print(vector.reserve(values,16));
    vector.swap(values,0,3);
    vector.remove(values,2);
    vector.truncate(values,3);
    print(vector.pop(values));
    print(vector.length(values));
    @s words vector<text>: vector.new<text>(2);
    vector.push(words,"alpha");
    vector.push(words,"beta");
    @s copy vector<text>: vector.slice(words,0,1); -- slice of a vector is a new owner
    print(vector.get(copy,0));
    vector.clear(words);
    print(vector.length(words));
    print(summarise(values,vector.view(values,0,2),"vector"));

    -- read only views, 32 byte descriptors, no allocation, no owner retained
    @p head view<i64>: vector.view(values,0,2);
    print(view.length(head));
    print(view.get(head,0));
    print(view.valid(head));
    @p tail view<i64>: view.slice(head,1,1);
    print(view.get(tail,0));

    -- text builders, append numbers and text, snapshot copies out immutable text
    @s report spool: spool.new(16);
    spool.append(report,"runs=");
    spool.i64(report,total_runs);
    spool.append(report," ");
    spool.u64(report,biggest);
    spool.codepoint(report,233u32);
    print(spool.length(report));
    print(spool.bytes(report));
    print(spool.capacity(report) >= spool.bytes(report));
    print(spool.snapshot(report));
    print(spool.valid(report));
    log(report," logged");                         -- borrowed builder, no move needed
    print(spool.snapshot(report));
    @s scratch spool: make_builder(8);
    print(spool.snapshot(scratch));
    @p drained: drain(move scratch);               -- move in a direct call, the callee owns it
    print(drained);
    spool.clear(report);
    print(spool.length(report));

    -- legacy growable i64 container, kept for older sources
    @s numbers int_vector: int_vector.new(2);
    int_vector.push(numbers,11);
    int_vector.push(numbers,12);
    int_vector.set(numbers,0,10);
    print(int_vector.length(numbers));
    print(int_vector.get(numbers,0) + int_vector.get(numbers,1));
    int_vector.insert(numbers,0,9);
    print(int_vector.remove(numbers,1));
    print(int_vector.pop(numbers));
    int_vector.clear(numbers);
    print(int_vector.length(numbers));

    -- byte buffers, the bridge between raw bytes and strict text
    @p bytes: buffer_new(32);
    buffer_write_text(bytes,0,"café");
    print(buffer_size(bytes));
    print(buffer_text(bytes,0,5));
    print(buffer_text_valid(bytes,0,5));
    buffer_set(bytes,0,u8(67));
    print(buffer_text(bytes,0,5));
    print(buffer_get(bytes,0));
    buffer_free(bytes);

    -- regular files, mode 0 read, 1 create new, 2 create or truncate, then atomic replace
    @p payload: buffer_new(32);
    buffer_write_text(payload,0,"tour payload");
    @p file: file_open("tour-scratch.txt",2);
    if file_valid(file) {
        print(file_write(file,payload,0,12));
        print(file_flush(file));
        print(file_size(file));
        print(file_close(file));
    } else {
        print(-1);
    };
    print(file_replace(".","tour-scratch.txt","tour-final.txt"));  -- atomic publish
    @p reopened: file_open("tour-final.txt",0);
    @p readback: buffer_new(32);
    if file_valid(reopened) {
        print(file_read(reopened,readback,0,12));
        print(buffer_text(readback,0,12));
        print(file_seek(reopened,0));
        print(file_size(reopened));
        print(file_close(reopened));
    } else {
        print(-1);
    };
    buffer_free(payload);
    buffer_free(readback);

    -- standard streams and the environment
    @p note: buffer_new(16);
    buffer_write_text(note,0,"tour note");
    print(stderr_write(note,0,9));                 -- writes to stderr, returns the count
    print(stdout_write(note,0,0));                 -- zero byte probe, count 0
    print(stdout_flush());
    print(stderr_flush());
    print(env_size("PATH") > 0);
    @p envbuf: buffer_new(8);
    @p envbytes: env_size("PATH");
    if envbytes >= 8 {
        print(env_read("PATH",envbuf,0,8));        -- -5 means the value did not fit the buffer
    } else {
        print(-1);
    };
    buffer_free(envbuf);
    buffer_free(note);
    -- stdin_read(note,0,16) would block without input, it reads stdin bytes into a buffer
    print(arg_count());
    print(arg_text_valid(0));
    print(arg_i64_valid(0));
    if arg_count() > 0 {
        print(arg_text(0));                        -- strict UTF8 copy of argv[1]
        print(arg_i64(0));                         -- strict integer argv[1]
    } else {
        print("no arguments");
    };

    -- synchronous subprocess capture, explicit argv, no shell, no PATH search
    @s out spool: spool.new(32);
    @s err spool: spool.new(32);
    @s argv vector<text>: vector.new<text>(1);
    vector.push(argv,"tour");
    print(process_capture("/bin/echo",vector.view(argv,0,1),out,err,5000));
    print(spool.snapshot(out));
    print(spool.bytes(err));

    -- loopback TCP listener, close straight away, tcp_accept/tcp_read/tcp_write need a live peer
    -- so they are exercised in examples/apps/kserve instead of a self-contained tour
    @p listener: tcp_listen_loopback(0,2);
    print(tcp_valid(listener));
    print(tcp_port(listener) > 0);
    print(tcp_close(listener));

    -- framebuffer window, headless hosts return 0 instead of a handle
    @p window: window_open(8,4);
    if window != 0 {
        window_set_title(window,"tour");
        window_set_pixel(window,0,0,16711680);
        print(window_width(window));
        print(window_height(window));
        print(window_present(window));
        print(window_poll(window));
        print(window_key(window));
        print(window_mouse_x(window));
        print(window_mouse_y(window));
        window_close(window);
    } else {
        print("no display");
    };

    -- clock and platform, monotonic milliseconds and a platform id
    @p started: clock_millis();
    sleep_millis(1);
    print(clock_millis() >= started);
    print(platform_kind());

    -- control flow, if/elseif/else, while, match on enums with payload binding
    @p step: 0;
    while step < 3 {
        if step == 0 {
            print("first");
        } elseif step == 1 {
            print("second");
        } else {
            print("last");
        };
        step: step + 1;
    };
    match classify(-1) then
        case Report.Ok(msg) then print(msg);
        case Report.Warn(msg) then print(msg);
        case Report.None() then print("none");
    end;
    match classify(4) then
        case Report.Ok(msg) then print(msg);
        case Report.Warn(msg) then print(msg);
        case Report.None() then print("none");
    end;
    match Event.Item("named",true) then
        case Event.Item(n,on) then print(n);        -- several binders, comma separated
        case Event.Ping() then print("ping");
    end;
    match classify(0) then
        case Report.Ok(_) then print("ok");
        case Report.Warn(_) then print("warn");
        case Report.None() then print("none");   -- `_` ignores a payload
    end;

    -- imported functions, imported enums, imported state, alias-qualified access
    print(lib.label());
    print(lib.version);
    print(lib.bump(2));
    lib.counter: lib.counter + 1;                  -- @w export, writable from here
    print(lib.counter);
    print(lib.call_count());
    match lib.grade(97) then
        case lib.Grade.Pass(score) then print(score);
        case lib.Grade.Fail(reason) then print(reason);
    end;
    match lib.nearest_ticket(-2) then
        case lib.Ticket.Id(number) then print(number);
        case lib.Ticket.None() then print("no ticket");
    end;
    @s import_values vector<i64>: vector.new<i64>(2);
    vector.push(import_values,4);
    vector.push(import_values,5);
    print(lib.total_of(import_values));
    announce(lib.label());

    -- structs, construction, field access, mutation and nested fields
    @p row Row: Row(Badge.Level("first"),3);
    print(row.weight);
    row.weight: row.weight + 2;
    print(row.weight);
    match row.badge then
        case Badge.Level(name) then print(name);
        case Badge.None() then print("none");
    end;
    grow(row,4);                                   -- @m borrows row, no copy back
    print(row.weight);

    -- for over a range, a collection, with break and continue
    @p range_total: 0;
    for i in 0..4 {
        range_total: range_total + i;
    };
    print(range_total);
    @p hits: 0;
    for item in values {
        if item == 5 { continue; };
        if item > 8 { break; };
        hits: hits + 1;
    };
    print(hits);
    @p sample [i64;3]: [2,5,9];
    @p sample_sum: 0;
    for number in sample {
        sample_sum: sample_sum + number;
    };
    print(sample_sum);

    -- hash containers, text keys and values, @s own the storage
    @s counts map<text,i64>: map.new<text,i64>(4);
    map.set(counts,"owl",1);
    map.set(counts,"cat",2);
    map.set(counts,"owl",map.get(counts,"owl") + 2);
    print(map.length(counts));
    print(map.get(counts,"owl"));
    print(map.remove(counts,"cat"));
    for key in counts {
        print(key);
    };
    @s marks set<i64>: set.new<i64>(2);
    print(set.add(marks,4));
    print(set.add(marks,4));
    print(set.length(marks));
    @p marks_copy vector<i64>: set.values(marks);
    print(vector.length(marks_copy));

    -- defer runs at scope exit, including every early return
    @p tracked: file_open("tour-final.txt",0);
    defer file_close(tracked);
    print(file_valid(tracked));

    print("tour complete");
    return 0;
};
