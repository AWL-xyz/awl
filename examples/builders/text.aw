-- Source-level recoverable error wrapper, not a built-in generic Result.
union Status
    Ok()
    Capacity()
    InvalidScalar()
    IO()
    Unknown(code:i64)
end
union Created
    Ready(value:spool)
    Unavailable()
end
function status(code:i64)->Status
    if code==0 then return Status.Ok() end
    if code==1 then return Status.Capacity() end
    if code==2 then return Status.InvalidScalar() end
    if code==3 then return Status.IO() end
    return Status.Unknown(code)
end
function create(capacity:i64)->Created
    local b:spool=spool_new(capacity)
    if spool_valid(b) then return Created.Ready(b) end
    return Created.Unavailable()
end
function append(b:spool,s:string)->Status
    return status(spool_append(b,s))
end
function codepoint(b:spool,cp:u32)->Status
    return status(spool_codepoint(b,cp))
end
