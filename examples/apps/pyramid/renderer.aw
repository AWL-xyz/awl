import math as m

function frame(w:i64, elapsed:i64)->bool
        local width: i64 = window_width(w)
        local height: i64 = window_height(w)
        local span: i64 = width
        if height < span then span = height end
        local angle: i64 = elapsed*360/5000 + 20
        local s: i64 = m.sine(angle)
        local c: i64 = m.sine(angle+90)
        local camera: m.Vec = m.rotate_inverse(m.Vec(0,18000,65000),s,c)
        -- Camera-relative key light: fixed in view while the m.pyramid rotates.
        local light: m.Vec = m.rotate_inverse(m.Vec(-4500,8000,5000),s,c)
        local y: i64 = 0
        while y < height do
            local x: i64 = 0
            while x < width do
                local sx: i64 = (2*x-width+1)*5200/span
                local sy: i64 = (height-1-2*y)*5200/span
                local world_ray: m.Vec = m.Vec(sx, sy*9700/10000-2400, -9700-sy*2400/10000)
                local d: m.Vec = m.rotate_inverse(world_ray,s,c)
                local hit: m.Hit = m.pyramid(camera,d)
                local color: i64 = 0
                if hit.t < 99999999 then
                    local n: m.Vec = hit.normal
                    local lambert: i64 = m.clamp((n.x*light.x+n.y*light.y+n.z*light.z)*10000/22500,0,10000)
                    local facing: i64 = m.clamp((n.x*camera.x+n.y*camera.y+n.z*camera.z)*10000/150000,0,10000)
                    local shade: i64 = 2000 + lambert*6200/10000 + facing*1800/10000
                    color = m.rgb(255*shade/10000, 177*shade/10000, 73*shade/10000)
                else
                    if world_ray.y < -100 then
                        local t: i64 = (-11000-18000)*10000/world_ray.y
                        local p: m.Vec = m.ray_point(m.Vec(0,18000,65000),world_ray,t)
                        local distance: i64 = m.absval(p.x)+m.absval(p.z)
                        local glow: i64 = m.clamp(10000-distance/7,0,10000)
                        local tile: i64 = ((p.x+10000000)/9000 + (p.z+10000000)/9000)%2
                        local floor_light: i64 = 7000 + glow/4 + tile*400
                        -- Actual shadow ray from the floor to the key light.
                        local local_floor: m.Vec = m.rotate_inverse(m.Vec(p.x,-10960,p.z),s,c)
                        local shadow: m.Hit = m.pyramid(local_floor,light)
                        if shadow.t < 99999999 then floor_light = floor_light*42/100 end
                        local fade: i64 = m.clamp(12000-t/16,1000,10000)
                        local haze: i64 = m.clamp(10000-m.absval(x-width/2)*8000/span-m.absval(y-height*145/320)*6400/span,0,10000)
                        color = m.rgb((6+haze/2200)*(10000-fade)/10000 + (17+glow/900)*floor_light*fade/100000000, (10+haze/1300)*(10000-fade)/10000 + (26+glow/550)*floor_light*fade/100000000, (20+haze/750)*(10000-fade)/10000 + (42+glow/450)*floor_light*fade/100000000)
                    else
                        local v: i64 = m.clamp(10000-m.absval(x-width/2)*8000/span-m.absval(y-height*145/320)*6400/span,0,10000)
                        color = m.rgb(6+v/2200, 10+v/1300, 20+v/750)
                    end
                end
                window_set_pixel(w,x,y,color)
                x = x + 1
            end
            y = y + 1
        end
    return window_present(w)
end
