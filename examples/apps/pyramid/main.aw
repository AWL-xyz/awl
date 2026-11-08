-- A real native application composed from four source modules.
import renderer
import window
function main()->i64
    local w:i64=window_open(480,480)
    if w==0 then print(-1) return 1 end
    local started:i64=clock_millis()
    local running:bool=true
    while running do
        running=window.alive(w)
        if running then
            running=renderer.frame(w,(clock_millis()-started)%5000)
            sleep_millis(16)
        end
    end
    window_close(w)
    return 0
end
