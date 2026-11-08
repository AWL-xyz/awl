union Lookup
    Found(value:i64)
    Missing()
end
function main()->i64
    match Lookup.Found(1) then
        case Lookup.Found(value) then
            return value
    end
end
