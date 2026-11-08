import transfer
function main()->i64
    if arg_count()!=2 then print("usage: kcopy SOURCE DESTINATION (destination must not exist)") return 2 end
    if not arg_text_valid(0) or not arg_text_valid(1) then print("arguments must be UTF-8 text") return 2 end
    local source:i64=file_open(arg_text(0),0)
    if source<0 then print("cannot open source") print(source) return 3 end
    defer file_close(source)
    local destination:i64=file_open(arg_text(1),1)
    if destination<0 then print("cannot create destination") print(destination) return 4 end
    local count:i64=transfer.chunks(source,destination)
    local closed:i64=file_close(destination)
    if count<0 then print("copy failed; partial destination may remain") print(count) return 5 end
    if closed<0 then print("destination close failed") print(closed) return 5 end
    print("bytes copied")
    print(count)
    return 0
end
