use TextMap.aw as textmap;
func name[text] :: prefix:text, sequence:i64 {
    return prefix + "." + string.fromi64(sequence) + ".kvs";
};
func checksum[i64] :: buffer:i64, count:i64 {
    @p a: 1;
    @p b: 0;
    @p i: 0;
    while i < count {
        a: (a + i64(buffer.get(buffer, i))) % 65521;
        b: (b + a) % 65521;
        i: i + 1;
    };
    return b * 65536 + a;
};
func put32 :: buffer:i64, offset:i64, value:i64 {
    buffer.set(buffer, offset, u8(value / 16777216));
    buffer.set(buffer, offset + 1, u8(value / 65536 % 256));
    buffer.set(buffer, offset + 2, u8(value / 256 % 256));
    buffer.set(buffer, offset + 3, u8(value % 256));
};
func read_record[bool] :: file:i64, buffer:i64, sequence:i64, @b draft[text] {
    @p size: file.size(file);
    if size < 17 or size > 1104 { return false; };
    @p offset: 0;
    while offset < size {
        @p n: file.read(file, buffer, offset, size - offset);
        if n <= 0 { return false; };
        offset: offset + n;
    };
    if file.read(file, buffer, size, 1) != 0 { return false; };
    if buffer.get(buffer, 0) != 75u8 or buffer.get(buffer, 1) != 86u8 or buffer.get(buffer, 2) != 83u8 or buffer.get(buffer, 3) != 49u8 { return false; };
    @p operation: buffer.get(buffer, 4);
    @p keys: i64(buffer.get(buffer, 5));
    @p values: i64(buffer.get(buffer, 6)) * 256 + i64(buffer.get(buffer, 7));
    @p seq: i64(buffer.get(buffer, 8)) * 256 + i64(buffer.get(buffer, 9));
    if keys < 1 or keys > 64 or values > 1024 or size != 16 + keys + values or seq != sequence { return false; };
    if buffer.get(buffer, 10) != 0u8 or buffer.get(buffer, 11) != 0u8 { return false; };
    if operation != 1u8 and operation != 2u8 { return false; };
    if operation == 2u8 and values != 0 { return false; };
    @p at: size - 4;
    @p stored: i64(buffer.get(buffer, at)) * 16777216 + i64(buffer.get(buffer, at + 1)) * 65536 + i64(buffer.get(buffer, at + 2)) * 256 + i64(buffer.get(buffer, at + 3));
    if stored != checksum(buffer, at) { return false; };
    if not buffer.textvalid(buffer, 12, keys + values) { return false; };
    @p key: buffer.text(buffer, 12, keys);
    if not valid_key(key) { return false; };
    if operation == 2u8 { return textmap.remove(draft, key); };
    if textmap.find(draft, key) < 0 and vector.length(draft) == 256 { return false; };
    return textmap.put(draft, key, buffer.text(buffer, 12 + keys, values));
};
exports{
    @r func valid_key[bool] :: key:text {
        @p size: string.bytes(key);
        if size < 1 or size > 64 { return false; };
        @p i: 0;
        while i < size {
            @p byte: string.byteat(key, i);
            if not ((byte >= 65u8 and byte <= 90u8) or (byte >= 97u8 and byte <= 122u8) or (byte >= 48u8 and byte <= 57u8) or byte == 45u8 or byte == 95u8) { return false; };
            i: i + 1;
        };
        return true;
    };
    @r func load[i64] :: prefix:text, buffer:i64, @b pairs[text] {
        if buffer.size(buffer) < 1105 or vector.length(pairs) != 0 { return -5; };
        @s draft vector<text>: vector.new<text>(0);
        if not vector.valid(draft) { return -9; };
        @p sequence: 1;
        @p committed: 0;
        @p gap: false;
        while sequence <= 257 {
            @p file: file.open(name(prefix, sequence), 0);
            if file == -2 {
                gap: true;
            } else {
                if file < 0 { return file; };
                if gap or sequence == 257 { file.close(file); return -5; };
                @p valid: read_record(file, buffer, sequence, draft);
                @p closed: file.close(file);
                if not valid or closed < 0 { return -5; };
                committed: sequence;
            };
            sequence: sequence + 1;
        };
        if not vector.reserve(pairs, vector.length(draft)) { return -9; };
        @p i: 0;
        while i < vector.length(draft) {
            if not vector.push(pairs, vector.get(draft, i)) { vector.clear(pairs); return -9; };
            i: i + 1;
        };
        return committed;
    };
    @r func append[bool] :: prefix:text, sequence:i64, operation:i64, key:text, value:text, buffer:i64 {
        if buffer.size(buffer) < 1104 { return false; };
        if sequence < 1 or sequence > 256 or not valid_key(key) or string.bytes(value) > 1024 { return false; };
        if operation != 1 and operation != 2 { return false; };
        if operation == 2 and string.bytes(value) != 0 { return false; };
        buffer.writetext(buffer, 0, "KVS1");
        buffer.set(buffer, 4, u8(operation));
        buffer.set(buffer, 5, u8(string.bytes(key)));
        buffer.set(buffer, 6, u8(string.bytes(value) / 256));
        buffer.set(buffer, 7, u8(string.bytes(value) % 256));
        buffer.set(buffer, 8, u8(sequence / 256));
        buffer.set(buffer, 9, u8(sequence % 256));
        buffer.set(buffer, 10, 0u8);
        buffer.set(buffer, 11, 0u8);
        buffer.writetext(buffer, 12, key);
        buffer.writetext(buffer, 12 + string.bytes(key), value);
        @p size: 12 + string.bytes(key) + string.bytes(value);
        put32(buffer, size, checksum(buffer, size));
        size: size + 4;
        @p file: file.open(name(prefix, sequence), 1);
        if file < 0 { return false; };
        @p offset: 0;
        while offset < size {
            @p n: file.write(file, buffer, offset, size - offset);
            if n <= 0 { file.close(file); return false; };
            offset: offset + n;
        };
        @p flushed: file.flush(file);
        @p closed: file.close(file);
        return flushed == 0 and closed == 0;
    };
};
