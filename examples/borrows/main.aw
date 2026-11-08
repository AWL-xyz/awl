import text as text
function render(borrow b:spool,n:i64)->i64
    return text.append_frame(b,n)
end
function main()->i64
    scoped b:spool=spool_new(32)
    if not spool_valid(b) then return 1 end
    local i:i64=0
    local total:i64=0
    while i<100000 do
        local count:i64=render(b,i)
        if count<0 then return 2 end
        total=total+count
        i=i+1
    end
    spool_print(b)
    print("100000 helper calls: one scoped builder")
    print(total)
    print(spool_valid(b))
    return 0
end
