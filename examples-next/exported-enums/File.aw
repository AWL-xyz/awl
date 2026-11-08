exports{
    @r enum Issue
        Missing();
        Io(code:i64);
        TooLarge(bytes:i64);
    end;
    @r enum Read
        Text(value:text);
        Failed(issue:Issue);
    end;
    @r func read :: path:text: Read {
        @p file: file_open(path, 0);
        if file == -2 { return Read.Failed(Issue.Missing()); };
        if file < 0 { return Read.Failed(Issue.Io(file)); };
        @p size: file_size(file);
        if size < 0 { file_close(file); return Read.Failed(Issue.Io(size)); };
        if size > 16384 { file_close(file); return Read.Failed(Issue.TooLarge(size)); };
        @p buffer: buffer_new(16384);
        if buffer == 0 { file_close(file); return Read.Failed(Issue.Io(-7)); };
        defer buffer_free(buffer);
        @p offset: 0;
        while offset < size {
            @p n: file_read(file, buffer, offset, size - offset);
            if n <= 0 { file_close(file); return Read.Failed(Issue.Io(n)); };
            offset: offset + n;
        };
        @p closed: file_close(file);
        if closed != 0 { return Read.Failed(Issue.Io(closed)); };
        if not buffer_text_valid(buffer, 0, size) { return Read.Failed(Issue.Io(-5)); };
        return Read.Text(buffer_text(buffer, 0, size));
    };
};
