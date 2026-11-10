exports{
    @r func render :: lines:view<text>, first:i64 {
        @p i: 0;
        while i < view.length(lines) {
            print(string.fromi64(first + i) + ": " + view.get(lines, i));
            i: i + 1;
        };
    };
};
