-- Experimental checked byte-buffer handles. Explicit lifetime, not ownership.
function main() -> i64
    local b: i64 = buffer_new(4)
    if b == 0 then return 1 end
    print(buffer_size(b))
    print(buffer_get(b,0))
    buffer_set(b,0,255u8)
    buffer_set(b,3,42u8)
    print(buffer_get(b,0))
    print(buffer_get(b,3))
    buffer_free(b)
    print(buffer_new(-1))
    return 0
end
