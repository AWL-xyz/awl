use Http.aw as http;
use Store.aw as store;
use Rules.aw as rules;
use vendor/Json.aw as json;
use Assets.aw as assets;
func error :: connection:i64, buffer:i64, status:i64 {
    http.respond(connection, buffer, status, "{\"error\":" + string.fromi64(status) + "}\n", "application/json", "Allow: GET, PUT, DELETE\r\n");
};
func snapshot[i64] :: connection:i64, buffer:i64, status:i64, uncertain:bool, download:bool, @b rows[text], @b meta[i64] {
    @s output vector<text>: vector.new<text>(1);
    if not vector.valid(output) { error(connection, buffer, 503); return 0; };
    if not store.encode(rows, meta, output) { error(connection, buffer, 503); return 0; };
    @p durability: "confirmed";
    if uncertain { durability: "uncertain"; };
    @p headers: "ETag: \"v" + string.fromi64(vector.get(meta, 0)) + "\"\r\nX-Awl-Durability: " + durability + "\r\n";
    if download { headers: headers + "Content-Disposition: attachment; filename=\"awl-board.json\"\r\n"; };
    http.respond(connection, buffer, status, vector.get(output, 0), "application/json; charset=utf-8", headers);
    return 0;
};
func handle[i64] :: connection:i64, buffer:i64, directory:text, port:i64, @b rows[text], @b meta[i64] {
    defer tcp.close(connection);
    @s input vector<text>: vector.new<text>(0);
    if not vector.valid(input) { return -1; };
    @p result: http.receive(connection, buffer, input);
    if result != 0 { error(connection, buffer, result); return 0; };
    @p host: vector.get(input, 3);
    @p suffix: ":" + string.fromi64(port);
    if host != "127.0.0.1" + suffix and host != "localhost" + suffix { error(connection, buffer, 403); return 0; };
    @p method: vector.get(input, 0);
    @p path: vector.get(input, 1);
    if path == "/" {
        if method != "GET" { error(connection, buffer, 405); return 0; };
        http.respond(connection, buffer, 200, assets.page(), "text/html; charset=utf-8", "Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; worker-src blob:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'\r\n");
        return 0;
    };
    if method == "GET" {
        if path != "/api/tasks" and path != "/api/export" { error(connection, buffer, 404); return 0; };
        snapshot(connection, buffer, 200, false, path == "/api/export", rows, meta);
        return 0;
    };
    if string.bytes(path) < 12 { error(connection, buffer, 404); return 0; };
    if string.slice(path, 0, 11) != "/api/tasks/" { error(connection, buffer, 404); return 0; };
    if vector.get(input, 4) != "http://" + host or vector.get(input, 6) == "cross-site" { error(connection, buffer, 403); return 0; };
    if vector.get(input, 5) == "" { error(connection, buffer, 428); return 0; };
    if vector.get(input, 5) != "\"v" + string.fromi64(vector.get(meta, 0)) + "\"" { error(connection, buffer, 412); return 0; };
    @p id: string.slice(path, 11, string.length(path) - 11);
    @p number: rules.integer(id);
    if number < 1 { error(connection, buffer, 400); return 0; };
    @p found: -1;
    @p i: 0;
    while i < vector.length(rows) {
        if vector.get(rows, i) == id { found: i; };
        i: i + 4;
    };
    @s tokens vector<text>: vector.new<text>(0);
    @s parsed vector<i64>: vector.new<i64>(0);
    @p title: "";
    @p note: "";
    @p state: "";
    if not vector.valid(tokens) or not vector.valid(parsed) { error(connection, buffer, 503); return 0; };
    if method == "PUT" {
        if not json.parse(vector.get(input, 2), tokens, parsed) { error(connection, buffer, 422); return 0; };
        @p a: store.field("/title", 5, tokens, parsed);
        @p b: store.field("/note", 5, tokens, parsed);
        @p c: store.field("/status", 5, tokens, parsed);
        if vector.length(tokens) != 8 or a < 0 or b < 0 or c < 0 { error(connection, buffer, 422); return 0; };
        title: vector.get(tokens, a);
        note: vector.get(tokens, b);
        state: vector.get(tokens, c);
        if not rules.valid_title(title) or not rules.valid_note(note) or not rules.valid_status(state) { error(connection, buffer, 422); return 0; };
        if found < 0 {
            if number != vector.get(meta, 1) { error(connection, buffer, 404); return 0; };
            if vector.length(rows) == 128 { error(connection, buffer, 507); return 0; };
        } else {
            if title == vector.get(rows, found + 1) and note == vector.get(rows, found + 2) and state == vector.get(rows, found + 3) {
                snapshot(connection, buffer, 200, false, false, rows, meta);
                return 0;
            };
        };
    } else {
        if found < 0 { error(connection, buffer, 404); return 0; };
    };
    if vector.get(meta, 0) == 10000 or vector.get(meta, 1) == 1000000 { error(connection, buffer, 507); return 0; };
    @s candidate vector<text>: vector.new<text>(128);
    @s next vector<i64>: vector.new<i64>(2);
    @s encoded vector<text>: vector.new<text>(1);
    if not vector.valid(candidate) or not vector.valid(next) or not vector.valid(encoded) { error(connection, buffer, 503); return 0; };
    vector.push(next, vector.get(meta, 0) + 1);
    vector.push(next, vector.get(meta, 1));
    i: 0;
    while i < vector.length(rows) {
        if i != found {
            vector.push(candidate, vector.get(rows, i));
            vector.push(candidate, vector.get(rows, i + 1));
            vector.push(candidate, vector.get(rows, i + 2));
            vector.push(candidate, vector.get(rows, i + 3));
        } else {
            if method == "PUT" {
                vector.push(candidate, id);
                vector.push(candidate, title);
                vector.push(candidate, note);
                vector.push(candidate, state);
            };
        };
        i: i + 4;
    };
    if found < 0 {
        vector.push(candidate, id);
        vector.push(candidate, title);
        vector.push(candidate, note);
        vector.push(candidate, state);
        vector.set(next, 1, vector.get(next, 1) + 1);
    };
    if not store.encode(candidate, next, encoded) { error(connection, buffer, 503); return 0; };
    result: store.save(directory, vector.get(encoded, 0), buffer);
    if result < 0 { error(connection, buffer, 503); return 0; };
    if not vector.reserve(rows, 128) { return -1; };
    vector.clear(rows);
    i: 0;
    while i < vector.length(candidate) {
        vector.push(rows, vector.get(candidate, i));
        i: i + 1;
    };
    vector.set(meta, 0, vector.get(next, 0));
    vector.set(meta, 1, vector.get(next, 1));
    @p status: 200;
    if found < 0 { status: 201; };
    if result == 1 { status: 202; };
    snapshot(connection, buffer, status, result == 1, false, rows, meta);
    return result;
};
func main[i64] {
    if arg.count() < 1 or arg.count() > 3 { print("usage: awl-board DATA_DIRECTORY [PORT] [REQUEST_LIMIT]"); return 2; };
    if not arg.textvalid(0) { return 2; };
    @p directory: arg.text(0);
    if string.bytes(directory) == 0 or string.bytes(directory) > 3800 { return 2; };
    @p port: 0;
    @p maximum: 256;
    if arg.count() > 1 {
        if not arg.i64valid(1) { return 2; };
        port: arg.i64(1);
    };
    if arg.count() > 2 {
        if not arg.i64valid(2) { return 2; };
        maximum: arg.i64(2);
    };
    if port < 0 or port > 65535 or maximum < 1 or maximum > 256 { return 2; };
    @p buffer: buffer.new(131072);
    if buffer == 0 { return 9; };
    defer buffer.free(buffer);
    @s rows vector<text>: vector.new<text>(128);
    @s meta vector<i64>: vector.new<i64>(2);
    if not vector.valid(rows) or not vector.valid(meta) { return 9; };
    vector.push(meta, 0);
    vector.push(meta, 1);
    if not store.load(directory, buffer, rows, meta) { print("invalid or unreadable board.json"); return 4; };
    @p listener: tcp.listenloopback(port, 16);
    if listener < 0 { print("listen failed"); return 3; };
    defer tcp.close(listener);
    port: tcp.port(listener);
    print(port);
    if stdout.flush() != 0 { return 3; };
    @p count: 0;
    @p idle: clock.millis() + 600000;
    while count < maximum and clock.millis() < idle {
        @p connection: tcp.accept(listener, 1000);
        if connection != -10 {
            if connection < 0 { return 3; };
            @p result: handle(connection, buffer, directory, port, rows, meta);
            if result != 0 { return 6; };
            count: count + 1;
            idle: clock.millis() + 600000;
        };
    };
    return 0;
};
