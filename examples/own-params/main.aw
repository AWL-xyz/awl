import sink as sink
function frame(n:i64)->i64
    scoped b:spool=spool_new(32)
    if not spool_valid(b) then return -1 end
    spool_append(b,"frame=")
    spool_i64(b,n)
    local count:i64=sink.finish(move b,n)
    return count
end
function main()->i64
    local i:i64=0
    local total:i64=0
    while i<100000 do
        total=total+frame(i)
        i=i+1
    end
    print("100000 owning calls: callee releases builders")
    print(total)
    scoped missing:spool=spool_new(-1)
    local available:bool=sink.available(move missing)
    print("Unavailable handles transfer safely")
    print(available)
    return 0
end
