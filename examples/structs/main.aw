-- structs, typed fields, initialization, field access and mutation
use Shape.aw as shape;

-- private struct with a nested struct field and an enum field
struct Size {
    w:i64;
    h:i64;
};

enum Kind Filled(color:string); Empty(); end;

struct Panel {
    size:Size;
    kind:Kind;
    title:string;
    visible:bool;
};

func area[i64] :: p:Panel {
    return p.size.w * p.size.h;
};

-- @m borrows the caller's struct in place, no copy and no return value needed
func stretch :: @m p:Panel, factor:i64 {
    p.size.w: p.size.w * factor;
    p.size.h: p.size.h * factor;
};

func rename[Panel] :: p:Panel, title:string {
    @p copy Panel: p;
    copy.title: title;
    return copy;
};

func main[i64] {
    -- structs of scalars/text/nested structs compare field-wise with == and !=
    @p same Size: Size(4,3);
    if same == Size(4,3) and same != Size(4,4) {
        print("struct equality ok");
    };
    @p panel Panel: Panel(Size(4,3),Kind.Filled("amber"),"dock",true);
    print(panel.size.w);
    print(panel.size.h);
    print(panel.title);
    print(area(panel));

    -- mutation through a local path, nested fields included
    panel.size.w: 6;
    panel.title: "dock v2";
    panel.visible: false;
    print(area(panel));
    print(panel.title);
    print(panel.visible);

    -- structs are values, a copy keeps the original intact
    @p taller Panel: rename(panel,"dock v3");
    print(taller.title);
    print(panel.title);

    -- match still binds the enum that lives inside the struct
    match panel.kind then
        case Kind.Filled(color) then print(color);
        case Kind.Empty() then print("empty");
    end;

    -- imported struct type, constructed and passed across the module boundary
    @p box shape.Box: shape.make_box(3,2,"crate");
    print(box.width * box.height);
    @p grown shape.Box: shape.grow(box,2);
    print(grown.width);
    print(grown.height);
    print(box.width);

    -- a mutable borrow edits the caller's value, an ordinary parameter edits a copy
    @p live Panel: Panel(Size(2,2),Kind.Empty(),"live",true);
    stretch(live,3);
    print(live.size.w);
    print(area(live));

    -- struct values in a fixed array
    @p row [Size;2]: [Size(1,1),Size(2,2)];
    row[0]: Size(5,5);
    print(row[0].w + row[1].h);
    print("structs done");
    return 0;
};
