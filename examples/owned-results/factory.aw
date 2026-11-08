function make(n:i64)->own spool
    scoped b:spool=spool_new(32)
    spool_append(b,"frame=")
    spool_i64(b,n)
    return move b
end
function transform(own b:spool)->own spool
    spool_append(b," / returned")
    return move b
end
function forward(n:i64)->own spool
    return make(n)
end
