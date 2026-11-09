exports{
    @r func now[i64] {
        return clock_millis();
    };
    @r func wall[i64] {
        return wall_clock_millis();
    };
    @r func elapsed[i64] :: since:i64 {
        @p current: clock_millis();
        if since < 0 or since >= current { return 0; };
        return current - since;
    };
    @r func remaining[i64] :: deadline:i64 {
        @p current: clock_millis();
        if deadline <= current { return 0; };
        return deadline - current;
    };
    @r func expired[bool] :: deadline:i64 {
        return remaining(deadline) == 0;
    };
    @r func deadline[i64] :: timeout:i64 {
        @p current: clock_millis();
        @p maximum: 9223372036854775807;
        if timeout <= 0 { return current; };
        if timeout > maximum - current { return maximum; };
        return current + timeout;
    };
    @r func sleep[bool] :: ms:i64 {
        if ms < 0 or ms > 600000 { return false; };
        @p left: ms;
        while left > 60000 {
            sleep_millis(60000);
            left: left - 60000;
        };
        if left > 0 { sleep_millis(left); };
        return true;
    };
};
