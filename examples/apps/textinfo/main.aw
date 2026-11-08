-- Bounded UTF-8 file inspection. Counts Unicode scalars, NOT grapheme clusters.
function main()->i64
    if arg_count()!=1 then print("usage: textinfo UTF8_FILE") return 2 end
    if not arg_text_valid(0) then print("argument must be UTF-8") return 2 end
    local f:i64=file_open(arg_text(0),0)
    if f<0 then print("cannot open file") print(f) return 3 end
    defer file_close(f)
    local size:i64=file_size(f)
    if size<0 or size>8388608 then print("file size unavailable or exceeds 8 MiB") return 4 end
    local b:i64=buffer_new(size+1)
    if b==0 then return 4 end
    defer buffer_free(b)
    local count:i64=0
    local reading:bool=true
    while reading do
        local part:i64=file_read(f,b,count,size+1-count)
        if part<0 then print("read failed") print(part) return 4 end
        if part==0 then reading=false else count=count+part end
        if count>size then print("file grew while reading") return 4 end
    end
    if not buffer_text_valid(b,0,count) then print("invalid UTF-8") return 5 end
    local text:string=buffer_text(b,0,count)
    print("bytes") print(string_bytes(text))
    print("Unicode scalars") print(string_length(text))
    return 0
end
