use Json.aw as json;
func main[i64] {
    if arg_count() != 2 { print("arguments"); return 2; };
    if not arg_text_valid(0) or not arg_text_valid(1) { print("utf8"); return 2; };
    @p source: arg_text(0);
    @p pointer: arg_text(1);
    @s tokens vector<text>: vector.new<text>(0);
    @s result vector<i64>: vector.new<i64>(0);
    if not vector.valid(tokens) or not vector.valid(result) { print("allocation"); return 9; };
    if not json.parse(source,tokens,result) {
        if vector.length(result)<2 { print("allocation"); return 9; };
        print("parse");
        print(vector.get(result,0));
        print(vector.get(result,1));
        return 4;
    };
    @p selected: json.locate(pointer,tokens,result);
    if selected<0 { print("selection"); print(selected); return 5; };
    print("ok");
    print(vector.get(result,2+selected*2));
    print(vector.length(tokens));
    print(vector.get(tokens,selected));
    return 0;
};
