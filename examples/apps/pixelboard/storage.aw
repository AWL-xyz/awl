-- KPBOARD1:8-byte magic,384RGB triples (24x16,row-major),4-byte BE Adler32.
-- Exclusive create, not overwrite/atomic replacement. A failed save may remain.
function checksum(bytes:i64)->i64
    local a:i64=1
    local b:i64=0
    local i:i64=0
    while i<1160 do
        a=a+i64(buffer_get(bytes,i))
        b=b+a
        i=i+1
    end
    -- Fixed1160-byte input: a<=295801,b<=171713060; both far below i64.
    return (b%65521)*65536+a%65521
end
function put32(bytes:i64,offset:i64,value:i64)->unit
    buffer_set(bytes,offset,u8(value/16777216))
    buffer_set(bytes,offset+1,u8(value/65536%256))
    buffer_set(bytes,offset+2,u8(value/256%256))
    buffer_set(bytes,offset+3,u8(value%256))
end
function get32(bytes:i64,offset:i64)->i64
    return i64(buffer_get(bytes,offset))*16777216+i64(buffer_get(bytes,offset+1))*65536+i64(buffer_get(bytes,offset+2))*256+i64(buffer_get(bytes,offset+3))
end
function encode(borrow cells:int_vector,bytes:i64)->i64
    if int_vector_length(cells)!=384 then return -5 end
    buffer_write_text(bytes,0,"KPBOARD1")
    local i:i64=0
    while i<384 do
        local color:i64=int_vector_get(cells,i)
        if color<0 or color>16777215 then return -5 end
        local at:i64=8+i*3
        buffer_set(bytes,at,u8(color/65536))
        buffer_set(bytes,at+1,u8(color/256%256))
        buffer_set(bytes,at+2,u8(color%256))
        i=i+1
    end
    put32(bytes,1160,checksum(bytes))
    return 0
end
function write_all(f:i64,bytes:i64)->i64
    local count:i64=0
    while count<1164 do
        local part:i64=file_write(f,bytes,count,1164-count)
        if part<0 then return part end
        if part==0 then return -1 end
        count=count+part
    end
    return 0
end
function save_new(borrow cells:int_vector,path:string)->i64
    local bytes:i64=buffer_new(1164)
    if bytes==0 then return -9 end
    defer buffer_free(bytes)
    local status:i64=encode(cells,bytes)
    if status<0 then return status end
    local f:i64=file_open(path,1)
    if f<0 then return f end
    status=write_all(f,bytes)
    if status==0 then status=file_flush(f) end
    local closed:i64=file_close(f)
    if status<0 then return status end
    return closed
end
function valid(bytes:i64)->bool
    if buffer_get(bytes,0)!=75u8 or buffer_get(bytes,1)!=80u8 or buffer_get(bytes,2)!=66u8 or buffer_get(bytes,3)!=79u8 or buffer_get(bytes,4)!=65u8 or buffer_get(bytes,5)!=82u8 or buffer_get(bytes,6)!=68u8 or buffer_get(bytes,7)!=49u8 then return false end
    return get32(bytes,1160)==checksum(bytes)
end
function load(borrow cells:int_vector,path:string)->i64
    if int_vector_length(cells)!=384 then return -5 end
    local f:i64=file_open(path,0)
    if f<0 then return f end
    defer file_close(f)
    local size:i64=file_size(f)
    if size<0 then return size end
    if size!=1164 then return -5 end
    local bytes:i64=buffer_new(1165)
    if bytes==0 then return -9 end
    defer buffer_free(bytes)
    local count:i64=0
    local reading:bool=true
    while reading do
        local part:i64=file_read(f,bytes,count,1165-count)
        if part<0 then return part end
        if part==0 then reading=false else count=count+part end
        if count>1164 then return -5 end
    end
    if count!=1164 then return -5 end
    if not valid(bytes) then return -5 end
    -- Commit only after full length/magic/checksum validation. No allocations here.
    local i:i64=0
    while i<384 do
        local at:i64=8+i*3
        local color:i64=i64(buffer_get(bytes,at))*65536+i64(buffer_get(bytes,at+1))*256+i64(buffer_get(bytes,at+2))
        int_vector_set(cells,i,color)
        i=i+1
    end
    return 0
end
