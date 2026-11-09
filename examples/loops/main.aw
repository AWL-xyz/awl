-- for over ranges and collections, plus break and continue
func label[text] :: n:i64 {
    if n % 15 == 0 { return "fizzbuzz"; };
    if n % 3 == 0 { return "fizz"; };
    if n % 5 == 0 { return "buzz"; };
    return string.from_i64(n);
};

func main[i64] {
    -- range form, the index is a fresh i64 per iteration
    @p total: 0;
    for i in 0..6 {
        total: total + i;
    };
    print(total);

    -- range with a computed bound
    @p limit: 4;
    for step in 1..limit {
        print(step);
    };

    -- break leaves the loop early
    for n in 0..100 {
        if n == 3 { break; };
        print(n);
    };

    -- continue skips the rest of this iteration
    @p kept: 0;
    for k in 0..10 {
        if k % 2 == 0 { continue; };
        kept: kept + 1;
    };
    print(kept);

    -- nested loops, the inner break only leaves the inner loop
    for row in 0..3 {
        for column in 0..3 {
            if column == 1 { break; };
            print(row * 10 + column);
        };
    };

    -- a real workload over a vector
    @p seen: 0;
    @s words vector<text>: vector.new<text>(4);
    vector.push(words,"alpha");
    vector.push(words,"skip");
    vector.push(words,"beta");
    for word in words {
        if word == "skip" { continue; };
        print(word);
        seen: seen + 1;
    };
    print(seen);

    -- views iterate too, no copy and no ownership
    @p head view<text>: vector.view(words,0,2);
    for shown in head {
        print(shown);
    };

    -- fixed arrays carry their length in the type
    @p grid [i64;3]: [4,5,6];
    @p blended: 0;
    for cell in grid {
        blended: blended + cell;
    };
    print(blended);

    -- while still works, break and continue behave the same
    @p tick: 0;
    while tick < 8 {
        tick: tick + 1;
        if tick % 3 == 0 { continue; };
        if tick == 7 { break; };
        print(label(tick));
    };

    -- numeric loop body
    @p fizzes: 0;
    for index in 1..16 {
        if label(index) == "fizz" { fizzes: fizzes + 1; };
    };
    print(fizzes);
    print("loops done");
    return 0;
};
