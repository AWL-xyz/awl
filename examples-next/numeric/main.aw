func identity :: x:f64: f64 {
    return x;
};
func main: i64 {
    @p version: 128.59;
    print(version);
    print(identity(128.59));
    print(sin(pi / 2));
    print(cos(0));
    print(sqrt(81));
    print(atan2(1, 1));
    print(tau);
    print(identity(2));
    print(f64(3));
    return 0;
};
