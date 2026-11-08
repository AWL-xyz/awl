use Library.aw as lib;
@p version: 999.0;
func main: i64 {
    print(lib.get_version());
    print(lib.fixed);
    lib.count: lib.count + 1;
    print(lib.count);
    print(lib.call_count());
    print(sqrt(81));
    print(sin(pi / 2));
    print(atan2(1, 1));
    return 0;
};
