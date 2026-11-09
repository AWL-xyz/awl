exports{
    @r func parse[bool] :: payload:text, base:i64, @b output[i64] {
        if base < 2 or base > 36 { return false; };
        @p size: string.bytes(payload);
        if size == 0 { return false; };
        @p index: 0;
        @p negative: false;
        @p first: string.byte_at(payload, 0);
        if first == 45u8 or first == 43u8 {
            negative: first == 45u8;
            index: 1;
        };
        if index == size { return false; };
        @p limit: -9223372036854775807;
        if negative { limit: -9223372036854775808; };
        @p value: 0;
        while index < size {
            @p digit: decode(string.byte_at(payload, index));
            if digit < 0 or digit >= base { return false; };
            -- keep the accumulator negative so the minimum i64 never needs negating
            if value < limit / base { return false; };
            value: value * base;
            if value < limit + digit { return false; };
            value: value - digit;
            index: index + 1;
        };
        if not negative { value: -value; };
        return vector.push(output, value);
    };
    @r func unsigned[bool] :: payload:text, base:i64, @b output[u64] {
        if base < 2 or base > 36 { return false; };
        @p size: string.bytes(payload);
        if size == 0 { return false; };
        @p index: 0;
        if string.byte_at(payload, 0) == 43u8 { index: 1; };
        if index == size { return false; };
        @p value: 0u64;
        @p radix: u64(base);
        @p limit: 18446744073709551615u64;
        while index < size {
            @p decoded: decode(string.byte_at(payload, index));
            if decoded < 0 or decoded >= base { return false; };
            @p digit: u64(decoded);
            if value > (limit - digit) / radix { return false; };
            value: value * radix + digit;
            index: index + 1;
        };
        return vector.push(output, value);
    };
};
func decode[i64] :: raw:u8 {
    @p byte: i64(raw);
    if byte >= 48 and byte <= 57 { return byte - 48; };
    if byte >= 65 and byte <= 90 { return byte - 55; };
    if byte >= 97 and byte <= 122 { return byte - 87; };
    return -1;
};
