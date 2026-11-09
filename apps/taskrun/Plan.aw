use vendor/Json.aw as json;
func kind[i64] :: @b metadata[i64], i:i64 { return vector.get(metadata,2+i*2); };
func safe[bool] :: value:text {
    if string.bytes(value)>4096 { return false; };
    @p i:0;
    while i<string.bytes(value) {
        if string.byte_at(value,i)==0u8 { return false; };
        i:i+1;
    };
    return true;
};
exports{
 @r func parse[bool] :: source:text,@b tokens[text],@b metadata[i64],@b ranges[i64] {
    if not json.parse(source,tokens,metadata) { return false; };
    if kind(metadata,0)!=2 { return false; };
    @p i:1; @p jobs:0;
    while i<vector.length(tokens)-1 {
        if jobs==16 or kind(metadata,i)!=2 { return false; };
        i:i+1; @p start:i;
        while i<vector.length(tokens) and kind(metadata,i)==5 {
            if not safe(vector.get(tokens,i)) { return false; };
            i:i+1;
        };
        if i==start or i-start>129 or i>=vector.length(tokens) { return false; };
        if string.bytes(vector.get(tokens,start))==0 or kind(metadata,i)!=4 { return false; };
        if not vector.push(ranges,start) or not vector.push(ranges,i-start) { return false; };
        jobs:jobs+1; i:i+1;
    };
    return jobs>0 and i==vector.length(tokens)-1 and kind(metadata,i)==4;
 };
};
