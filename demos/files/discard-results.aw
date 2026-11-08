-- Regression demonstration: ignored results must not repeat or erase effects.
function side()->i64
    print("side effect, exactly once")
    return 7
end
function main()->i64
    scoped values:int_vector=int_vector_new(1)
    int_vector_push(values,9)
    side()
    print(int_vector_get(values,0))
    return 0
end
