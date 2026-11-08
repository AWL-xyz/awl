-- Native paint with validated load and exclusive-create save; no atomic overwrite.
import canvas
import storage
function notice(w:i64,status:i64,saving:bool)->unit
    if status==0 then
        if saving then window_set_title(w,"Awl Pixelboard | Saved new file | S: save | L: load | other key: clear") else window_set_title(w,"Awl Pixelboard | Loaded file | S: save | L: load | other key: clear") end
    else
        if saving then
            if status==-3 then window_set_title(w,"Awl Pixelboard | Save refused: file exists | choose new path on launch") else window_set_title(w,"Awl Pixelboard | Save failed; partial file may remain | canvas retained") end
        else window_set_title(w,"Awl Pixelboard | Load failed: canvas unchanged | S: save | L: load") end
    end
end
function main()->i64
    if arg_count()>2 then print("usage: pixelboard [NEW_SAVE_PATH [LOAD_PATH]]") return 2 end
    local save_path:string="pixelboard.kpb"
    if arg_count()>0 then
        if not arg_text_valid(0) then return 2 end
        save_path=arg_text(0)
    end
    local load_path:string=save_path
    if arg_count()>1 then
        if not arg_text_valid(1) then return 2 end
        load_path=arg_text(1)
    end
    local save_key:i64=39
    local load_key:i64=46
    if platform_kind()==2 then save_key=83 load_key=76 end
    local w:i64=window_open(720,480)
    if w==0 then return 3 end
    defer window_close(w)
    if not window_set_title(w,"Awl Pixelboard | S: save new | L: load | other key: clear | right: color") then return 4 end
    scoped cells:int_vector=int_vector_new(384)
    if not int_vector_valid(cells) then return 3 end
    local i:i64=0
    while i<384 do
        if not int_vector_push(cells,0) then return 3 end
        i=i+1
    end
    canvas.blank(cells)
    local active:bool=true
    local dirty:bool=true
    local painting:bool=false
    local selected:i64=0
    while active do
        local event:i64=window_poll(w)
        while event!=0 and active do
            if event==1 then active=false end
            if event==2 or event==3 then dirty=true end
            if event==4 then
                local key:i64=window_key(w)
                if key==save_key then
                    notice(w,storage.save_new(cells,save_path),true)
                else
                    if key==load_key then
                        local status:i64=storage.load(cells,load_path)
                        notice(w,status,false)
                        if status==0 then dirty=true end
                    else canvas.blank(cells) dirty=true end
                end
            end
            if event==7 and window_key(w)==3 then selected=(selected+1)%4 end
            if event==7 and window_key(w)==1 then painting=true end
            if event==8 and window_key(w)==1 then painting=false end
            if (event==6 or event==7) and painting then
                if canvas.paint(cells,w,canvas.brush(selected)) then dirty=true end
            end
            event=window_poll(w)
        end
        if active and dirty then
            active=canvas.draw(cells,w)
            dirty=false
        end
        if active then sleep_millis(10) end
    end
    return 0
end
