use Sort.aw as sort;
func error[i64] :: buffer:i64, message:text {
    @p size: buffer_write_text(buffer, 0, message);
    if size >= 0 {
        @p offset: 0;
        while offset < size {
            @p n: stderr_write(buffer, offset, size - offset);
            if n <= 0 { return 3; };
            offset: offset + n;
        };
    };
    return 2;
};
func add[bool] :: @b rows[text], buffer:i64, start:i64, count:i64 {
    if vector.length(rows) == 32768 { return false; };
    return vector.push(rows, buffer_text(buffer, start, count));
};
func main[i64] {
    @p buffer: buffer_new(1048577);
    if buffer == 0 { return 9; };
    defer buffer_free(buffer);
    @p unique: false;
    if arg_count() > 0 {
        if arg_count() != 1 or not arg_text_valid(0) { return error(buffer, "ksort: usage: ksort [--unique]\n"); };
        if arg_text(0) != "--unique" { return error(buffer, "ksort: usage: ksort [--unique]\n"); };
        unique: true;
    };
    @p total: 0;
    @p done: false;
    while not done {
        @p n: stdin_read(buffer, total, 1048577 - total);
        if n < 0 { return error(buffer, "ksort: input error\n"); };
        if n == 0 { done: true; };
        total: total + n;
        if total > 1048576 { return error(buffer, "ksort: input exceeds 1 MiB\n"); };
    };
    if not buffer_text_valid(buffer, 0, total) { return error(buffer, "ksort: input must be utf-8\n"); };
    @s rows vector<text>: vector.new<text>(0);
    if not vector.valid(rows) { return 9; };
    @p start: 0;
    @p index: 0;
    while index < total {
        if buffer_get(buffer, index) == 10u8 {
            if not add(rows, buffer, start, index - start) { return error(buffer, "ksort: allocation failure or more than 32768 lines\n"); };
            start: index + 1;
        };
        index: index + 1;
    };
    if start < total {
        if not add(rows, buffer, start, total - start) { return error(buffer, "ksort: allocation failure or more than 32768 lines\n"); };
    };
    if not sort.stable(rows) { return 9; };
    index: 0;
    @p previous: "";
    while index < vector.length(rows) {
        @p value: vector.get(rows, index);
        if not unique or index == 0 or value != previous { print(value); };
        previous: value;
        index: index + 1;
    };
    if stdout_flush() != 0 { return 3; };
    return 0;
};
