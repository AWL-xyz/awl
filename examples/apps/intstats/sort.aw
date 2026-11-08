function sift(borrow values:int_vector,start:i64,stop:i64)->unit
    local root:i64=start
    local done:bool=false
    while root*2+1<stop and not done do
        local child:i64=root*2+1
        if child+1<stop then
            if int_vector_get(values,child)<int_vector_get(values,child+1) then child=child+1 end
        end
        if int_vector_get(values,root)<int_vector_get(values,child) then
            local saved:i64=int_vector_get(values,root)
            int_vector_set(values,root,int_vector_get(values,child))
            int_vector_set(values,child,saved)
            root=child
        else
            done=true
        end
    end
end
function ascending(borrow values:int_vector)->unit
    local count:i64=int_vector_length(values)
    local start:i64=count/2
    while start>0 do
        start=start-1
        sift(values,start,count)
    end
    local stop:i64=count
    while stop>1 do
        stop=stop-1
        local saved:i64=int_vector_get(values,0)
        int_vector_set(values,0,int_vector_get(values,stop))
        int_vector_set(values,stop,saved)
        sift(values,0,stop)
    end
end
