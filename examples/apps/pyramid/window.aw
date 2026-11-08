-- Event-loop helper module.
function alive(w: i64) -> bool
    local event: i64 = window_poll(w)
    while event != 0 do
        if event == 1 then return false end
        event = window_poll(w)
    end
    return true
end
