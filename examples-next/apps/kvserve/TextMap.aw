func lower :: @b pairs[text], key:text: i64 {
    @p low: 0;
    @p high: vector.length(pairs) / 2;
    while low < high {
        @p middle: (low + high) / 2;
        if string.compare(vector.get(pairs, middle * 2), key) < 0 { low: middle + 1; } else { high: middle; };
    };
    return low * 2;
};
exports{
    @r func find :: @b pairs[text], key:text: i64 {
        if vector.length(pairs) % 2 != 0 { return -2; };
        @p at: lower(pairs, key);
        if at == vector.length(pairs) { return -1; };
        if vector.get(pairs, at) != key { return -1; };
        return at + 1;
    };
    @r func put :: @b pairs[text], key:text, value:text: bool {
        @p size: vector.length(pairs);
        if size % 2 != 0 { return false; };
        @p at: lower(pairs, key);
        if at < size {
            if vector.get(pairs, at) == key { vector.set(pairs, at + 1, value); return true; };
        };
        if not vector.reserve(pairs, size + 2) { return false; };
        if not vector.insert(pairs, at, key) { return false; };
        if not vector.insert(pairs, at + 1, value) { vector.remove(pairs, at); return false; };
        return true;
    };
    @r func remove :: @b pairs[text], key:text: bool {
        @p at: find(pairs, key);
        if at < 0 { return false; };
        vector.remove(pairs, at - 1);
        vector.remove(pairs, at - 1);
        return true;
    };
};
