use File.aw as file;
use vendor/Json.aw as json;
func field[i64] :: name:text, @b tokens[text], @b metadata[i64] {
    return json.locate("/" + name, tokens, metadata);
};
func port[i64] :: value:text {
    if string.bytes(value) == 0 or string.bytes(value) > 5 { return -1; };
    @p i: 0;
    @p result: 0;
    while i < string.bytes(value) {
        @p byte: i64(string.byte_at(value, i));
        if byte < 48 or byte > 57 { return -1; };
        result: result * 10 + byte - 48;
        i: i + 1;
    };
    if result < 1 or result > 65535 { return -1; };
    return result;
};
exports{
    @r enum Settings
        Profile(host:text, port:i64, debug:bool);
    end;
    @r enum Result
        Loaded(settings:Settings);
        FileIssue(issue:file.Issue);
        Malformed(offset:i64);
        Schema(field:text);
        Resource();
    end;
    @r func parse[Result] :: source:text {
        @s tokens vector<text>: vector.new<text>(0);
        @s metadata vector<i64>: vector.new<i64>(0);
        if not vector.valid(tokens) or not vector.valid(metadata) { return Result.Resource(); };
        if not json.parse(source, tokens, metadata) {
            if vector.length(metadata) < 2 { return Result.Resource(); };
            return Result.Malformed(vector.get(metadata, 1));
        };
        @p host: field("host", tokens, metadata);
        @p number: field("port", tokens, metadata);
        @p debug: field("debug", tokens, metadata);
        if host < 0 { return Result.Schema("host"); };
        if number < 0 { return Result.Schema("port"); };
        if debug < 0 { return Result.Schema("debug"); };
        if vector.length(tokens) != 8 { return Result.Schema("keys"); };
        if vector.get(metadata, 2 + host * 2) != 5 { return Result.Schema("host"); };
        @p hostname: vector.get(tokens, host);
        if string.bytes(hostname) == 0 or string.bytes(hostname) > 253 { return Result.Schema("host"); };
        @p i: 0;
        while i < string.length(hostname) {
            @p cp: string.codepoint(hostname, i);
            if cp <= 32u32 or cp == 127u32 { return Result.Schema("host"); };
            i: i + 1;
        };
        if vector.get(metadata, 2 + number * 2) != 6 { return Result.Schema("port"); };
        @p parsed: port(vector.get(tokens, number));
        if parsed < 0 { return Result.Schema("port"); };
        @p kind: vector.get(metadata, 2 + debug * 2);
        if kind != 7 and kind != 8 { return Result.Schema("debug"); };
        return Result.Loaded(Settings.Profile(hostname, parsed, kind == 7));
    };
    @r func load[Result] :: path:text {
        match file.read(path) then
            case file.Read.Text(source) then return parse(source);
            case file.Read.Failed(issue) then return Result.FileIssue(issue);
        end;
    };
};
