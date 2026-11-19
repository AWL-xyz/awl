func main {
    @p count: arg.count() - 1;
    if count < 1 { return 2; };
    @p rounds: arg.i64(0);
    @p checksum: 0;
    for i in 0..rounds {
        @p value: arg.i64(1 + i % count);
        checksum: checksum + value % 97;
    };
    print(checksum);
    return 0;
};
