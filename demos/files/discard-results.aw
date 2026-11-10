-- Regression demonstration: ignored results must not repeat or erase effects.
function side()->i64
    print("side effect, exactly once")
    return 7
end
function main()->i64
    scoped values:int_vector=intvector.new(1)
    intvector.push(values,9)
    side()
    print(intvector.get(values,0))
    return 0
end
