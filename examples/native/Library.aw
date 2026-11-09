func private_bonus[i64] {
    return 1;
};
exports{
    @r func answer[i64] {
        @p func helper[i64] {
            @p value: 41;
            return value + private_bonus();
        };
        return helper();
    };
    @r func version[text] {
        @p func private_text[text] {
            @p value: "1.0.0";
            return value;
        };
        return private_text();
    };
};
