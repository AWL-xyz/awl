func contains_folded :: value:text, query:text: bool {
    @p at: 0;
    while at + string.bytes(query) <= string.bytes(value) {
        @p i: 0;
        @p same: true;
        while i < string.bytes(query) and same {
            @p a: i64(string.byte_at(value, at + i));
            @p b: i64(string.byte_at(query, i));
            if a >= 65 and a <= 90 { a: a + 32; };
            if b >= 65 and b <= 90 { b: b + 32; };
            if a != b { same: false; };
            i: i + 1;
        };
        if same { return true; };
        at: at + 1;
    };
    return false;
};
exports{
    @r func integer :: value:text: i64 {
        if string.bytes(value) == 0 or string.bytes(value) > 7 { return -1; };
        if string.bytes(value) > 1 and string.byte_at(value, 0) == 48u8 { return -1; };
        @p number: 0;
        @p i: 0;
        while i < string.bytes(value) {
            @p digit: i64(string.byte_at(value, i)) - 48;
            if digit < 0 or digit > 9 { return -1; };
            number: number * 10 + digit;
            if number > 1000000 { return -1; };
            i: i + 1;
        };
        return number;
    };
    @r func valid_title :: value:text: bool {
        if string.bytes(value) == 0 or string.bytes(value) > 160 { return false; };
        @p i: 0;
        @p nonspace: false;
        while i < string.length(value) {
            @p cp: string.codepoint(value, i);
            if cp < 32u32 or cp == 127u32 { return false; };
            if cp != 32u32 { nonspace: true; };
            i: i + 1;
        };
        return nonspace;
    };
    @r func valid_note :: value:text: bool {
        if string.bytes(value) > 256 { return false; };
        @p i: 0;
        while i < string.length(value) {
            @p cp: string.codepoint(value, i);
            if (cp < 32u32 and cp != 10u32 and cp != 9u32) or cp == 127u32 { return false; };
            i: i + 1;
        };
        return true;
    };
    @r func valid_status :: value:text: bool {
        return value == "todo" or value == "doing" or value == "done";
    };
    @r func visible :: title:text, note:text, status:text, query:text, filter:text: bool {
        if filter != "all" and filter != status { return false; };
        return contains_folded(title, query) or contains_folded(note, query);
    };
};
