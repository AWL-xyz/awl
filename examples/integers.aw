-- Integer widths are part of the type; literals do not infer their width.
struct Header
    version: u8
    length: u16
    offset: u32
end

union ByteResult
    Value(value: u8)
    OutOfRange(original: i64)
end

function try_byte(x: i64) -> ByteResult
    if x < 0 or x > 255 then
        return ByteResult.OutOfRange(x)
    end
    -- Conversions are checked at runtime; this guard ensures u8(x) fits.
    return ByteResult.Value(u8(x))
end

function main() -> i64
    local h: Header = Header(1u8, 4096u16, 65536u32)
    local length: u64 = u64(h.length) + u64(h.version)
    print(length)
    print(-128i8)
    print(32767i16)
    print(2147483647i32)
    match try_byte(255) then
        case ByteResult.Value(byte) then
            print(byte)
        case ByteResult.OutOfRange(value) then
            print(value)
    end
    return 0
end
