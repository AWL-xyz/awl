use Sort.aw as sort;
func error[i64] :: buffer:i64, message:text {
    @p size: buffer.writetext(buffer, 0, message);
    if size >= 0 {
        @p offset: 0;
        while offset < size {
            @p n: stderr.write(buffer, offset, size - offset);
            if n <= 0 { return 3; };
            offset: offset + n;
        };
    };
    return 2;
};
func add[bool] :: @b rows[text], buffer:i64, start:i64, count:i64 {
    if vector.length(rows) == 32768 { return false; };
    return vector.push(rows, buffer.text(buffer, start, count));
};
func main[i64] {
    @p buffer: buffer.new(1048577);
    if buffer == 0 { return 9; };
    defer buffer.free(buffer);
    @p unique: false;
    if arg.count() > 0 {
        if arg.count() != 1 or not arg.textvalid(0) { return error(buffer, "ksort: usage: ksort [--unique]\n"); };
        if arg.text(0) != "--unique" { return error(buffer, "ksort: usage: ksort [--unique]\n"); };
        unique: true;
    };
    @p total: 0;
    @p done: false;
    while not done {
        @p n: stdin.read(buffer, total, 1048577 - total);
        if n < 0 { return error(buffer, "ksort: input error\n"); };
        if n == 0 { done: true; };
        total: total + n;
        if total > 1048576 { return error(buffer, "ksort: input exceeds 1 MiB\n"); };
    };
    if not buffer.textvalid(buffer, 0, total) { return error(buffer, "ksort: input must be utf-8\n"); };
    @s rows vector<text>: vector.new<text>(0);
    if not vector.valid(rows) { return 9; };
    @p start: 0;
    while start < total {
        @p endline: buffer.findbyte(buffer, start, total - start, 10u8);
        if endline < 0 { endline: total; };
        if not add(rows, buffer, start, endline - start) { return error(buffer, "ksort: allocation failure or more than 32768 lines\n"); };
        start: endline + 1;
    };
    if not sort.stable(rows) { return 9; };
    -- Each row is an independent text copy. Reuse the input buffer: even with
    -- the final LF added, the output is at most one byte larger than the input.
    @p size: 0;
    @p count: vector.length(rows);
    @p index: 0;
    @p previous: "";
    while index < count {
        @p value: vector.get(rows, index);
        if not unique or index == 0 or value != previous {
            @p bytes: buffer.writetext(buffer, size, value);
            if bytes < 0 { return 3; };
            size: size + bytes;
            buffer.set(buffer, size, 10u8);
            size: size + 1;
        };
        previous: value;
        index: index + 1;
    };
    @p sent: 0;
    while sent < size {
        @p n: stdout.write(buffer, sent, size - sent);
        if n <= 0 { return 3; };
        sent: sent + n;
    };
    return 0;
};
