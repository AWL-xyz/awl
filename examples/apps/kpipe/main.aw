func write_all[bool] :: buffer:i64, count:i64, errors:bool {
    @p offset: 0;
    while offset < count {
        @p written: 0;
        if errors {
            written: stderr_write(buffer, offset, count - offset);
        } else {
            written: stdout_write(buffer, offset, count - offset);
        };
        if written <= 0 {
            return false;
        };
        offset: offset + written;
    };
    return true;
};
func message[bool] :: buffer:i64, payload:text {
    @p count: buffer_write_text(buffer, 0, payload);
    if count < 0 {
        return false;
    };
    return write_all(buffer, count, true);
};
func main[i64] {
    @p buffer: buffer_new(65536);
    if buffer == 0 {
        return 9;
    };
    defer buffer_free(buffer);
    @p mode: "copy";
    @p size: env_read("KPIPE_MODE", buffer, 0, 16);
    if size >= 0 {
        if not buffer_text_valid(buffer, 0, size) {
            message(buffer, "kpipe: mode must be valid utf-8\n");
            return 2;
        };
        mode: buffer_text(buffer, 0, size);
    } else {
        if size != -2 {
            message(buffer, "kpipe: cannot read mode configuration\n");
            return 2;
        };
    };
    if mode != "copy" and mode != "upper" and mode != "lower" {
        message(buffer, "kpipe: mode must be copy, upper, or lower\n");
        return 2;
    };
    @p report: false;
    size: env_read("KPIPE_REPORT", buffer, 0, 1);
    if size >= 0 {
        report: size == 1 and buffer_get(buffer, 0) == 49u8;
        if not report {
            message(buffer, "kpipe: report must be 1 when set\n");
            return 2;
        };
    } else {
        if size != -2 {
            message(buffer, "kpipe: cannot read report configuration\n");
            return 2;
        };
    };
    @p total: 0;
    @p running: true;
    while running {
        @p count: stdin_read(buffer, 0, 65536);
        if count < 0 {
            message(buffer, "kpipe: stdin read failed\n");
            return 3;
        };
        if count == 0 {
            running: false;
        } else {
            if mode != "copy" {
                @p index: 0;
                while index < count {
                    @p byte: buffer_get(buffer, index);
                    if mode == "upper" and byte >= 97u8 and byte <= 122u8 {
                        buffer_set(buffer, index, byte - 32u8);
                    };
                    if mode == "lower" and byte >= 65u8 and byte <= 90u8 {
                        buffer_set(buffer, index, byte + 32u8);
                    };
                    index: index + 1;
                };
            };
            if not write_all(buffer, count, false) {
                message(buffer, "kpipe: stdout write failed\n");
                return 4;
            };
            total: total + count;
        };
    };
    if stdout_flush() < 0 {
        return 5;
    };
    if report {
        @p summary: "bytes processed: " + string.from_i64(total) + "\n";
        if not message(buffer, summary) {
            return 6;
        };
        if stderr_flush() < 0 {
            return 6;
        };
    };
    return 0;
};
