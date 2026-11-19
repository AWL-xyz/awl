use csv;

func assert_row[bool] :: @b fields[text], @b rows[i64] {
    if vector.length(rows) != 2 or vector.length(fields) != 4 { return false; };
    return vector.get(rows, 0) == 2 and vector.get(rows, 1) == 4 and
           vector.get(fields, 0) == "item" and vector.get(fields, 1) == "quantity" and
           vector.get(fields, 2) == "Owl \"λ\"\r\nlarge" and vector.get(fields, 3) == "+0007";
};

func main {
    @s fields vector<text>: vector.new<text>(0);
    @s rows vector<i64>: vector.new<i64>(0);
    @s output spool: spool.new(128);
    @s small spool: spool.new(14);
    if not spool.valid(output) or not spool.valid(small) { return 1; };

    @p parsed: csv.parse("item,quantity\r\n\"Owl \"\"λ\"\"\r\nlarge\",+0007", fields, rows);
    if parsed.code != 0 or not assert_row(fields, rows) {
        print("the quoted multiline record should parse to two fields");
        return 2;
    };
    @p duplicate: csv.parse("a\n", fields, rows);
    if duplicate.code != 3 or duplicate.offset != -1 or not assert_row(fields, rows) {
        print("parse should reject nonempty outputs without changing them");
        return 3;
    };
    if not csv.encode(fields, rows, output) { return 4; };
    @p encoded: spool.snapshot(output);
    if encoded != "\"item\",\"quantity\"\n\"Owl \"\"λ\"\"\r\nlarge\",\"+0007\"\n" {
        print("expected canonical LF records with escaped quotes");
        return 5;
    };
    if spool.append(small, "π") != 0 or csv.encode(fields, rows, small) or spool.snapshot(small) != "π" {
        print("encoding should roll back when the next field exceeds capacity");
        return 6;
    };
    for after in 2..6 {
        if after != 4 {
            vector.set(rows, 1, after);
            if csv.encode(fields, rows, output) or spool.snapshot(output) != encoded {
                print("encoding should reject a malformed row table without appending");
                return 7;
            };
        };
    };

    vector.clear(fields);
    vector.clear(rows);
    @p invalid: csv.parse("ok\nλ,\"bad\"tail", fields, rows);
    if invalid.code != 1 or invalid.offset != 10 or vector.length(fields) != 0 or vector.length(rows) != 0 {
        print("a bad record should report a scalar offset and clear partial output");
        return 8;
    };
    parsed: csv.parse(encoded, fields, rows);
    if parsed.code != 0 or not assert_row(fields, rows) { return 9; };
    spool.clear(output);
    if spool.append(output, "π:") != 0 or not csv.encode(fields, rows, output) or
       spool.snapshot(output) != "π:" + encoded { return 10; };

    vector.clear(fields);
    vector.clear(rows);
    @s tight spool: spool.new(4);
    @s exact spool: spool.new(5);
    if not vector.push(fields, "\"") or not vector.push(rows, 1) { return 11; };
    if csv.encode(fields, rows, tight) or spool.bytes(tight) != 0 { return 12; };
    if not csv.encode(fields, rows, exact) or spool.snapshot(exact) != "\"\"\"\"\n" { return 13; };

    @s unavailable vector<text>: vector.new<text>(-1);
    @p storage: csv.parse("", unavailable, rows);
    if storage.code != 3 or storage.offset != -1 or csv.encode(unavailable, rows, output) { return 14; };
    return 0;
};
