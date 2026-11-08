func name_ok :: name:text: bool {
    @p size: string.bytes(name);
    if size < 1 or size > 255 or name == "." or name == ".." { return false; };
    @p i: 0;
    while i < size {
        @p b: string.byte_at(name, i);
        if b == 0u8 or b == 47u8 { return false; };
        i: i + 1;
    };
    return true;
};
func copy :: file:i64, buffer:i64: i64 {
    @p total: 0;
    @p done: false;
    while not done {
        @p count: stdin_read(buffer, 0, 65536);
        if count < 0 { return count; };
        if count == 0 { done: true;
        } else {
            if total > 536870912 - count { return -8; };
            @p offset: 0;
            while offset < count {
                @p part: file_write(file, buffer, offset, count - offset);
                if part <= 0 { return -1; };
                offset: offset + part;
            };
            total: total + count;
        };
    };
    return total;
};
func main: i64 {
    if arg_count() != 3 { return 2; };
    @p i: 0;
    while i < 3 { if not arg_text_valid(i) { return 2; }; i: i + 1; };
    @p directory: arg_text(0);
    @p temporary: arg_text(1);
    @p target: arg_text(2);
    if string.bytes(directory) < 1 or not name_ok(temporary) or not name_ok(target) or temporary == target { return 2; };
    @p buffer: buffer_new(65536);
    if buffer == 0 { return 9; };
    defer buffer_free(buffer);
    @p file: file_open(directory + "/" + temporary, 1);
    if file < 0 { print(file); return 3; };
    @p count: copy(file, buffer);
    @p closed: file_close(file);
    if count < 0 or closed < 0 { print(-1); return 4; };
    @p status: file_replace(directory, temporary, target);
    print(status);
    if stdout_flush() != 0 { return 7; };
    if status < 0 { return 5; };
    if status == 1 { return 6; };
    return 0;
};
