function positive(x: i64) -> bool
    return x > 0
end

function main() -> i64
    local ok: bool = positive(42) and not false
    if ok then
        print(true)
    else
        print(false)
    end
    return 0
end
