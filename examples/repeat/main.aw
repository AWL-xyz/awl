function seed()->i64
    print("Seed evaluated once")
    return 7
end
function main()->i64
    print("Compact fixed arrays")
    local values:[i64;1024]=[seed();1024]
    print(array_length(values))
    local i:i64=0
    local sum:i64=0
    while i<array_length(values) do
        sum=sum+values[i]
        i=i+1
    end
    print(sum)
    local grid:[[i64;4];3]=[[0;4];3]
    grid[1][2]=42
    print("Independent rows after copy")
    print(grid[0][2])
    print(grid[1][2])
    print(grid[2][2])
    return 0
end
