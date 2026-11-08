use Http.aw as http;
use TextMap.aw as textmap;
use Journal.aw as journal;
use Json.aw as json;
func error :: connection:i64, buffer:i64, status:i64 {
    http.respond(connection, buffer, status, "{\"error\":" + string.from_i64(status) + "}\n", "GET, PUT, DELETE");
};
func handle :: connection:i64, buffer:i64, prefix:text, revision:i64, @b pairs[text]: i64 {
    defer tcp_close(connection);
    @s input vector<text>: vector.new<text>(0);
    if not vector.valid(input) { return -1; };
    @p status: http.receive(connection, buffer, input);
    if status != 0 { error(connection, buffer, status); return revision; };
    @p method: vector.get(input, 0);
    @p path: vector.get(input, 1);
    @p value: vector.get(input, 2);
    if path == "/health" {
        if method != "GET" { http.respond(connection, buffer, 405, "{\"error\":405}\n", "GET"); return revision; };
        http.respond(connection, buffer, 200, "{\"status\":\"ok\",\"keys\":" + string.from_i64(vector.length(pairs) / 2) + ",\"revision\":" + string.from_i64(revision) + "}\n", "GET");
        return revision;
    };
    if string.bytes(path) < 4 { error(connection, buffer, 404); return revision; };
    if string.slice(path, 0, 4) != "/kv/" { error(connection, buffer, 404); return revision; };
    @p key: string.slice(path, 4, string.length(path) - 4);
    if not journal.valid_key(key) { error(connection, buffer, 400); return revision; };
    @p found: textmap.find(pairs, key);
    if method == "GET" {
        if found < 0 { error(connection, buffer, 404); return revision; };
        @s encoded vector<text>: vector.new<text>(1);
        if not vector.valid(encoded) { return -1; };
        if not json.quote(vector.get(pairs, found), encoded) { error(connection, buffer, 503); return revision; };
        http.respond(connection, buffer, 200, "{\"key\":\"" + key + "\",\"value\":" + vector.get(encoded, 0) + ",\"revision\":" + string.from_i64(revision) + "}\n", "GET, PUT, DELETE");
        return revision;
    };
    if method == "DELETE" and found < 0 { error(connection, buffer, 404); return revision; };
    if revision == 256 { error(connection, buffer, 507); return revision; };
    if method == "PUT" and found < 0 {
        if vector.length(pairs) == 256 { error(connection, buffer, 507); return revision; };
        if not vector.reserve(pairs, vector.length(pairs) + 2) { error(connection, buffer, 503); return revision; };
    };
    @p operation: 1;
    if method == "DELETE" { operation: 2; };
    if not journal.append(prefix, revision + 1, operation, key, value, buffer) {
        error(connection, buffer, 503);
        return -1;
    };
    @p body: "";
    if method == "PUT" {
        if not textmap.put(pairs, key, value) { error(connection, buffer, 500); return -1; };
        status: 200;
        if found < 0 { status: 201; };
        body: "{\"stored\":\"" + key + "\",\"revision\":" + string.from_i64(revision + 1) + "}\n";
    } else {
        if not textmap.remove(pairs, key) { error(connection, buffer, 500); return -1; };
        status: 200;
        body: "{\"deleted\":\"" + key + "\",\"revision\":" + string.from_i64(revision + 1) + "}\n";
    };
    http.respond(connection, buffer, status, body, "GET, PUT, DELETE");
    return revision + 1;
};
func main: i64 {
    if arg_count() < 1 or arg_count() > 3 { return 2; };
    if not arg_text_valid(0) { return 2; };
    @p prefix: arg_text(0);
    if string.bytes(prefix) == 0 or string.bytes(prefix) > 3900 { return 2; };
    @p port: 0;
    @p maximum: 128;
    if arg_count() > 1 {
        if not arg_i64_valid(1) { return 2; };
        port: arg_i64(1);
    };
    if arg_count() > 2 {
        if not arg_i64_valid(2) { return 2; };
        maximum: arg_i64(2);
    };
    if maximum < 1 or maximum > 256 { return 2; };
    @p buffer: buffer_new(16384);
    if buffer == 0 { return 9; };
    defer buffer_free(buffer);
    @s pairs vector<text>: vector.new<text>(0);
    if not vector.valid(pairs) { return 9; };
    @p revision: journal.load(prefix, buffer, pairs);
    if revision < 0 { print(revision); return 4; };
    @p listener: tcp_listen_loopback(port, 16);
    if listener < 0 { print(listener); return 3; };
    defer tcp_close(listener);
    print(tcp_port(listener));
    if stdout_flush() != 0 { return 3; };
    @p count: 0;
    while count < maximum {
        @p connection: tcp_accept(listener, 5000);
        if connection == -10 { return 0; };
        if connection < 0 { return 3; };
        revision: handle(connection, buffer, prefix, revision, pairs);
        if revision < 0 { return 5; };
        count: count + 1;
    };
    return 0;
};
