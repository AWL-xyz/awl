func fail[i64] :: @b result[i64], code:i64, offset:i64 {
    vector.set(result, 0, code);
    vector.set(result, 1, offset);
    return -1;
};
func space[i64] :: source:text, offset:i64 {
    while offset < string.bytes(source) {
        @p b: string.byte_at(source, offset);
        if b != 32u8 and b != 9u8 and b != 10u8 and b != 13u8 { return offset; };
        offset: offset + 1;
    };
    return offset;
};
func emit[bool] :: kind:i64, value:text, offset:i64, @b values[text], @b metadata[i64], @b result[i64] {
    if vector.length(values) == 512 { fail(result, 2, offset); return false; };
    if not vector.reserve(values, vector.length(values) + 1) or not vector.reserve(metadata, vector.length(metadata) + 2) { fail(result, 3, offset); return false; };
    vector.push(values, value);
    vector.push(metadata, kind);
    vector.push(metadata, offset);
    return true;
};
func hex[i64] :: source:text, offset:i64 {
    if offset + 4 > string.bytes(source) { return -1; };
    @p value: 0;
    @p i: 0;
    while i < 4 {
        @p b: i64(string.byte_at(source, offset + i));
        @p digit: -1;
        if b >= 48 and b <= 57 { digit: b - 48; };
        if b >= 65 and b <= 70 { digit: b - 55; };
        if b >= 97 and b <= 102 { digit: b - 87; };
        if digit < 0 { return -1; };
        value: value * 16 + digit;
        i: i + 1;
    };
    return value;
};
func quoted[i64] :: source:text, offset:i64, kind:i64, @b values[text], @b metadata[i64], @b result[i64] {
    @p start: offset;
    @p size: string.bytes(source);
    if offset >= size { return fail(result, 1, offset); };
    if string.byte_at(source, offset) != 34u8 { return fail(result, 1, offset); };
    @s builder spool: spool.new(4096);
    if not spool.valid(builder) { return fail(result, 3, offset); };
    offset: offset + 1;
    while offset < size {
        @p at: offset;
        @p cp: i64(string.byte_at(source, offset));
        offset: offset + 1;
        if cp == 34 {
            if not emit(kind, spool.snapshot(builder), start, values, metadata, result) { return -1; };
            return offset;
        };
        if cp < 32 { return fail(result, 1, at); };
        if cp == 92 {
            if offset == size { return fail(result, 1, offset); };
            cp: i64(string.byte_at(source, offset));
            offset: offset + 1;
            if cp == 117 {
                cp: hex(source, offset);
                if cp < 0 { return fail(result, 1, offset); };
                offset: offset + 4;
                if cp >= 55296 and cp <= 56319 {
                    if offset + 6 > size { return fail(result, 1, offset); };
                    if string.byte_at(source, offset) != 92u8 or string.byte_at(source, offset + 1) != 117u8 { return fail(result, 1, offset); };
                    @p low: hex(source, offset + 2);
                    if low < 56320 or low > 57343 { return fail(result, 1, offset + 2); };
                    cp: 65536 + (cp - 55296) * 1024 + low - 56320;
                    offset: offset + 6;
                } else {
                    if cp >= 56320 and cp <= 57343 { return fail(result, 1, at); };
                };
            } else {
                if cp == 98 { cp: 8;
                } else { if cp == 102 { cp: 12;
                } else { if cp == 110 { cp: 10;
                } else { if cp == 114 { cp: 13;
                } else { if cp == 116 { cp: 9;
                } else { if cp != 34 and cp != 92 and cp != 47 { return fail(result, 1, at); }; }; }; }; }; };
            };
        } else {
            if cp >= 128 {
                @p width: 2;
                @p mask: 32;
                if cp >= 224 { width: 3; mask: 16; };
                if cp >= 240 { width: 4; mask: 8; };
                cp: cp % mask;
                @p i: 1;
                while i < width {
                    cp: cp * 64 + i64(string.byte_at(source, offset)) % 64;
                    offset: offset + 1;
                    i: i + 1;
                };
            };
        };
        @p bytes: 1;
        if cp >= 128 { bytes: 2; };
        if cp >= 2048 { bytes: 3; };
        if cp >= 65536 { bytes: 4; };
        if spool.bytes(builder) + bytes > 4096 { return fail(result, 2, at); };
        if spool.codepoint(builder, u32(cp)) < 0 { return fail(result, 3, at); };
    };
    return fail(result, 1, size);
};
func digit[bool] :: source:text, offset:i64 {
    if offset >= string.bytes(source) { return false; };
    @p b: string.byte_at(source, offset);
    return b >= 48u8 and b <= 57u8;
};
func number[i64] :: source:text, offset:i64, @b values[text], @b metadata[i64], @b result[i64] {
    @p start: offset;
    @p size: string.bytes(source);
    if string.byte_at(source, offset) == 45u8 { offset: offset + 1; };
    if not digit(source, offset) { return fail(result, 1, offset); };
    if string.byte_at(source, offset) == 48u8 { offset: offset + 1;
    } else { while digit(source, offset) { offset: offset + 1; }; };
    if offset < size {
        if string.byte_at(source, offset) == 46u8 {
            offset: offset + 1;
            if not digit(source, offset) { return fail(result, 1, offset); };
            while digit(source, offset) { offset: offset + 1; };
        };
    };
    if offset < size {
        @p b: string.byte_at(source, offset);
        if b == 101u8 or b == 69u8 {
            offset: offset + 1;
            if offset < size {
                b: string.byte_at(source, offset);
                if b == 43u8 or b == 45u8 { offset: offset + 1; };
            };
            if not digit(source, offset) { return fail(result, 1, offset); };
            while digit(source, offset) { offset: offset + 1; };
        };
    };
    @s builder spool: spool.new(16384);
    if not spool.valid(builder) { return fail(result, 3, start); };
    @p i: start;
    while i < offset { spool.codepoint(builder, u32(string.byte_at(source, i))); i: i + 1; };
    if not emit(6, spool.snapshot(builder), start, values, metadata, result) { return -1; };
    return offset;
};
func item[i64] :: source:text, offset:i64, depth:i64, @b values[text], @b metadata[i64], @b result[i64] {
    offset: space(source, offset);
    @p size: string.bytes(source);
    if offset == size { return fail(result, 1, offset); };
    @p b: string.byte_at(source, offset);
    if b == 34u8 { return quoted(source, offset, 5, values, metadata, result); };
    if b == 45u8 or digit(source, offset) { return number(source, offset, values, metadata, result); };
    if b == 123u8 or b == 91u8 {
        if depth == 16 { return fail(result, 2, offset); };
        @p kind: 1;
        @p close: 125u8;
        if b == 91u8 { kind: 2; close: 93u8; };
        if not emit(kind, "", offset, values, metadata, result) { return -1; };
        offset: space(source, offset + 1);
        if offset < size {
            if string.byte_at(source, offset) == close {
                if not emit(kind + 2, "", offset, values, metadata, result) { return -1; };
                return offset + 1;
            };
        };
        while offset < size {
            if kind == 1 {
                offset: quoted(source, offset, 10, values, metadata, result);
                if offset < 0 { return -1; };
                offset: space(source, offset);
                if offset == size { return fail(result, 1, offset); };
                if string.byte_at(source, offset) != 58u8 { return fail(result, 1, offset); };
                offset: offset + 1;
            };
            offset: item(source, offset, depth + 1, values, metadata, result);
            if offset < 0 { return -1; };
            offset: space(source, offset);
            if offset == size { return fail(result, 1, offset); };
            b: string.byte_at(source, offset);
            if b == close {
                if not emit(kind + 2, "", offset, values, metadata, result) { return -1; };
                return offset + 1;
            };
            if b != 44u8 { return fail(result, 1, offset); };
            offset: space(source, offset + 1);
        };
        return fail(result, 1, offset);
    };
    @p literal: "null";
    @p kind: 9;
    if b == 116u8 { literal: "true"; kind: 7; };
    if b == 102u8 { literal: "false"; kind: 8; };
    @p i: 0;
    while i < string.bytes(literal) {
        if offset + i >= size { return fail(result, 1, size); };
        if string.byte_at(source, offset + i) != string.byte_at(literal, i) { return fail(result, 1, offset + i); };
        i: i + 1;
    };
    if not emit(kind, literal, offset, values, metadata, result) { return -1; };
    return offset + i;
};
func after[i64] :: index:i64, @b tokens[text], @b result[i64] {
    @p kind: vector.get(result, 2 + index * 2);
    if kind != 1 and kind != 2 { return index + 1; };
    @p depth: 1;
    index: index + 1;
    while index < vector.length(tokens) {
        kind: vector.get(result, 2 + index * 2);
        if kind == 1 or kind == 2 { depth: depth + 1; };
        if kind == 3 or kind == 4 { depth: depth - 1; };
        index: index + 1;
        if depth == 0 { return index; };
    };
    return -1;
};
exports{
    @r func parse[bool] :: source:text, @b tokens[text], @b result[i64] {
        if not vector.reserve(result, 2) { return false; };
        vector.clear(result);
        vector.push(result, 0);
        vector.push(result, 0);
        if string.bytes(source) > 65536 { fail(result, 2, 65536); return false; };
        @s values vector<text>: vector.new<text>(0);
        @s metadata vector<i64>: vector.new<i64>(0);
        if not vector.valid(values) or not vector.valid(metadata) { fail(result, 3, 0); return false; };
        @p offset: item(source, 0, 0, values, metadata, result);
        if offset < 0 { return false; };
        offset: space(source, offset);
        if offset != string.bytes(source) { fail(result, 1, offset); return false; };
        if not vector.reserve(tokens, vector.length(values)) or not vector.reserve(result, vector.length(metadata) + 2) { fail(result, 3, offset); return false; };
        vector.clear(tokens);
        @p i: 0;
        while i < vector.length(values) { vector.push(tokens, vector.get(values, i)); i: i + 1; };
        i: 0;
        while i < vector.length(metadata) { vector.push(result, vector.get(metadata, i)); i: i + 1; };
        vector.set(result, 1, offset);
        return true;
    };
    @r func locate[i64] :: pointer:text, @b tokens[text], @b result[i64] {
        @p count: vector.length(tokens);
        if count == 0 or vector.length(result) != count * 2 + 2 { return -4; };
        if vector.get(result, 0) != 0 { return -4; };
        if string.bytes(pointer) > 4096 { return -2; };
        if pointer == "" { return 0; };
        if string.codepoint(pointer, 0) != 47u32 { return -2; };
        @s parts vector<text>: vector.new<text>(16);
        @s builder spool: spool.new(4096);
        if not vector.valid(parts) or not spool.valid(builder) { return -5; };
        @p i: 1;
        @p size: string.length(pointer);
        while i <= size {
            if i == size {
                if vector.length(parts) == 16 { return -2; };
                vector.push(parts, spool.snapshot(builder));
                i: i + 1;
            } else {
                @p cp: string.codepoint(pointer, i);
                i: i + 1;
                if cp == 47u32 {
                    if vector.length(parts) == 16 { return -2; };
                    vector.push(parts, spool.snapshot(builder));
                    spool.clear(builder);
                } else {
                    if cp == 126u32 {
                        if i == size { return -2; };
                        cp: string.codepoint(pointer, i);
                        i: i + 1;
                        if cp == 48u32 { cp: 126u32;
                        } else { if cp == 49u32 { cp: 47u32;
                        } else { return -2; }; };
                    };
                    if spool.codepoint(builder, cp) < 0 { return -5; };
                };
            };
        };
        @p selected: 0;
        i: 0;
        while i < vector.length(parts) {
            @p part: vector.get(parts, i);
            @p kind: vector.get(result, 2 + selected * 2);
            @p cursor: selected + 1;
            @p found: -1;
            if kind == 1 {
                while cursor < count {
                    @p next: vector.get(result, 2 + cursor * 2);
                    if next == 3 { cursor: count;
                    } else {
                        if next != 10 or cursor + 1 >= count { return -4; };
                        if vector.get(tokens, cursor) == part {
                            if found >= 0 { return -3; };
                            found: cursor + 1;
                        };
                        cursor: after(cursor + 1, tokens, result);
                        if cursor < 0 { return -4; };
                    };
                };
            } else {
                if kind != 2 { return -1; };
                @p index: 0;
                @p j: 0;
                if part == "-" { return -1; };
                if string.bytes(part) == 0 { return -2; };
                if string.bytes(part) > 1 {
                    if string.byte_at(part, 0) == 48u8 { return -2; };
                };
                while j < string.bytes(part) {
                    @p b: string.byte_at(part, j);
                    if b < 48u8 or b > 57u8 { return -2; };
                    if index <= 512 { index: index * 10 + i64(b) - 48; };
                    j: j + 1;
                };
                j: 0;
                while cursor < count {
                    if vector.get(result, 2 + cursor * 2) == 4 { cursor: count;
                    } else {
                        if j == index { found: cursor; };
                        cursor: after(cursor, tokens, result);
                        if cursor < 0 { return -4; };
                        j: j + 1;
                    };
                };
            };
            if found < 0 { return -1; };
            selected: found;
            i: i + 1;
        };
        return selected;
    };
};
