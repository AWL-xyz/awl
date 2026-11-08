-- Geometry and fixed-point math module. No window ownership here.
struct Vec
    x: i64
    y: i64
    z: i64
end
struct Hit
    t: i64
    normal: Vec
end
function absval(x: i64) -> i64
    if x < 0 then return -x end
    return x
end
function clamp(x: i64, lo: i64, hi: i64) -> i64
    if x < lo then return lo end
    if x > hi then return hi end
    return x
end
function sine(degrees: i64) -> i64
    local a: i64 = degrees % 360
    local sign: i64 = 1
    if a >= 180 then
        a = a - 180
        sign = -1
    end
    local p: i64 = a * (180 - a)
    -- Bhaskara's rational sine approximation, no floating point.
    return sign * 40000 * p / (40500 - p)
end
function rotate_inverse(v: Vec, s: i64, c: i64) -> Vec
    return Vec((c*v.x - s*v.z)/10000, v.y, (s*v.x + c*v.z)/10000)
end
function ray_point(o: Vec, d: Vec, t: i64) -> Vec
    return Vec(o.x+d.x*t/10000, o.y+d.y*t/10000, o.z+d.z*t/10000)
end
function pyramid(o: Vec, d: Vec) -> Hit
    local best: Hit = Hit(99999999, Vec(0,0,0))
    local face: i64 = 0
    while face < 5 do
        local n: Vec = Vec(2,1,0)
        local plane: i64 = 15000
        if face == 1 then n = Vec(-2,1,0) end
        if face == 2 then n = Vec(0,1,2) end
        if face == 3 then n = Vec(0,1,-2) end
        if face == 4 then
            n = Vec(0,-1,0)
            plane = 11000
        end
        local denom: i64 = n.x*d.x+n.y*d.y+n.z*d.z
        if denom != 0 then
            local t: i64 = (plane-n.x*o.x-n.y*o.y-n.z*o.z)*10000/denom
            if t > 5 and t < best.t then
                local p: Vec = ray_point(o,d,t)
                local width: i64 = (15000-p.y)/2
                if p.y >= -11015 and p.y <= 15015 and absval(p.x) <= width+15 and absval(p.z) <= width+15 then
                    best = Hit(t,n)
                end
            end
        end
        face = face + 1
    end
    return best
end
function rgb(r: i64, g: i64, b: i64) -> i64
    return clamp(r,0,255)*65536 + clamp(g,0,255)*256 + clamp(b,0,255)
end
