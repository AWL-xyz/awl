func glyph[i64] :: cp:u32 {
    if cp >= 97u32 and cp <= 122u32 { cp: cp - 32u32; };
    if cp == 32u32 { return 0; };
    if cp == 33u32 { return 4299296900; };
    if cp == 34u32 { return 10570; };
    if cp == 35u32 { return 11105828170; };
    if cp == 36u32 { return 4786165700; };
    if cp == 37u32 { return 27684643443; };
    if cp == 38u32 { return 23946532134; };
    if cp == 39u32 { return 2180; };
    if cp == 40u32 { return 8726317192; };
    if cp == 41u32 { return 2290360450; };
    if cp == 42u32 { return 720353952; };
    if cp == 43u32 { return 139432064; };
    if cp == 44u32 { return 2281701376; };
    if cp == 45u32 { return 1015808; };
    if cp == 46u32 { return 6643777536; };
    if cp == 47u32 { return 1109533200; };
    if cp == 48u32 { return 15623448110; };
    if cp == 49u32 { return 15170932932; };
    if cp == 50u32 { return 33357578798; };
    if cp == 51u32 { return 16660251151; };
    if cp == 52u32 { return 8891181448; };
    if cp == 53u32 { return 16660268095; };
    if cp == 54u32 { return 15621129262; };
    if cp == 55u32 { return 2216829471; };
    if cp == 56u32 { return 15621113390; };
    if cp == 57u32 { return 15587034670; };
    if cp == 58u32 { return 207624384; };
    if cp == 59u32 { return 2285902016; };
    if cp == 60u32 { return 8726284424; };
    if cp == 61u32 { return 32537600; };
    if cp == 62u32 { return 2290622594; };
    if cp == 63u32 { return 4299440686; };
    if cp == 64u32 { return 32260159022; };
    if cp == 65u32 { return 18842895918; };
    if cp == 66u32 { return 16694887983; };
    if cp == 67u32 { return 32246891582; };
    if cp == 68u32 { return 16694953519; };
    if cp == 69u32 { return 33321092159; };
    if cp == 70u32 { return 1108837439; };
    if cp == 71u32 { return 32801457214; };
    if cp == 72u32 { return 18842895921; };
    if cp == 73u32 { return 15170932878; };
    if cp == 74u32 { return 6754148636; };
    if cp == 75u32 { return 18560947505; };
    if cp == 76u32 { return 33320633377; };
    if cp == 77u32 { return 18842572657; };
    if cp == 78u32 { return 18842703473; };
    if cp == 79u32 { return 15621211694; };
    if cp == 80u32 { return 1108854319; };
    if cp == 81u32 { return 23946905134; };
    if cp == 82u32 { return 18561353263; };
    if cp == 83u32 { return 16660235326; };
    if cp == 84u32 { return 4433514655; };
    if cp == 85u32 { return 15621211697; };
    if cp == 86u32 { return 4648912433; };
    if cp == 87u32 { return 19182306865; };
    if cp == 88u32 { return 18834663985; };
    if cp == 89u32 { return 4433521201; };
    if cp == 90u32 { return 33321787935; };
    if cp == 91u32 { return 15101659214; };
    if cp == 92u32 { return 17725261857; };
    if cp == 93u32 { return 15309480206; };
    if cp == 94u32 { return 17732; };
    if cp == 95u32 { return 33285996544; };
    if cp == 96u32 { return 130; };
    if cp == 123u32 { return 8728416392; };
    if cp == 124u32 { return 4433514628; };
    if cp == 125u32 { return 2286162050; };
    if cp == 126u32 { return 9078784; };
    return 4299440686;
};
func valid[bool] :: @b pixels[i64], width:i64, height:i64, color:i64 {
    if width < 1 or height < 1 or width > 2048 or height > 2048 { return false; };
    if width * height > 1048576 { return false; };
    return vector.length(pixels) == width * height and color >= 0 and color <= 16777215;
};
func coordinate[bool] :: value:i64 {
    return value >= -32768 and value <= 32767;
};
func dot :: @b pixels[i64], width:i64, height:i64, x:i64, y:i64, color:i64 {
    if x >= 0 and y >= 0 and x < width and y < height { vector.set(pixels, y * width + x, color); };
};
exports{
    @r func rgb[i64] :: red:i64, green:i64, blue:i64 {
        if red < 0 or red > 255 or green < 0 or green > 255 or blue < 0 or blue > 255 { return -1; };
        return red * 65536 + green * 256 + blue;
    };
    @r func gray[i64] :: level:i64 {
        return rgb(level, level, level);
    };
    @r func surface[bool] :: @b pixels[i64], width:i64, height:i64, color:i64 {
        if width < 1 or height < 1 or width > 2048 or height > 2048 { return false; };
        if width * height > 1048576 or color < 0 or color > 16777215 { return false; };
        if not vector.reserve(pixels, width * height) { return false; };
        vector.clear(pixels);
        @p i: 0;
        while i < width * height { vector.push(pixels, color); i: i + 1; };
        return true;
    };
    @r func rect[bool] :: @b pixels[i64], width:i64, height:i64, x:i64, y:i64, wide:i64, high:i64, color:i64 {
        if not valid(pixels, width, height, color) or not coordinate(x) or not coordinate(y) { return false; };
        if wide < 0 or high < 0 or wide > 65536 or high > 65536 { return false; };
        @p left: x;
        @p top: y;
        @p right: x + wide;
        @p bottom: y + high;
        if left < 0 { left: 0; };
        if top < 0 { top: 0; };
        if right > width { right: width; };
        if bottom > height { bottom: height; };
        @p row: top;
        while row < bottom {
            @p col: left;
            while col < right { vector.set(pixels, row * width + col, color); col: col + 1; };
            row: row + 1;
        };
        return true;
    };
    @r func line[bool] :: @b pixels[i64], width:i64, height:i64, x:i64, y:i64, target_x:i64, target_y:i64, color:i64 {
        if not valid(pixels, width, height, color) or not coordinate(x) or not coordinate(y) or not coordinate(target_x) or not coordinate(target_y) { return false; };
        @p dx: target_x - x;
        @p dy: target_y - y;
        @p sx: 1;
        @p sy: 1;
        if dx < 0 { dx: -dx; sx: -1; };
        if dy < 0 { dy: -dy; sy: -1; };
        dy: -dy;
        @p error: dx + dy;
        @p done: false;
        while not done {
            dot(pixels, width, height, x, y, color);
            if x == target_x and y == target_y { done: true;
            } else {
                @p twice: error * 2;
                if twice >= dy { error: error + dy; x: x + sx; };
                if twice <= dx { error: error + dx; y: y + sy; };
            };
        };
        return true;
    };
    @r func circle[bool] :: @b pixels[i64], width:i64, height:i64, center_x:i64, center_y:i64, radius:i64, color:i64 {
        if not valid(pixels, width, height, color) or not coordinate(center_x) or not coordinate(center_y) { return false; };
        if radius < 0 or radius > 4096 { return false; };
        @p left: center_x - radius;
        @p right: center_x + radius;
        @p top: center_y - radius;
        @p bottom: center_y + radius;
        if left < 0 { left: 0; };
        if right >= width { right: width - 1; };
        if top < 0 { top: 0; };
        if bottom >= height { bottom: height - 1; };
        @p y: top;
        while y <= bottom {
            @p x: left;
            while x <= right {
                @p dx: x - center_x;
                @p dy: y - center_y;
                if dx * dx + dy * dy <= radius * radius { vector.set(pixels, y * width + x, color); };
                x: x + 1;
            };
            y: y + 1;
        };
        return true;
    };
    @r func draw_text[bool] :: @b pixels[i64], width:i64, height:i64, x:i64, y:i64, payload:text, scale:i64, color:i64 {
        if not valid(pixels, width, height, color) or not coordinate(x) or not coordinate(y) { return false; };
        if scale < 1 or scale > 8 or string.length(payload) > 512 { return false; };
        @p column: x;
        @p row: y;
        @p i: 0;
        while i < string.length(payload) {
            @p cp: string.codepoint(payload, i);
            if cp == 10u32 { column: x; row: row + 8 * scale;
            } else {
                @p bits: glyph(cp);
                @p factor: 1;
                @p py: 0;
                while py < 7 {
                    @p px: 0;
                    while px < 5 {
                        if bits / factor % 2 == 1 {
                            @p sy: 0;
                            while sy < scale {
                                @p sx: 0;
                                while sx < scale { dot(pixels, width, height, column + px * scale + sx, row + py * scale + sy, color); sx: sx + 1; };
                                sy: sy + 1;
                            };
                        };
                        factor: factor * 2;
                        px: px + 1;
                    };
                    py: py + 1;
                };
                column: column + 6 * scale;
            };
            i: i + 1;
        };
        return true;
    };
    @r func present[bool] :: window:i64, @b pixels[i64], width:i64, height:i64 {
        if not valid(pixels, width, height, 0) { return false; };
        if window.width(window) != width or window.height(window) != height { return false; };
        @p i: 0;
        while i < vector.length(pixels) {
            @p color: vector.get(pixels, i);
            if color < 0 or color > 16777215 { return false; };
            i: i + 1;
        };
        i: 0;
        while i < vector.length(pixels) { window.pixel(window, i % width, i / width, vector.get(pixels, i)); i: i + 1; };
        return window.present(window);
    };
};
