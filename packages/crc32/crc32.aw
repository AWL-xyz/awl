-- Streaming CRC-32/ISO-HDLC over bytes. Keep the unfinalized state between chunks.
exports{
    @r func start[u32] {
        return 4294967295u32;
    };

    @r func update[u32] :: state:u32, bytes:i64, offset:i64, count:i64 {
        @p size: buffer.size(bytes);
        if offset < 0 or offset > size or count < 0 or count > size - offset {
            -- Report the usual buffer range trap without attempting offset + count.
            buffer.findbyte(bytes, offset, count, 0u8);
            return state;
        };
        if count == 0 { return state; };

        -- The 16 remainders for four reflected steps with polynomial 0xEDB88320.
        -- For each starting nibble, repeat: shift right once, XOR the polynomial
        -- if the bit shifted out was one. Two table lookups process a byte.
        @p table: [
            0u32, 498536548u32, 997073096u32, 651767980u32,
            1994146192u32, 1802195444u32, 1303535960u32, 1342533948u32,
            3988292384u32, 4027552580u32, 3604390888u32, 3412177804u32,
            2607071920u32, 2262029012u32, 2685067896u32, 3183342108u32
        ];
        @p crc: state;
        @p end_offset: offset + count;
        for i in offset..end_offset {
            crc: bits.xor(crc, u32.convert(buffer.get(bytes, i)));
            crc: bits.xor(bits.shr(crc, 4), table[i64.convert(bits.and(crc, 15u32))]);
            crc: bits.xor(bits.shr(crc, 4), table[i64.convert(bits.and(crc, 15u32))]);
        };
        return crc;
    };

    @r func finish[u32] :: state:u32 {
        return bits.not(state);
    };
};
