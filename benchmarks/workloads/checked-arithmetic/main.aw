func main {
    if arg.count() != 3 { return 2; };
    @p rounds: arg.i64(0);
    @p factor: arg.i64(1);
    @p state: arg.i64(2);
    @p total: 0;
    for i in 0..rounds {
        state: (state * factor - i) % 1048573;
        total: total + state;
    };
    print(total);
    print(state);
    return 0;
};
