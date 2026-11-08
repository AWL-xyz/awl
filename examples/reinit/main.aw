function finish(own b:spool,n:i64)->i64
    if n==99999 then spool_print(b) end
    return spool_bytes(b)
end
function make(n:i64)->own spool
    scoped b:spool=spool_new(32)
    spool_append(b,"restored=")
    spool_i64(b,n)
    return move b
end
function frame(n:i64)->i64
    scoped b:spool=spool_new(32)
    spool_append(b,"first=")
    spool_i64(b,n)
    local first:i64=finish(move b,-1)
    b=make(n)
    local second:i64=finish(move b,n)
    b=spool_new(0)
    return first+second
end
function main()->i64
    local i:i64=0
    local total:i64=0
    while i<100000 do
        total=total+frame(i)
        i=i+1
    end
    print("100000 owner reinitializations: original cleanup slot")
    print(total)
    return 0
end
