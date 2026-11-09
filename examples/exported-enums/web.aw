use Config.aw as config;
use File.aw as file;
func main[i64] {
    if arg_count() != 1 { print("usage: configcheck-json JSON"); return 2; };
    if not arg_text_valid(0) { return 2; };
    match config.parse(arg_text(0)) then
        case config.Result.Loaded(settings) then
            match settings then
                case config.Settings.Profile(host, port, debug) then
                    print(host); print(port); print(debug); return 0;
            end;
        case config.Result.FileIssue(issue) then
            match issue then
                case file.Issue.Missing() then print("missing"); return 3;
                case file.Issue.Io(code) then print("io"); print(code); return 3;
                case file.Issue.TooLarge(bytes) then print("limit"); print(bytes); return 3;
            end;
        case config.Result.Malformed(offset) then print("json"); print(offset); return 4;
        case config.Result.Schema(field) then print("schema"); print(field); return 5;
        case config.Result.Resource() then print("resource"); return 9;
    end;
};
