function make(n:i64)->own spool
    scoped b:spool=spool_new(32)
    spool_append(b,"frame=")
    spool_i64(b,n)
    return move b
end
function finish(own b:spool,n:i64)->i64
    if n==99999 then spool_print(b) end
    return spool_bytes(b)
end
function main()->i64
    scoped b:spool=make(0)
    local i:i64=0
    local total:i64=0
    while i<100000 do
        local count:i64=finish(move b,i)
        total=total+count
        b=make(i+1)
        i=i+1
    end
    print("100000 loop-carried owners: state restored on every backedge")
    print(total)
    print("Final owner remains live")
    spool_print(b)
    return 0
end
