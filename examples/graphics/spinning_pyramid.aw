-- A complete fixed-point ray renderer in Awl 0.7.1.
-- Output: 150 frames, 320x320 pixels/frame, row-major packed RGB integers.
-- All projection, rotation, intersection, lighting, shadows and colors are Awl.
-- Scale: 10000 = 1. No floats, arrays, window API or foreign calls required.
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
function main() -> i64
    local frame: i64 = 0
    while frame < 150 do
        local angle: i64 = frame*360/150 + 20
        local s: i64 = sine(angle)
        local c: i64 = sine(angle+90)
        local camera: Vec = rotate_inverse(Vec(0,18000,65000),s,c)
        -- Camera-relative key light: fixed in view while the pyramid rotates.
        local light: Vec = rotate_inverse(Vec(-4500,8000,5000),s,c)
        local y: i64 = 0
        while y < 320 do
            local x: i64 = 0
            while x < 320 do
                local sx: i64 = (2*x-319)*5200/320
                local sy: i64 = (319-2*y)*5200/320
                local world_ray: Vec = Vec(sx, sy*9700/10000-2400, -9700-sy*2400/10000)
                local d: Vec = rotate_inverse(world_ray,s,c)
                local hit: Hit = pyramid(camera,d)
                local color: i64 = 0
                if hit.t < 99999999 then
                    local n: Vec = hit.normal
                    local lambert: i64 = clamp((n.x*light.x+n.y*light.y+n.z*light.z)*10000/22500,0,10000)
                    local facing: i64 = clamp((n.x*camera.x+n.y*camera.y+n.z*camera.z)*10000/150000,0,10000)
                    local shade: i64 = 2000 + lambert*6200/10000 + facing*1800/10000
                    color = rgb(255*shade/10000, 177*shade/10000, 73*shade/10000)
                else
                    if world_ray.y < -100 then
                        local t: i64 = (-11000-18000)*10000/world_ray.y
                        local p: Vec = ray_point(Vec(0,18000,65000),world_ray,t)
                        local distance: i64 = absval(p.x)+absval(p.z)
                        local glow: i64 = clamp(10000-distance/7,0,10000)
                        local tile: i64 = ((p.x+10000000)/9000 + (p.z+10000000)/9000)%2
                        local floor_light: i64 = 7000 + glow/4 + tile*400
                        -- Actual shadow ray from the floor to the key light.
                        local local_floor: Vec = rotate_inverse(Vec(p.x,-10960,p.z),s,c)
                        local shadow: Hit = pyramid(local_floor,light)
                        if shadow.t < 99999999 then floor_light = floor_light*42/100 end
                        local fade: i64 = clamp(12000-t/16,1000,10000)
                        local haze: i64 = clamp(10000-absval(x-160)*25-absval(y-145)*20,0,10000)
                        color = rgb((6+haze/2200)*(10000-fade)/10000 + (17+glow/900)*floor_light*fade/100000000, (10+haze/1300)*(10000-fade)/10000 + (26+glow/550)*floor_light*fade/100000000, (20+haze/750)*(10000-fade)/10000 + (42+glow/450)*floor_light*fade/100000000)
                    else
                        local v: i64 = clamp(10000-absval(x-160)*25-absval(y-145)*20,0,10000)
                        color = rgb(6+v/2200, 10+v/1300, 20+v/750)
                    end
                end
                print(color)
                x = x + 1
            end
            y = y + 1
        end
        frame = frame + 1
    end
    return 0
end
