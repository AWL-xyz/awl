use Json.aw as json;
func read :: file:i64, buffer:i64: i64 {
    @p count: 0;
    while count < 16385 {
        @p n: file_read(file, buffer, count, 16385 - count);
        if n < 0 { return n; };
        if n == 0 { return count; };
        count: count + n;
    };
    return count;
};
func message :: buffer:i64, payload:text: i64 {
    @p count: buffer_write_text(buffer, 0, payload + "\n");
    @p offset: 0;
    while offset < count {
        @p n: stderr_write(buffer, offset, count - offset);
        if n <= 0 { return -1; };
        offset: offset + n;
    };
    return stderr_flush();
};
func main: i64 {
    if arg_count() < 1 or arg_count() > 2 { return 2; };
    if not arg_text_valid(0) { return 2; };
    @p pointer: "";
    if arg_count() == 2 {
        if not arg_text_valid(1) { return 2; };
        pointer: arg_text(1);
    };
    @p buffer: buffer_new(16385);
    if buffer == 0 { return 9; };
    defer buffer_free(buffer);
    @p file: file_open(arg_text(0), 0);
    if file < 0 { message(buffer, "cannot open input"); return 3; };
    @p count: read(file, buffer);
    @p closed: file_close(file);
    if count < 0 or closed < 0 { message(buffer, "input read/close failed"); return 3; };
    if count > 16384 { message(buffer, "input exceeds 16384 bytes"); return 4; };
    if not buffer_text_valid(buffer, 0, count) { message(buffer, "input isn't UTF-8"); return 4; };
    @p source: buffer_text(buffer, 0, count);
    @s tokens vector<text>: vector.new<text>(0);
    @s result vector<i64>: vector.new<i64>(0);
    if not vector.valid(tokens) or not vector.valid(result) { return 9; };
    if not json.parse(source, tokens, result) {
        if vector.length(result) < 2 { return 9; };
        message(buffer, "json error " + string.from_i64(vector.get(result, 0)) + " at byte " + string.from_i64(vector.get(result, 1)));
        return 4;
    };
    @p selected: json.locate(pointer, tokens, result);
    if selected < 0 {
        message(buffer, "selection error " + string.from_i64(selected));
        if selected == -2 { return 2; };
        return 5;
    };
    @p kind: vector.get(result, 2 + selected * 2);
    if kind < 5 or kind > 9 { message(buffer, "selected value isn't a scalar"); return 6; };
    count: buffer_write_text(buffer, 0, vector.get(tokens, selected) + "\n");
    @p offset: 0;
    while offset < count {
        @p n: stdout_write(buffer, offset, count - offset);
        if n <= 0 { return 3; };
        offset: offset + n;
    };
    if stdout_flush() != 0 { return 3; };
    return 0;
};
