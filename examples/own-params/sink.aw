function finish(own b:spool,n:i64)->i64
    if n==99999 then spool_print(b) end
    return spool_bytes(b)
end
function available(own b:spool)->bool
    return spool_valid(b)
end
