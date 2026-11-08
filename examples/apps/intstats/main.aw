import sort as sort
function main()->i64
    if arg_count()==0 then
        print("usage: intstats INTEGER [INTEGER ...]")
        return 2
    end
    scoped values:int_vector=int_vector_new(0)
    if not int_vector_valid(values) then return 3 end
    local i:i64=0
    while i<arg_count() do
        if not arg_i64_valid(i) then
            print("invalid signed 64-bit integer argument")
            return 2
        end
        if not int_vector_push(values,arg_i64(i)) then
            print("vector growth failed")
            return 3
        end
        i=i+1
    end
    sort.ascending(values)
    print("count")
    print(int_vector_length(values))
    print("minimum")
    print(int_vector_get(values,0))
    print("maximum")
    print(int_vector_get(values,int_vector_length(values)-1))
    print("sorted")
    i=0
    while i<int_vector_length(values) do
        print(int_vector_get(values,i))
        i=i+1
    end
    return 0
end
