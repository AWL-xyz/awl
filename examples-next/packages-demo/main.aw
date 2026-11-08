-- installed packages live in packages/NAME/NAME.awpkg, bare `use NAME;` selects them and never falls back to local files
use env;
use json;

func main: i64 {
    @s keys vector<text>: vector.new<text>(4);
    @s values vector<text>: vector.new<text>(4);
    @s result vector<i64>: vector.new<i64>(2);
    vector.push(result, 0);
    vector.push(result, 0);
    if not env.parse("HOST=localhost\nPORT=8080 # default\n", keys, values, result) { return 1; };
    print(env.get("HOST", keys, values, "?"));
    print(env.get("PORT", keys, values, "?"));

    @s tokens vector<text>: vector.new<text>(8);
    @s metadata vector<i64>: vector.new<i64>(16);
    vector.push(metadata, 0);
    vector.push(metadata, 0);
    if json.parse("{\"port\":8080}", tokens, metadata) { print("json ok"); };
    return 0;
};
