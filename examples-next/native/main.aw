use Library.aw as lib;
func private_bonus: i64 {
    return 1000;
};
func main: i64 {
    @p count: 3;
    while count > 0 {
        count: count - 1;
    };
    if count == 0 {
        print(lib.answer());
        print(lib.version());
    } else {
        return 9;
    };
    return 0;
};
