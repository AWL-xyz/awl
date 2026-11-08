function frame(n:i64)->i64
    scoped b:spool=spool_new(32)
    if not spool_valid(b) then return -1 end
    spool_append(b,"frame=")
    spool_i64(b,n)
    if n==99999 then spool_print(b) end
    return spool_bytes(b)
end
function main()->i64
    local i:i64=0
    local total:i64=0
    while i<100000 do
        total=total+frame(i)
        i=i+1
    end
    print("100000 scoped builders: automatic release")
    print(total)
    scoped missing:spool=spool_new(-1)
    print("Unavailable allocation is safe to leave scope")
    print(spool_valid(missing))
    return 0
end
