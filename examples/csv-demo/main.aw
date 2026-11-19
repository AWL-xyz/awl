use csv;

func fail[i64] :: scratch:i64, message:text {
    @p size: buffer.writetext(scratch, 0, message);
    if size < 0 { return 3; };
    @p sent: 0;
    while sent < size {
        @p wrote: stderr.write(scratch, sent, size - sent);
        if wrote <= 0 { return 3; };
        sent: sent + wrote;
    };
    return 2;
};

func main {
    -- Reserve one extra byte to distinguish a full input from an oversized one.
    @p scratch: buffer.new(1048577);
    if scratch == 0 { return 3; };
    defer buffer.free(scratch);
    @p size: 0;
    while size <= 1048576 {
        @p got: stdin.read(scratch, size, 1048577 - size);
        if got < 0 { return fail(scratch, "csv-demo: input read failed\n"); };
        if got == 0 { break; };
        size: size + got;
    };
    if size > 1048576 { return fail(scratch, "csv-demo: input exceeds 1 MiB\n"); };
    if not buffer.textvalid(scratch, 0, size) { return fail(scratch, "csv-demo: input must be UTF-8\n"); };

    @s fields vector<text>: vector.new<text>(0);
    @s rows vector<i64>: vector.new<i64>(0);
    @p result: csv.parse(buffer.text(scratch, 0, size), fields, rows);
    if result.code != 0 {
        @p message: "csv-demo: CSV error " + string.fromi64(result.code);
        if result.offset >= 0 { message: message + " at scalar offset " + string.fromi64(result.offset); };
        return fail(scratch, message + "\n");
    };
    if vector.length(rows) == 0 or vector.get(rows, 0) != 2 or
       vector.get(fields, 0) != "item" or vector.get(fields, 1) != "quantity" {
        return fail(scratch, "csv-demo: expected item,quantity header\n");
    };

    @p first: 2;
    @p total: 0;
    @p count: vector.length(rows);
    for row in 1..count {
        @p after: vector.get(rows, row);
        if after - first != 2 { return fail(scratch, "csv-demo: each order must have two fields\n"); };
        @p value: vector.get(fields, first + 1);
        if not string.i64valid(value) { return fail(scratch, "csv-demo: quantity must be a signed decimal integer\n"); };
        @p quantity: string.toi64(value);
        -- Together with the CSV row limit, this keeps the sum in range.
        if quantity < 0 or quantity > 1000000000 { return fail(scratch, "csv-demo: quantity must be 0..1000000000\n"); };
        total: total + quantity;
        first: after;
    };
    print("Orders: " + string.fromi64(count - 1));
    print("Total quantity: " + string.fromi64(total));
    return 0;
};
