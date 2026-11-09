@p version: "1.0.0";
@p private_message: "only Template can access this";
exports{
    @r var1: "readonly variable";
    @w variable: "readwrite variable";
    @r func get_version[text] {
        @p func helper[text] {
            return version;
        };
        return helper();
    };
};
