use File.aw as file;
use Display.aw as display;
func show :: source:text, first:i64, count:i64: i64 {
    @s lines vector<text>: vector.new<text>(0);
    @s line spool: spool.new(64);
    if not vector.valid(lines) or not spool.valid(line) { return 9; };
    @p i: 0;
    while i < string.length(source) {
        @p cp: string.codepoint(source, i);
        if cp == 10u32 or cp == 13u32 {
            if vector.length(lines) == 4096 { print("too many lines"); return 4; };
            if not vector.push(lines, spool.snapshot(line)) { return 9; };
            spool.clear(line);
            if cp == 13u32 and i + 1 < string.length(source) {
                if string.codepoint(source, i + 1) == 10u32 { i: i + 1; };
            };
        } else {
            if (cp < 32u32 and cp != 9u32) or cp == 127u32 { print("unsupported control character"); return 4; };
            @p width: 1;
            if cp >= 65536u32 { width: 4; } elseif cp >= 2048u32 { width: 3; } elseif cp >= 128u32 { width: 2; };
            @p need: spool.bytes(line) + width;
            if need > 4096 { print("line exceeds 4096 bytes"); return 4; };
            if need > spool.capacity(line) {
                @p capacity: spool.capacity(line) * 2;
                while capacity < need { capacity: capacity * 2; };
                if capacity > 4096 { capacity: 4096; };
                if not spool.reserve(line, capacity) { return 9; };
            };
            if spool.codepoint(line, cp) != 0 { print("line exceeds 4096 bytes"); return 4; };
        };
        i: i + 1;
    };
    if spool.bytes(line) > 0 {
        if vector.length(lines) == 4096 { print("too many lines"); return 4; };
        if not vector.push(lines, spool.snapshot(line)) { return 9; };
    };
    if first < 1 or first - 1 > vector.length(lines) { print("invalid range"); return 2; };
    if count < 0 or count > vector.length(lines) - (first - 1) { print("invalid range"); return 2; };
    @p window: vector.view(lines, first - 1, count);
    display.render(window, first);
    return 0;
};
func main: i64 {
    if arg_count() != 3 { print("usage: logwindow FILE FIRST_LINE COUNT"); return 2; };
    if not arg_text_valid(0) or not arg_i64_valid(1) or not arg_i64_valid(2) { return 2; };
    match file.read(arg_text(0)) then
        case file.Read.Text(source) then return show(source, arg_i64(1), arg_i64(2));
        case file.Read.Failed(issue) then
            match issue then
                case file.Issue.Missing() then print("missing file"); return 3;
                case file.Issue.Io(code) then print("io error"); print(code); return 3;
                case file.Issue.TooLarge(bytes) then print("file exceeds 16384 bytes"); print(bytes); return 3;
            end;
    end;
};
