exports{
    @r func stable :: @b rows[text]: bool {
        @p count: vector.length(rows);
        @s scratch vector<text>: vector.slice(rows, 0, count);
        if not vector.valid(scratch) { return false; };
        @p width: 1;
        while width < count {
            merge(rows, scratch, width);
            merge(scratch, rows, width * 2);
            width: width * 4;
        };
        return true;
    };
};
func merge :: @b source[text], @b target[text], width:i64 {
    @p count: vector.length(source);
    @p start: 0;
    while start < count {
        @p middle: start + width;
        if middle > count { middle: count; };
        @p finish: middle + width;
        if finish > count { finish: count; };
        @p left: start;
        @p right: middle;
        @p out: start;
        while out < finish {
            @p take_left: false;
            if left < middle {
                if right == finish {
                    take_left: true;
                } else {
                    take_left: string.compare(vector.get(source, left), vector.get(source, right)) <= 0;
                };
            };
            if take_left {
                vector.set(target, out, vector.get(source, left));
                left: left + 1;
            } else {
                vector.set(target, out, vector.get(source, right));
                right: right + 1;
            };
            out: out + 1;
        };
        start: finish;
    };
};
