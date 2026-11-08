function prepare(borrow b:spool,n:i64)->unit
    spool_append(b,"frame=")
    spool_i64(b,n)
end
function frame(n:i64)->i64
    scoped building:spool=spool_new(32)
    if not spool_valid(building) then return -1 end
    prepare(building,n)
    scoped ready:spool=move building
    spool_append(ready," / moved")
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
    print("100000 local moves: one release per owner")
    print(total)
    scoped unavailable:spool=spool_new(-1)
    scoped transferred:spool=move unavailable
    print("Moved unavailable descriptor remains unavailable")
    print(spool_valid(transferred))
    return 0
end
