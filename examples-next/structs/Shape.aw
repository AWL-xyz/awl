-- exported struct types travel between modules like exported enums do
exports{
    @r struct Box {
        width:i64;
        height:i64;
        name:string;
    };
    @r func make_box :: width:i64, height:i64, name:string: Box {
        return Box(width,height,name);
    };
    @r func grow :: box:Box, by:i64: Box {
        @p bigger Box: box;
        bigger.width: bigger.width + by;
        bigger.height: bigger.height + by;
        return bigger;
    };
};
