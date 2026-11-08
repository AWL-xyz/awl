union Route
    Render()
    Persist()
    Keep()
end
function choose(n:i64)->Route
    if n%3==0 then return Route.Render() end
    if n%3==1 then return Route.Persist() end
    return Route.Keep()
end
function finish(own b:spool,n:i64)->i64
    if n==99999 then spool_print(b) end
    return spool_bytes(b)
end
function frame(n:i64)->i64
    scoped b:spool=spool_new(32)
    spool_append(b,"frame=")
    spool_i64(b,n)
    local count:i64=0
    match choose(n) then
        case Route.Render() then
            spool_append(b," / draw")
            local taken:i64=finish(move b,n)
            count=taken
        case Route.Persist() then
            scoped ready:spool=move b
            spool_append(ready," / save")
            local taken:i64=finish(move ready,n)
            count=taken
        case Route.Keep() then
            count=spool_bytes(b)
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
    print("100000 match routes: moved or retained, one cleanup")
    print(total)
    return 0
end
