import text
function demo(b:spool)->i64
    text.append(b,"Awl café | ")
    spool_i64(b,42)
    spool_print(b)
    print(spool_length(b))
    print(spool_bytes(b))
    spool_clear(b)
    match text.codepoint(b,55296u32) then
    case text.Status.Ok() then return 2
    case text.Status.Capacity() then return 3
    case text.Status.InvalidScalar() then print("Invalid scalar: recovered")
    case text.Status.IO() then return 4
    case text.Status.Unknown(code) then return code
    end
    local i:i64=0
    while i<100000 do
        spool_clear(b)
        if spool_append(b,"frame=")!=0 then return 5 end
        if spool_i64(b,i)!=0 then return 6 end
        i=i+1
    end
    spool_print(b)
    print("100000 updates, one reusable builder")
    return 0
end
function main()->i64
    match text.create(64) then
    case text.Created.Ready(b) then
        local result:i64=demo(b)
        spool_free(b)
        return result
    case text.Created.Unavailable() then return 1
    end
end
