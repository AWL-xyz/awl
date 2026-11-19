use crc32;

func fail[i64] :: scratch:i64, message:text, code:i64 {
    @p size: buffer.writetext(scratch, 0, message);
    if size < 0 { return 3; };
    @p sent: 0;
    while sent < size {
        @p wrote: stderr.write(scratch, sent, size - sent);
        if wrote <= 0 { return 3; };
        sent: sent + wrote;
    };
    return code;
};

func write_checksum[bool] :: scratch:i64, value:u32 {
    @p digits: "0123456789abcdef";
    for i in 0..8 {
        @p digit: bits.and(bits.shr(value, (7 - i) * 4), 15u32);
        buffer.set(scratch, i, string.byteat(digits, i64.convert(digit)));
    };
    buffer.set(scratch, 8, 10u8);
    @p sent: 0;
    while sent < 9 {
        @p wrote: stdout.write(scratch, sent, 9 - sent);
        if wrote <= 0 { return false; };
        sent: sent + wrote;
    };
    return true;
};

func main {
    @p capacity: 65536;
    @p scratch: buffer.new(capacity);
    if scratch == 0 { return 3; };
    defer buffer.free(scratch);
    if arg.count() != 0 { return fail(scratch, "usage: crc32-demo < FILE\n", 2); };

    @p state: crc32.start();
    while true {
        @p got: stdin.read(scratch, 0, capacity);
        if got < 0 { return fail(scratch, "crc32-demo: input read failed\n", 3); };
        if got == 0 { break; };
        state: crc32.update(state, scratch, 0, got);
    };
    if not write_checksum(scratch, crc32.finish(state)) {
        return fail(scratch, "crc32-demo: output write failed\n", 3);
    };
    return 0;
};
