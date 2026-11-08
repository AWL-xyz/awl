import factory as factory
function frame(n:i64)->i64
    scoped draft:spool=factory.forward(n)
    scoped ready:spool=factory.transform(move draft)
    if n==99999 then spool_print(ready) end
    return spool_bytes(ready)
end
function main()->i64
    local i:i64=0
    local total:i64=0
    while i<100000 do
        total=total+frame(i)
        i=i+1
    end
    print("100000 factory -> transform -> caller pipelines")
    print(total)
    return 0
end
