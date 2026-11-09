-- Library.aw, the imported side of the tour
-- A module is one .aw file, `use Library.aw as lib;` imports it under an alias
-- top-level `@p` declarations are private to this file, importers never see them

@p threshold: 3;
@p calls: 0;
enum Internal Missing(); end;              -- private enum, only usable here

exports{
    @r version: "0.26";                    -- @r variable, importers may read it
    @r limit: 10;
    @w counter: 0;                         -- @w variable, importers may read and write it

    @r enum Grade Pass(score:i64); Fail(reason:text); end;
    @r enum Ticket Id(number:i64); None(); end;

    @r func label[text] {                  -- parameterless function, result annotation after ':'
        return "library "..version;
    };

    @r func grade[Grade] :: score:i64 {    -- `::` starts the parameter list, no parentheses
        if score >= 90 {
            return Grade.Pass(score);
        };
        return Grade.Fail("below the bar");
    };

    @r func bump[i64] :: step:i64 {         -- exported function touching private module state
        counter: counter + step;
        calls: calls + 1;
        return counter;
    };

    @r func call_count[i64] {
        return calls;
    };

    @r func nearest_ticket[Ticket] :: number:i64 {
        @p func inside[bool] :: value:i64 {  -- nested helper, private to this function body
            return value > 0;               -- helpers capture nothing, pass parent values in
        };
        if inside(number) {
            return Ticket.Id(number);
        };
        return Ticket.None();
    };

    @r func total_of[i64] :: @b values[i64] {  -- `@b name[T]` is a borrowed vector parameter
        @p sum: 0;
        @p i: 0;
        while i < vector.length(values) {
            sum: sum + vector.get(values,i);
            i: i + 1;
        };
        return sum;
    };
};
