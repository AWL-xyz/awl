use crc32;

func main {
    @p start: crc32.start();
    if crc32.finish(start) != 0u32 { return 1; };
    @p bytes: buffer.new(11);
    if bytes == 0 { return 2; };
    defer buffer.free(bytes);
    buffer.set(bytes, 0, 255u8);
    buffer.set(bytes, 10, 10u8);
    if buffer.writetext(bytes, 1, "123456789") != 9 { return 2; };
    @p whole: crc32.update(start, bytes, 1, 9);
    if crc32.finish(whole) != 3421780262u32 {
        print("unexpected CRC-32 for the standard check string");
        return 3;
    };
    for split in 0..10 {
        @p first: crc32.update(start, bytes, 1, split);
        @p second: crc32.update(first, bytes, 1 + split, 9 - split);
        if second != whole {
            print("CRC-32 depends on where the input was split");
            return 4;
        };
    };
    @p state: start;
    for i in 1..10 {
        state: crc32.update(state, bytes, i, 1);
    };
    if state != whole or crc32.update(state, bytes, 11, 0) != state { return 5; };
    if buffer.get(bytes, 0) != 255u8 or buffer.get(bytes, 10) != 10u8 or
    buffer.text(bytes, 1, 9) != "123456789" { return 6; };
    return 0;
};
