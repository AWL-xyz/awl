function finish(own b:spool,n:i64)->i64
    if n==99999 then spool_print(b) end
    return spool_bytes(b)
end
function frame(n:i64)->i64
    scoped b:spool=spool_new(32)
    spool_append(b,"frame=")
    spool_i64(b,n)
    local count:i64=0
    if n%2==0 then
        spool_append(b," / even")
        local taken:i64=finish(move b,n)
        count=taken
    else
        scoped ready:spool=move b
        spool_append(ready," / odd")
        local taken:i64=finish(move ready,n)
        count=taken
    end
    return count
end
function main()->i64
    local i:i64=0
    local total:i64=0
    while i<100000 do
        total=total+frame(i)
        i=i+1
    end
    print("100000 conditional handoffs: one owner per path")
    print(total)
    return 0
end
