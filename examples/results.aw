-- A concrete Result-like type, not a generic library Result[T,E].
struct Quotient
    value: i64
    exact: bool
end

union DivideResult
    Ok(result: Quotient)
    ZeroDivisor()
    Overflow(dividend: i64, divisor: i64)
end

function divide(a: i64, b: i64) -> DivideResult
    if b == 0 then
        return DivideResult.ZeroDivisor()
    end
    if a == -9223372036854775808 and b == -1 then
        return DivideResult.Overflow(a, b)
    end
    return DivideResult.Ok(Quotient(a / b, a % b == 0))
end

function display(r: DivideResult) -> unit
    match r then
        case DivideResult.Ok(q) then
            print(q.value)
            print(q.exact)
        case DivideResult.ZeroDivisor() then
            print(false)
        case DivideResult.Overflow(_, _) then
            print(-1)
    end
end

function main() -> i64
    display(divide(42, 6))
    display(divide(20, 3))
    display(divide(1, 0))
    display(divide(-9223372036854775808, -1))
    return 0
end
