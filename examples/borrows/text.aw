function append_frame(borrow b:spool,n:i64)->i64
    spool_clear(b)
    if spool_append(b,"frame=")!=0 then return -1 end
    if spool_i64(b,n)!=0 then return -2 end
    return spool_bytes(b)
end
