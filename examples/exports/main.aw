use Template.aw as t;
func main[i64] {
    print(t.var1);
    t.variable: "updated value";
    print(t.get_version());
    return 0;
};
