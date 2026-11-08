-- structs may own map/set/vector/spool fields, the struct is then an @s owner
-- moved in through its constructor, borrowed with @m, freed field by field at scope exit
struct Inventory {
    stock:map<text,i64>;
    seen:set<text>;
    log:vector<i64>;
    label:string;
};

struct Shop {
    items:Inventory;
    name:string;
};

func restock :: @m inv:Inventory, item:text, count:i64 {
    map.set(inv.stock,item,count);
    set.add(inv.seen,item);
    vector.push(inv.log,count);
};

func total :: @m inv:Inventory: i64 {
    @p sum: 0;
    for item in inv.stock {
        sum: sum + map.get(inv.stock,item);
    };
    return sum;
};

-- owned result, the caller takes the whole struct
func make :: label:string: @o Inventory {
    @s stock map<text,i64>: map.new<text,i64>(4);
    @s seen set<text>: set.new<text>(4);
    @s log vector<i64>: vector.new<i64>(4);
    @s inv Inventory: Inventory(move stock,move seen,move log,label);
    return move inv;
};

func main: i64 {
    @s inv Inventory: make("dock");
    restock(inv,"bolt",40);
    restock(inv,"nut",25);
    print(total(inv));
    print(map.length(inv.stock));
    print(vector.length(inv.log));
    print("label ${inv.label}");

    -- nested: a struct owning another resource struct
    @s stock map<text,i64>: map.new<text,i64>(2);
    @s seen set<text>: set.new<text>(2);
    @s log vector<i64>: vector.new<i64>(2);
    @s inner Inventory: Inventory(move stock,move seen,move log,"inner");
    @s shop Shop: Shop(move inner,"corner");
    restock(shop.items,"gear",7);
    print(total(shop.items));
    return 0;
};
