-- dotenv style parsing: KEY=VALUE lines, # comments, optional export prefix,
-- unquoted (trailing spaces and " #comment" are dropped), "double" (\n \t \\ \" escapes) and 'single' (literal) values.
-- Pairs are appended to keys and values, result[0] is the error code, result[1] the line.
-- codes: 5 invalid input/buffers/allocation, 6 trailing quoted-value data
-- 1 invalid key, 2 missing '=', 3 unterminated quote, 4 more than 256 entries
exports{
    @r func parse :: source:text, @b keys[text], @b values[text], @b result[i64]: bool {
        if vector.length(result) < 2 { return false; };
        vector.set(result, 0, 0); vector.set(result, 1, 0);
        if string.bytes(source) > 16384 or vector.length(keys) != vector.length(values) or vector.length(keys) > 256 {
            vector.set(result, 0, 5); return false;
        };
        @s key spool: spool.new(string.bytes(source));
        @s value spool: spool.new(string.bytes(source));
        if not spool.valid(key) or not spool.valid(value) { vector.set(result, 0, 5); return false; };
        @p state: 0;
        @p line: 1;
        @p escaped: false;
        @p count: 0;
        @p gap: 0;
        for c in source {
            @p newline: c == 10u32;
            if state == 0 {
                if c == 35u32 { state: 5; }
                elseif c == 32u32 or c == 9u32 or c == 13u32 or newline { }
                elseif (c >= 65u32 and c <= 90u32) or (c >= 97u32 and c <= 122u32) or c == 95u32 { spool.clear(key); spool.codepoint(key, c); state: 1; }
                else { vector.set(result, 0, 1); vector.set(result, 1, line); return false; };
            } elseif state == 1 {
                if (c >= 65u32 and c <= 90u32) or (c >= 97u32 and c <= 122u32) or c == 95u32 or (c >= 48u32 and c <= 57u32) { spool.codepoint(key, c); }
                elseif c == 61u32 { spool.clear(value); state: 2; }
                elseif c == 32u32 or c == 9u32 {
                    if spool.snapshot(key) == "export" { spool.clear(key); state: 0; } else { state: 8; };
                }
                else { vector.set(result, 0, 1); vector.set(result, 1, line); return false; };
            } elseif state == 8 {
                if c == 61u32 { spool.clear(value); state: 2; }
                elseif c == 32u32 or c == 9u32 { }
                else { vector.set(result, 0, 2); vector.set(result, 1, line); return false; };
            } elseif state == 2 {
                spool.clear(value);
                if c == 32u32 or c == 9u32 { }
                elseif c == 34u32 { state: 4; escaped: false; }
                elseif c == 39u32 { state: 6; }
                elseif newline or c == 13u32 { state: 9; }
                elseif c == 35u32 { state: 11; }
                else { spool.codepoint(value, c); state: 3; };
            } elseif state == 3 {
                if newline or c == 13u32 { state: 9; gap: 0; }
                elseif c == 32u32 or c == 9u32 { gap: gap + 1; }
                elseif c == 35u32 and gap > 0 { state: 11; gap: 0; }
                else {
                    while gap > 0 { spool.codepoint(value, 32u32); gap: gap - 1; };
                    spool.codepoint(value, c);
                };
            } elseif state == 4 {
                if escaped {
                    escaped: false;
                    if c == 110u32 { spool.codepoint(value, 10u32); }
                    elseif c == 116u32 { spool.codepoint(value, 9u32); }
                    else { spool.codepoint(value, c); };
                } elseif c == 92u32 { escaped: true; }
                elseif c == 34u32 { state: 9; }
                else { spool.codepoint(value, c); };
            } elseif state == 6 {
                if c == 39u32 { state: 9; }
                else { spool.codepoint(value, c); };
            } elseif state == 9 {
                if newline { state: 10; }
                elseif c == 35u32 { state: 11; }
                elseif c != 32u32 and c != 9u32 and c != 13u32 { vector.set(result, 0, 6); vector.set(result, 1, line); return false; };
            };
            if state == 11 and newline { state: 10; };
            if state == 5 and newline { state: 0; };
            if state == 10 or (state == 9 and newline) {
                if vector.length(keys) == 256 { vector.set(result, 0, 4); vector.set(result, 1, line); return false; };
                if not vector.reserve(keys, vector.length(keys) + 1) or not vector.reserve(values, vector.length(values) + 1) { vector.set(result, 0, 4); vector.set(result, 1, line); return false; };
                vector.push(keys, spool.snapshot(key));
                vector.push(values, spool.snapshot(value));
                count: count + 1;
                state: 0;
            };
            if newline { line: line + 1; };
        };
        if state == 4 or state == 6 { vector.set(result, 0, 3); vector.set(result, 1, line); return false; };
        if state == 1 or state == 8 { vector.set(result, 0, 2); vector.set(result, 1, line); return false; };
        if state == 2 or state == 3 or state == 9 or state == 11 {
            if vector.length(keys) == 256 { vector.set(result, 0, 4); vector.set(result, 1, line); return false; };
            if not vector.reserve(keys, vector.length(keys) + 1) or not vector.reserve(values, vector.length(values) + 1) { vector.set(result, 0, 4); vector.set(result, 1, line); return false; };
            vector.push(keys, spool.snapshot(key));
            vector.push(values, spool.snapshot(value));
        };
        return true;
    };
    @r func find :: name:text, @b keys[text]: i64 {
        @p i: 0;
        while i < vector.length(keys) {
            if vector.get(keys, i) == name { return i; };
            i: i + 1;
        };
        return -1;
    };
    @r func get :: name:text, @b keys[text], @b values[text], fallback:text: text {
        @p i: find(name, keys);
        if i < 0 or i >= vector.length(values) { return fallback; };
        return vector.get(values, i);
    };
};
