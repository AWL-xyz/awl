-- Streaming arbitrary bytes, not UTF-8 decoding. Handles partial OS writes.
function chunks(source:i64,destination:i64)->i64
    local bytes:i64=buffer_new(65536)
    if bytes==0 then return -9 end
    defer buffer_free(bytes)
    local total:i64=0
    local reading:bool=true
    while reading do
        local count:i64=file_read(source,bytes,0,65536)
        if count<0 then return count end
        if count==0 then
            reading=false
        else
            local written:i64=0
            while written<count do
                local part:i64=file_write(destination,bytes,written,count-written)
                if part<0 then return part end
                if part==0 then return -1 end
                written=written+part
            end
            total=total+count
        end
    end
    local status:i64=file_flush(destination)
    if status<0 then return status end
    return total
end
