use vendor/Json.aw as json;
use Rules.aw as rules;
func quote[bool] :: @b builder:spool, payload:text {
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
    return spool.append(builder, "\"") >= 0;
};
func decode_into[bool] :: source:text, @b rows[text], @b meta[i64] {
    @s tokens vector<text>: vector.new<text>(0);
    @s result vector<i64>: vector.new<i64>(0);
    if not vector.valid(tokens) or not vector.valid(result) { return false; };
    if not json.parse(source, tokens, result) { return false; };
    @p version: field("/version", 6, tokens, result);
    @p revision: field("/revision", 6, tokens, result);
    @p next: field("/next_id", 6, tokens, result);
    @p tasks: field("/tasks", 2, tokens, result);
    if version < 0 or revision < 0 or next < 0 or tasks < 0 { return false; };
    if vector.get(tokens, version) != "1" { return false; };
    @p rev: rules.integer(vector.get(tokens, revision));
    @p nextid: rules.integer(vector.get(tokens, next));
    if rev < 0 or rev > 10000 or nextid < 1 { return false; };
    @p count: 0;
    @p previous: 0;
    while count < 33 {
        @p prefix: "/tasks/" + string.from_i64(count);
        @p task: json.locate(prefix, tokens, result);
        if task == -1 {
            if vector.length(tokens) != 11 + count * 10 { return false; };
            vector.set(meta, 0, rev);
            vector.set(meta, 1, nextid);
            return true;
        };
        if count == 32 or task < 0 { return false; };
        @p id: field(prefix + "/id", 6, tokens, result);
        @p title: field(prefix + "/title", 5, tokens, result);
        @p note: field(prefix + "/note", 5, tokens, result);
        @p status: field(prefix + "/status", 5, tokens, result);
        if id < 0 or title < 0 or note < 0 or status < 0 { return false; };
        @p number: rules.integer(vector.get(tokens, id));
        if number <= previous or number >= nextid { return false; };
        if not rules.valid_title(vector.get(tokens, title)) or not rules.valid_note(vector.get(tokens, note)) or not rules.valid_status(vector.get(tokens, status)) { return false; };
        if not vector.reserve(rows, vector.length(rows) + 4) { return false; };
        vector.push(rows, vector.get(tokens, id));
        vector.push(rows, vector.get(tokens, title));
        vector.push(rows, vector.get(tokens, note));
        vector.push(rows, vector.get(tokens, status));
        previous: number;
        count: count + 1;
    };
    return false;
};
exports{
    @r func field[i64] :: pointer:text, kind:i64, @b tokens[text], @b result[i64] {
        @p found: json.locate(pointer, tokens, result);
        if found < 0 { return -1; };
        if vector.get(result, 2 + found * 2) != kind { return -1; };
        return found;
    };
    @r func decode[bool] :: source:text, @b rows[text], @b meta[i64] {
        if vector.length(rows) != 0 or vector.length(meta) != 2 { return false; };
        @s staged vector<text>: vector.new<text>(128);
        @s next vector<i64>: vector.new<i64>(2);
        if not vector.valid(staged) or not vector.valid(next) { return false; };
        vector.push(next, 0);
        vector.push(next, 1);
        if not decode_into(source, staged, next) { return false; };
        if not vector.reserve(rows, vector.length(staged)) { return false; };
        @p i: 0;
        while i < vector.length(staged) {
            vector.push(rows, vector.get(staged, i));
            i: i + 1;
        };
        vector.set(meta, 0, vector.get(next, 0));
        vector.set(meta, 1, vector.get(next, 1));
        return true;
    };
    @r func encode[bool] :: @b rows[text], @b meta[i64], @b output[text] {
        if vector.length(meta) != 2 or vector.length(rows) > 128 or vector.length(rows) % 4 != 0 { return false; };
        @s builder spool: spool.new(65536);
        if not spool.valid(builder) { return false; };
        if spool.append(builder, "{\"version\":1,\"revision\":" + string.from_i64(vector.get(meta, 0)) + ",\"next_id\":" + string.from_i64(vector.get(meta, 1)) + ",\"tasks\":[") < 0 { return false; };
        @p i: 0;
        while i < vector.length(rows) {
            if i > 0 {
                if spool.append(builder, ",") < 0 { return false; };
            };
            if spool.append(builder, "{\"id\":" + vector.get(rows, i) + ",\"title\":") < 0 { return false; };
            if not quote(builder, vector.get(rows, i + 1)) { return false; };
            if spool.append(builder, ",\"note\":") < 0 { return false; };
            if not quote(builder, vector.get(rows, i + 2)) { return false; };
            if spool.append(builder, ",\"status\":") < 0 { return false; };
            if not quote(builder, vector.get(rows, i + 3)) { return false; };
            if spool.append(builder, "}") < 0 { return false; };
            i: i + 4;
        };
        if spool.append(builder, "]}\n") < 0 { return false; };
        return vector.push(output, spool.snapshot(builder));
    };
    @r func load[bool] :: directory:text, buffer:i64, @b rows[text], @b meta[i64] {
        @p file: file_open(directory + "/board.json", 0);
        if file == -2 { return true; };
        if file < 0 { return false; };
        @p size: file_size(file);
        if size < 1 or size > 65536 { file_close(file); return false; };
        @p offset: 0;
        while offset < size {
            @p n: file_read(file, buffer, offset, size - offset);
            if n <= 0 { file_close(file); return false; };
            offset: offset + n;
        };
        if file_close(file) != 0 { return false; };
        if not buffer_text_valid(buffer, 0, size) { return false; };
        return decode(buffer_text(buffer, 0, size), rows, meta);
    };
    @r func save[i64] :: directory:text, source:text, buffer:i64 {
        @p file: file_open(directory + "/.board.tmp", 2);
        if file < 0 { return -1; };
        @p size: buffer_write_text(buffer, 0, source);
        if size < 0 { file_close(file); return -1; };
        @p offset: 0;
        while offset < size {
            @p n: file_write(file, buffer, offset, size - offset);
            if n <= 0 { file_close(file); return -1; };
            offset: offset + n;
        };
        if file_close(file) != 0 { return -1; };
        return file_replace(directory, ".board.tmp", "board.json");
    };
};
