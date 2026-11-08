function blank(borrow cells:int_vector)->unit
    local i:i64=0
    while i<int_vector_length(cells) do
        local x:i64=i%24
        local y:i64=i/24
        int_vector_set(cells,i,1056816+(x/4+y/4)%2*263688)
        i=i+1
    end
end
function brush(index:i64)->i64
    if index==0 then return 2217134 end
    if index==1 then return 7695615 end
    if index==2 then return 16217750 end
    return 16764784
end
function paint(borrow cells:int_vector,w:i64,color:i64)->bool
    local x:i64=window_mouse_x(w)
    local y:i64=window_mouse_y(w)
    if x<0 or y<0 or x>=window_width(w) or y>=window_height(w) then return false end
    int_vector_set(cells,y*16/window_height(w)*24+x*24/window_width(w),color)
    return true
end
function draw(borrow cells:int_vector,w:i64)->bool
    local width:i64=window_width(w)
    local height:i64=window_height(w)
    local y:i64=0
    while y<height do
        local x:i64=0
        while x<width do
            local color:i64=int_vector_get(cells,y*16/height*24+x*24/width)
            if x*24%width<24 or y*16%height<16 then color=4609647 end
            window_set_pixel(w,x,y,color)
            x=x+1
        end
        y=y+1
    end
    return window_present(w)
end
