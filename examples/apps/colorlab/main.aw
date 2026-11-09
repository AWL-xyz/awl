use Graphics.aw as gfx;
func render[bool] :: window:i64, @b pixels[i64], red:i64, green:i64, blue:i64 {
    @p width: window_width(window);
    @p height: window_height(window);
    if not gfx.surface(pixels, width, height, 1119522) { return false; };
    gfx.rect(pixels, width, height, 24, 68, 432, 224, 1646897);
    gfx.rect(pixels, width, height, 472, 68, 224, 224, 1646897);
    gfx.draw_text(pixels, width, height, 28, 24, "Awl COLOR LAB", 3, 14215151);
    gfx.draw_text(pixels, width, height, 48, 88, "RED   " + string.from_i64(red), 2, 16741488);
    gfx.draw_text(pixels, width, height, 48, 152, "GREEN " + string.from_i64(green), 2, 8124596);
    gfx.draw_text(pixels, width, height, 48, 216, "BLUE  " + string.from_i64(blue), 2, 8100863);
    @p x: 0;
    while x < 384 {
        @p value: x * 256 / 384;
        gfx.rect(pixels, width, height, 48 + x, 112, 1, 22, gfx.rgb(value, green, blue));
        gfx.rect(pixels, width, height, 48 + x, 176, 1, 22, gfx.rgb(red, value, blue));
        gfx.rect(pixels, width, height, 48 + x, 240, 1, 22, gfx.rgb(red, green, value));
        x: x + 1;
    };
    gfx.line(pixels, width, height, 48 + red * 383 / 255, 110, 48 + red * 383 / 255, 135, 16777215);
    gfx.line(pixels, width, height, 48 + green * 383 / 255, 174, 48 + green * 383 / 255, 199, 16777215);
    gfx.line(pixels, width, height, 48 + blue * 383 / 255, 238, 48 + blue * 383 / 255, 263, 16777215);
    gfx.draw_text(pixels, width, height, 492, 88, "LIVE PREVIEW", 2, 14215151);
    gfx.rect(pixels, width, height, 492, 116, 184, 116, gfx.rgb(red, green, blue));
    gfx.circle(pixels, width, height, 522, 262, 12, gfx.gray(red));
    gfx.circle(pixels, width, height, 584, 262, 12, gfx.gray(green));
    gfx.circle(pixels, width, height, 646, 262, 12, gfx.gray(blue));
    gfx.draw_text(pixels, width, height, 28, 314, "GRAYSCALE, CLICK TO SELECT", 2, 14215151);
    x: 0;
    while x < 640 { gfx.rect(pixels, width, height, 28 + x, 342, 1, 28, gfx.gray(x * 256 / 640)); x: x + 1; };
    gfx.draw_text(pixels, width, height, 28, 400, "DRAG A BAR, CLOSE WINDOW TO EXIT", 2, 9213855);
    return gfx.present(window, pixels, width, height);
};
func main[i64] {
    if arg_count() != 0 { return 2; };
    @p window: window_open(720, 440);
    if window == 0 { return 3; };
    defer window_close(window);
    if not window_set_title(window, "Awl Color Lab | native source graphics") { return 3; };
    @s pixels vector<i64>: vector.new<i64>(0);
    if not vector.valid(pixels) { return 9; };
    @p red: 78;
    @p green: 166;
    @p blue: 224;
    @p active: true;
    @p dirty: true;
    @p dragging: false;
    @p frames: 0;
    while active and frames < 2048 {
        @p events: 0;
        @p event: window_poll(window);
        while event != 0 and active and events < 64 {
            if event == 1 { active: false; };
            if event == 2 or event == 3 { dirty: true; };
            if event == 7 and window_key(window) == 1 { dragging: true; };
            if event == 8 and window_key(window) == 1 { dragging: false; };
            if dragging and (event == 6 or event == 7) {
                @p x: window_mouse_x(window);
                @p y: window_mouse_y(window);
                if x >= 48 and x < 432 {
                    @p value: (x - 48) * 256 / 384;
                    if y >= 112 and y < 134 { red: value; dirty: true; };
                    if y >= 176 and y < 198 { green: value; dirty: true; };
                    if y >= 240 and y < 262 { blue: value; dirty: true; };
                };
                if x >= 28 and x < 668 and y >= 342 and y < 370 {
                    red: (x - 28) * 256 / 640; green: red; blue: red; dirty: true;
                };
            };
            events: events + 1;
            if events < 64 { event: window_poll(window); };
        };
        if active and dirty {
            if not render(window, pixels, red, green, blue) { return 3; };
            frames: frames + 1;
            dirty: false;
        };
        if active { sleep_millis(10); };
    };
    if active { return 6; };
    print(string.from_i64(red) + " " + string.from_i64(green) + " " + string.from_i64(blue));
    if stdout_flush() != 0 { return 3; };
    return 0;
};
