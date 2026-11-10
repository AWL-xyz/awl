exports{
    @r func quote[bool] :: payload:text, @b output[text] {
        if string.bytes(payload) > 1024 { return false; };
        @s builder spool: spool.new(8192);
        if not spool.valid(builder) { return false; };
        if spool.append(builder, "\"") < 0 { return false; };
        @p i: 0;
        while i < string.length(payload) {
            @p cp: string.codepoint(payload, i);
            if cp < 32u32 {
                if spool.append(builder, "\\u00") < 0 { return false; };
                if spool.codepoint(builder, string.codepoint("0123456789abcdef", i64(cp) / 16)) < 0 { return false; };
                if spool.codepoint(builder, string.codepoint("0123456789abcdef", i64(cp) % 16)) < 0 { return false; };
            } else {
                if cp == 34u32 or cp == 92u32 {
                    if spool.append(builder, "\\") < 0 { return false; };
                };
                if spool.codepoint(builder, cp) < 0 { return false; };
            };
            i: i + 1;
        };
        if spool.append(builder, "\"") < 0 { return false; };
        return vector.push(output, spool.snapshot(builder));
    };
};
