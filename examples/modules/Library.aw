@p version: 128.59;
@p calls: 0;
exports{
    @r fixed: 42;
    @w count: 1;
    @r func get_version[f64] {
        @p func helper[f64] {
            calls: calls + 1;
            return version;
        };
        return helper();
    };
    @r func call_count[i64] {
        return calls;
    };
};
