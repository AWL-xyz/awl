struct Samples
    values: [i64;4]
end
function doubled(input:[i64;4])->[i64;4]
    local output:[i64;4]=input
    local i:i64=0
    while i<array_length(output) do
        output[i]=output[i]*2
        i=i+1
    end
    return output
end
function main()->i64
    local original:[i64;4]=[3,7,11,15]
    local result:Samples=Samples(doubled(original))
    print("Typed arrays: original / doubled")
    local i:i64=0
    while i<array_length(original) do
        print(original[i])
        print(result.values[i])
        i=i+1
    end
    local grid:[[i64;2];2]=[[1,2],[3,4]]
    grid[1][0]=42
    print("Nested update")
    print(grid[1][0])
    print("Value copies preserve the original")
    print(original[0]==3)
    return 0
end
