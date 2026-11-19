-- The harness supplies three UTF-8 fields on stdin, separated by byte counts
-- in argv. Lengths (rather than delimiters) allow embedded NUL and newlines.
func main {
    if arg.count() != 3 { return 2; };
    @p source: arg.i64(0);
    @p from: arg.i64(1);
    @p to: arg.i64(2);
    if source < 0 or source > 1048576 or from < 0 or from > 1048576 or to < 0 or to > 1048576 {
        return 2;
    };
    @p size: source + from + to;
    @p bytes: buffer.new(size);
    if bytes == 0 { return 2; };
    defer buffer.free(bytes);
    @p received: 0;
    while received < size {
        @p n: stdin.read(bytes, received, size - received);
        if n <= 0 { return 2; };
        received: received + n;
    };
    @p result: string.replace(buffer.text(bytes, 0, source),
        buffer.text(bytes, source, from), buffer.text(bytes, source + from, to));
    print(string.length(result));
    print(string.bytes(result));
    print(result);
    return 0;
};
