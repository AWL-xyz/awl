function render(index:i64)->i64
    local b:spool=spool_new(64)
    if not spool_valid(b) then return 1 end
    defer spool_free(b)
    if spool_append(b,"frame=")!=0 then return 2 end
    if spool_i64(b,index)!=0 then return 3 end
    if index==99999 then
        if spool_print(b)!=0 then return 4 end
    end
    return 0
end
function main()->i64
    local i:i64=0
    while i<100000 do
        local result:i64=render(i)
        if result!=0 then return result end
        i=i+1
    end
    print("100000 calls: scoped cleanup on every return")
    if true then
        local b:spool=spool_new(8)
        if not spool_valid(b) then return 5 end
        defer spool_free(b)
        spool_append(b,"café")
        spool_print(b)
    end
    print("Inner scope released before this line")
    return 0
end
