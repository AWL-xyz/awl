function main() -> i64
    local text: string = "Awl café"
    print("Hello, " + text + "!")
    print("Scalars: " + string_from_i64(string_length(text)))
    print("Bytes: " + string_from_i64(string_bytes(text)))
    print("Slice: " + string_slice(text,5,4))
    print(string_codepoint(text,8) == 233u32)
    return 0
end
