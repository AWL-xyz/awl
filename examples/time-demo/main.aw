use time;

func main[i64] {
    @p started: time.now();
    @p stamp: time.wall();
    if not time.sleep(20) { return 1; };
    print(time.elapsed(started) >= 1);
    print(stamp > 0);
    print(time.expired(started));
    return 0;
};
