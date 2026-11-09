func main[i64] {
    @p window: window_open(64, 48);
    if window == 0 {
        return 1;
    };
    @p titled: window_set_title(window, "Awl spinning donut");
    @p running: true;
    @p frame: 0;
    while running {
        @p event: window_poll(window);
        while event != 0 {
            if event == 1 {
                running: false;
            };
            event: window_poll(window);
        };
        if running == false {
            window_close(window);
            return 0;
        };
        @p angle: f64(frame) * tau / 90;
        @p row: 0;
        while row < 48 {
            @p col: 0;
            while col < 64 {
                @p dx: (f64(col) - 31.5) / 48;
                @p dy: (23.5 - f64(row)) / 48;
                @p length: sqrt(dx * dx + dy * dy + 1);
                dx: dx / length;
                dy: dy / length;
                @p dz: -1.0 / length;
                @p distance: 0.0;
                @p step: 0;
                @p color: 0;
                while step < 80 {
                    @p x: dx * distance;
                    @p y: dy * distance;
                    @p z: 4 + dz * distance;
                    @p ry: y * cos(angle) - z * sin(angle);
                    @p rz: y * sin(angle) + z * cos(angle);
                    @p ring: sqrt(x * x + rz * rz) - 1;
                    @p gap: sqrt(ring * ring + ry * ry) - 0.35;
                    if gap < 0.003 {
                        @p shade: 255 - step * 3;
                        if shade < 30 {
                            shade: 30;
                        };
                        color: shade * 65793;
                        step: 80;
                    } else {
                        distance: distance + gap;
                        step: step + 1;
                        if distance > 8 {
                            step: 80;
                        };
                    };
                };
                window_set_pixel(window, col, row, color);
                col: col + 1;
            };
            row: row + 1;
        };
        running: window_present(window);
        sleep_millis(16);
        frame: (frame + 1) % 90;
    };
    window_close(window);
    return 0;
};
