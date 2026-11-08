-- Awl bootstrap: static types, checked arithmetic, native output.
function factorial(n: i64) -> i64
    if n <= 1 then
        return 1
    else
        return n * factorial(n - 1)
    end
end

function main() -> i64
    local i: i64 = 1
    while i <= 10 do
        print(factorial(i))
        i = i + 1
    end
    return 0
end
