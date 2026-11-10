exports{
    @r func now[i64] {
        return clock.millis();
    };
    @r func wall[i64] {
        return clock.wall();
    };
    @r func elapsed[i64] :: since:i64 {
        @p current: clock.millis();
        if since < 0 or since >= current { return 0; };
        return current - since;
    };
    @r func remaining[i64] :: deadline:i64 {
        @p current: clock.millis();
        if deadline <= current { return 0; };
        return deadline - current;
    };
    @r func expired[bool] :: deadline:i64 {
        return remaining(deadline) == 0;
    };
    @r func deadline[i64] :: timeout:i64 {
        @p current: clock.millis();
        @p maximum: 9223372036854775807;
        if timeout <= 0 { return current; };
        if timeout > maximum - current { return maximum; };
        return current + timeout;
    };
    @r func sleep[bool] :: ms:i64 {
        if ms < 0 or ms > 600000 { return false; };
        @p left: ms;
        while left > 60000 {
            clock.sleep(60000);
            left: left - 60000;
        };
        if left > 0 { clock.sleep(left); };
        return true;
    };
};
