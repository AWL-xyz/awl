func reverse :: @b rows[text] {
    @p left: 0;
    @p right: vector.length(rows)-1;
    while left<right {
        vector.swap(rows,left,right);
        left: left+1;
        right: right-1;
    };
};
func main[i64] {
    @s rows vector<text>: vector.new<text>(4);
    if not vector.valid(rows) { return 9; };
    if not vector.push(rows,"alpha") or not vector.push(rows,"beta") or not vector.push(rows,"gamma") { return 9; };
    reverse(rows);
    if not vector.truncate(rows,2) { return 1; };
    print(vector.get(rows,0));
    print(vector.get(rows,1));
    print("capacity: "+string.from_i64(vector.capacity(rows)));
    print("length: "+string.from_i64(vector.length(rows)));
    return 0;
};
