func equal[bool] :: buffer:i64, start:i64, count:i64, expected:text, folded:bool {
    if count != string.bytes(expected) { return false; };
    @p i: 0;
    while i < count {
        @p byte: i64(buffer.get(buffer, start + i));
        if folded and byte >= 65 and byte <= 90 { byte: byte + 32; };
        if byte != i64(string.byteat(expected, i)) { return false; };
        i: i + 1;
    };
    return true;
};
exports{
    @r func request[i64] :: connection:i64, buffer:i64 {
        @p count: 0;
        @p scan: 0;
        @p finish: 0;
        @p deadline: clock.millis() + 500;
        while finish == 0 {
            if count == 8192 { return 431; };
            @p remaining: deadline - clock.millis();
            if remaining <= 0 { return 408; };
            @p n: tcp.read(connection, buffer, count, 8192 - count, remaining);
            if n == -10 { return 408; };
            if n <= 0 { return 400; };
            count: count + n;
            while scan + 3 < count and finish == 0 {
                if buffer.get(buffer, scan) == 13u8 and buffer.get(buffer, scan + 1) == 10u8 and buffer.get(buffer, scan + 2) == 13u8 and buffer.get(buffer, scan + 3) == 10u8 { finish: scan + 4; };
                scan: scan + 1;
            };
        };
        @p i: 0;
        while i < finish {
            @p byte: buffer.get(buffer, i);
            if byte == 13u8 {
                if i + 1 >= finish { return 400; };
                if buffer.get(buffer, i + 1) != 10u8 { return 400; };
                i: i + 1;
            } else {
                if byte < 32u8 or byte > 126u8 { return 400; };
            };
            i: i + 1;
        };
        @p line: 0;
        while buffer.get(buffer, line) != 13u8 { line: line + 1; };
        @p method: 0;
        while method < line and buffer.get(buffer, method) != 32u8 { method: method + 1; };
        if method == 0 or method == line { return 400; };
        @p path: method + 1;
        @p stop: path;
        while stop < line and buffer.get(buffer, stop) != 32u8 { stop: stop + 1; };
        if stop == path or stop == line or stop - path > 256 { return 400; };
        if not equal(buffer, stop + 1, line - stop - 1, "HTTP/1.1", false) { return 400; };
        @p hosts: 0;
        @p headers: 0;
        @p lengths: 0;
        @p start: line + 2;
        while start < finish - 2 {
            headers: headers + 1;
            if headers > 32 { return 431; };
            @p endline: start;
            while buffer.get(buffer, endline) != 13u8 { endline: endline + 1; };
            @p colon: start;
            while colon < endline and buffer.get(buffer, colon) != 58u8 {
                @p byte: buffer.get(buffer, colon);
                if not ((byte >= 65u8 and byte <= 90u8) or (byte >= 97u8 and byte <= 122u8) or (byte >= 48u8 and byte <= 57u8) or byte == 45u8) { return 400; };
                colon: colon + 1;
            };
            if colon == start or colon == endline or colon - start > 64 { return 400; };
            @p value: colon + 1;
            while value < endline and buffer.get(buffer, value) == 32u8 { value: value + 1; };
            @p last: endline;
            while last > value and buffer.get(buffer, last - 1) == 32u8 { last: last - 1; };
            if equal(buffer, start, colon - start, "host", true) {
                hosts: hosts + 1;
                if last == value { return 400; };
            };
            if equal(buffer, start, colon - start, "transfer-encoding", true) { return 400; };
            if equal(buffer, start, colon - start, "content-length", true) {
                lengths: lengths + 1;
                if lengths > 1 or not equal(buffer, value, last - value, "0", false) { return 400; };
            };
            start: endline + 2;
        };
        if hosts != 1 { return 400; };
        @p get: equal(buffer, 0, method, "GET", false);
        @p post: equal(buffer, 0, method, "POST", false);
        if equal(buffer, path, stop - path, "/health", false) {
            if get { return 1; };
            return 4;
        };
        if equal(buffer, path, stop - path, "/counter", false) {
            if get { return 2; };
            if post { return 3; };
            return 405;
        };
        return 404;
    };
    @r func respond[bool] :: connection:i64, buffer:i64, status:i64, body:text, allow:text {
        @p reason: "OK";
        if status == 400 { reason: "Bad Request"; };
        if status == 404 { reason: "Not Found"; };
        if status == 405 { reason: "Method Not Allowed"; };
        if status == 408 { reason: "Request Timeout"; };
        if status == 431 { reason: "Request Header Fields Too Large"; };
        @p extra: "";
        if status == 405 { extra: "Allow: " + allow + "\r\n"; };
        @p response: "HTTP/1.1 " + string.fromi64(status) + " " + reason + "\r\nContent-Type: application/json\r\nConnection: close\r\n" + extra + "Content-Length: " + string.fromi64(string.bytes(body)) + "\r\n\r\n" + body;
        @p size: buffer.writetext(buffer, 0, response);
        if size < 0 { return false; };
        @p offset: 0;
        @p deadline: clock.millis() + 500;
        while offset < size {
            @p remaining: deadline - clock.millis();
            if remaining <= 0 { return false; };
            @p n: tcp.write(connection, buffer, offset, size - offset, remaining);
            if n <= 0 { return false; };
            offset: offset + n;
        };
        return true;
    };
};
