-- Bounded UTF-8 comma-separated tables. Each row end is an exclusive index
-- into the flat field vector. The package does not interpret headers or types.
@p max_bytes i64: 1048576;
@p max_fields i64: 8192;
@p max_rows i64: 4096;

func finish[i64] :: @b fields[text], @b rows[i64], @b field:spool, end_row:bool {
    if vector.length(fields) == max_fields or (end_row and vector.length(rows) == max_rows) { return 2; };
    if not vector.push(fields, spool.snapshot(field)) { return 3; };
    if end_row and not vector.push(rows, vector.length(fields)) { return 3; };
    spool.clear(field);
    return 0;
};

func read_table[Result] :: source:text, @b fields[text], @b rows[i64], @b field:spool {
    -- States: 0 start of field, 1 unquoted, 2 quoted, 3 after a quote.
    @p state: 0;
    @p offset: 0;
    @p started: false;
    @p expect_lf: false;
    for cp in source {
        @p field_break: false;
        @p row_break: false;
        @p append: false;
        if expect_lf {
            if cp != 10u32 { return Result(1, offset - 1); };
            expect_lf: false;
            row_break: true;
        } elseif state == 2 {
            if cp == 34u32 { state: 3; } else { append: true; };
        } elseif state == 3 and cp == 34u32 {
            state: 2;
            append: true;
        } elseif cp == 44u32 {
            field_break: true;
        } elseif cp == 10u32 {
            row_break: true;
        } elseif cp == 13u32 {
            expect_lf: true;
        } elseif state == 3 {
            return Result(1, offset);
        } elseif cp == 34u32 {
            if state != 0 { return Result(1, offset); };
            state: 2;
        } else {
            state: 1;
            append: true;
        };
        if append and spool.codepoint(field, cp) != 0 { return Result(3, offset); };
        started: not row_break;
        if field_break or row_break {
            @p code: finish(fields, rows, field, row_break);
            if code != 0 { return Result(code, offset); };
            state: 0;
        };
        offset: offset + 1;
    };
    if expect_lf { return Result(1, offset - 1); };
    if state == 2 { return Result(1, offset); };
    if started { return Result(finish(fields, rows, field, true), offset); };
    return Result(0, offset);
};

func write_table[bool] :: @b fields[text], @b rows[i64], @b sink:spool, budget:i64 {
    @p room: budget;
    @p index: 0;
    for after in rows {
        while index < after {
            @p field: vector.get(fields, index);
            -- The quotes and one separator (comma or LF) also count.
            @p needed: string.bytes(field) + 3;
            if needed > room { return false; };
            room: room - needed;
            if spool.append(sink, "\"") != 0 { return false; };
            for cp in field {
                if cp == 34u32 {
                    if room == 0 or spool.codepoint(sink, cp) != 0 { return false; };
                    room: room - 1;
                };
                if spool.codepoint(sink, cp) != 0 { return false; };
            };
            index: index + 1;
            @p suffix: "\",";
            if index == after { suffix: "\"\n"; };
            if spool.append(sink, suffix) != 0 { return false; };
        };
    };
    return true;
};

exports {
    -- 0 success, 1 malformed CSV, 2 budget exceeded, 3 invalid outputs/storage.
    -- Offset counts Unicode scalars; -1 means no source position applies.
    @r struct Result {
        code:i64;
        offset:i64;
    };

    @r func parse[Result] :: source:text, @b fields[text], @b rows[i64] {
        if not vector.valid(fields) or not vector.valid(rows) { return Result(3, -1); };
        if vector.length(fields) != 0 or vector.length(rows) != 0 { return Result(3, -1); };
        @p size: string.bytes(source);
        if size > max_bytes { return Result(2, -1); };
        if size == 0 { return Result(0, 0); };
        @s field spool: spool.new(size);
        if not spool.valid(field) { return Result(3, -1); };
        @p result: read_table(source, fields, rows, field);
        if result.code != 0 {
            vector.clear(fields);
            vector.clear(rows);
        };
        return result;
    };

    -- Append canonical CSV (all fields quoted, LF after every row). The sink's
    -- previous contents survive any reported failure, even after a partial write.
    @r func encode[bool] :: @b fields[text], @b rows[i64], @b sink:spool {
        if not vector.valid(fields) or not vector.valid(rows) or not spool.valid(sink) { return false; };
        @p count: vector.length(fields);
        if count > max_fields or vector.length(rows) > max_rows { return false; };
        @p previous: 0;
        for after in rows {
            if after <= previous or after > count { return false; };
            previous: after;
        };
        if previous != count { return false; };
        @p initial: spool.length(sink);
        @p budget: spool.capacity(sink) - spool.bytes(sink);
        if budget > max_bytes { budget: max_bytes; };
        if write_table(fields, rows, sink, budget) { return true; };
        spool.truncate(sink, initial);
        return false;
    };
};
