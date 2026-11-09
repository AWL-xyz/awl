enum IntegerResult
    Value(value:i64);
    Invalid(offset:i64);
    Overflow();
end;
enum Calculation
    Value(value:i64);
    OperandError(operand:text, issue:IntegerResult);
    BadOperator(operator:text);
    DivisionByZero();
    Overflow();
end;
func integer[IntegerResult] :: payload:text {
    @p size: string.bytes(payload);
    @p offset: 0;
    @p negative: false;
    if size == 0 { return IntegerResult.Invalid(0); };
    @p first: string.byte_at(payload, 0);
    if first == 45u8 or first == 43u8 { negative: first == 45u8; offset: 1; };
    if offset == size { return IntegerResult.Invalid(offset); };
    @p limit: -9223372036854775807;
    if negative { limit: -9223372036854775808; };
    @p value: 0;
    while offset < size {
        @p byte: string.byte_at(payload, offset);
        if byte < 48u8 or byte > 57u8 { return IntegerResult.Invalid(offset); };
        @p digit: i64(byte) - 48;
        if value < limit / 10 { return IntegerResult.Overflow(); };
        value: value * 10;
        if value < limit + digit { return IntegerResult.Overflow(); };
        value: value - digit;
        offset: offset + 1;
    };
    if not negative { value: -value; };
    return IntegerResult.Value(value);
};
func arithmetic[Calculation] :: operator:text, left:i64, right:i64 {
    @p maximum: 9223372036854775807;
    @p minimum: -9223372036854775808;
    if operator == "+" {
        if right > 0 and left > maximum - right { return Calculation.Overflow(); };
        if right < 0 and left < minimum - right { return Calculation.Overflow(); };
        return Calculation.Value(left + right);
    };
    if operator == "-" {
        if right < 0 and left > maximum + right { return Calculation.Overflow(); };
        if right > 0 and left < minimum + right { return Calculation.Overflow(); };
        return Calculation.Value(left - right);
    };
    if operator == "*" {
        if left > 0 {
            if right > 0 and left > maximum / right { return Calculation.Overflow(); };
            if right < 0 and right < minimum / left { return Calculation.Overflow(); };
        } else {
            if left < 0 {
                if right > 0 and left < minimum / right { return Calculation.Overflow(); };
                if right < 0 and left < maximum / right { return Calculation.Overflow(); };
            };
        };
        return Calculation.Value(left * right);
    };
    if operator == "/" {
        if right == 0 { return Calculation.DivisionByZero(); };
        if left == minimum and right == -1 { return Calculation.Overflow(); };
        return Calculation.Value(left / right);
    };
    return Calculation.BadOperator(operator);
};
func calculate[Calculation] :: operator:text, left:text, right:text {
    @p first: integer(left);
    match first then
        case IntegerResult.Value(a) then
            @p second: integer(right);
            match second then
                case IntegerResult.Value(b) then return arithmetic(operator, a, b);
                case IntegerResult.Invalid(_) then return Calculation.OperandError("right", second);
                case IntegerResult.Overflow() then return Calculation.OperandError("right", second);
            end;
        case IntegerResult.Invalid(_) then return Calculation.OperandError("left", first);
        case IntegerResult.Overflow() then return Calculation.OperandError("left", first);
    end;
};
func main[i64] {
    if arg_count() != 3 { return 2; };
    @p i: 0;
    while i < 3 { if not arg_text_valid(i) { return 2; }; i: i + 1; };
    match calculate(arg_text(0), arg_text(1), arg_text(2)) then
        case Calculation.Value(value) then print(value); return 0;
        case Calculation.BadOperator(operator) then print("unknown operator: " + operator); return 2;
        case Calculation.DivisionByZero() then print("division by zero"); return 4;
        case Calculation.Overflow() then print("arithmetic overflow"); return 4;
        case Calculation.OperandError(operand, issue) then
            match issue then
                case IntegerResult.Value(_) then return 6;
                case IntegerResult.Invalid(offset) then print(operand + " invalid at byte " + string.from_i64(offset)); return 3;
                case IntegerResult.Overflow() then print(operand + " integer overflow"); return 3;
            end;
    end;
};
