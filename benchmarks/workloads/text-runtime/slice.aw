-- All text and offsets enter through argv, not constant-folded fixtures.
func main {
    if arg.count() != 5 { return 2; };
    @p source: arg.text(0);
    @p start: arg.i64(1);
    @p width: arg.i64(2);
    @p jitter: arg.i64(3);
    @p rounds: arg.i64(4);
    @p checksum: 0;
    for i in 0..rounds {
        @p part: string.slice(source, start + i % jitter, width);
        @p bytes: string.bytes(part);
        checksum: checksum + bytes + i64.convert(string.byteat(part, 0)) + i64.convert(string.byteat(part, bytes - 1));
    };
    print(checksum);
    return 0;
};
