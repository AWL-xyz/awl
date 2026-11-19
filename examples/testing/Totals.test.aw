use Pricing.aw as pricing;

func main {
    if pricing.total(125, 3) != 375 {
        print("three items at 125 cents should total 375 cents");
        return 1;
    };
    if pricing.total(125, 0) != 0 {
        print("an empty order should cost nothing");
        return 1;
    };
    if pricing.total(125, -1) != -1 {
        print("negative quantities should be rejected");
        return 1;
    };
    return 0;
};
