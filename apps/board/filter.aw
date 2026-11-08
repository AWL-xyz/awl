use vendor/Json.aw as json;
use Rules.aw as rules;
use Store.aw as store;
func main: i64 {
    if arg_count() != 3 { return 2; };
    if not arg_text_valid(0) or not arg_text_valid(1) or not arg_text_valid(2) { return 2; };
    @p query: arg_text(1);
    @p filter: arg_text(2);
    if string.bytes(query) > 160 { return 2; };
    if filter != "all" and not rules.valid_status(filter) { return 2; };
    @s rows vector<text>: vector.new<text>(0);
    @s meta vector<i64>: vector.new<i64>(2);
    if not vector.valid(rows) or not vector.valid(meta) { return 9; };
    vector.push(meta, 0);
    vector.push(meta, 1);
    if not store.decode(arg_text(0), rows, meta) { return 4; };
    @p i: 0;
    while i < vector.length(rows) {
        if rules.visible(vector.get(rows, i + 1), vector.get(rows, i + 2), vector.get(rows, i + 3), query, filter) { print(vector.get(rows, i)); };
        i: i + 4;
    };
    return 0;
};
