use Http.aw as http;
func serve :: connection:i64, buffer:i64, counter:i64: i64 {
    defer tcp_close(connection);
    @p route: http.request(connection, buffer);
    @p next: counter;
    @p status: 200;
    @p allow: "GET, POST";
    @p body: "{\"status\":\"ok\"}\n";
    if route == 2 or route == 3 {
        if route == 3 { next: counter + 1; };
        body: "{\"counter\":" + string.from_i64(next) + "}\n";
    } else {
        if route != 1 {
            status: route;
            if route == 4 { status: 405; allow: "GET"; };
            body: "{\"error\":" + string.from_i64(status) + "}\n";
        };
    };
    http.respond(connection, buffer, status, body, allow);
    return next;
};
func main: i64 {
    if arg_count() > 2 { return 2; };
    @p port: 0;
    @p maximum: 32;
    if arg_count() > 0 {
        if not arg_i64_valid(0) { return 2; };
        port: arg_i64(0);
    };
    if arg_count() > 1 {
        if not arg_i64_valid(1) { return 2; };
        maximum: arg_i64(1);
    };
    if maximum < 1 or maximum > 256 { return 2; };
    @p listener: tcp_listen_loopback(port, 16);
    if listener < 0 { print(listener); return 3; };
    defer tcp_close(listener);
    @p buffer: buffer_new(8192);
    if buffer == 0 { return 9; };
    defer buffer_free(buffer);
    print(tcp_port(listener));
    if stdout_flush() != 0 { return 3; };
    @p counter: 0;
    @p handled: 0;
    while handled < maximum {
        @p connection: tcp_accept(listener, 5000);
        if connection == -10 { return 0; };
        if connection < 0 { return 4; };
        counter: serve(connection, buffer, counter);
        handled: handled + 1;
    };
    return 0;
};
