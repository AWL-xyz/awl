/* Wall-clock helper emitted only for programs that call wall_clock_millis.
 * CLOCK_REALTIME is UTC time since the Epoch; FILETIME uses 100ns ticks since 1601.
 * Overflow and malformed clock values trap rather than wrapping into i64. */
static int64_t k_wall_clock_millis(void) {
#if defined(_WIN32)
    FILETIME ft;
    ULARGE_INTEGER raw;
    GetSystemTimePreciseAsFileTime(&ft);
    raw.LowPart=ft.dwLowDateTime;
    raw.HighPart=ft.dwHighDateTime;
    if (raw.QuadPart < 116444736000000000ULL) k_resource_trap();
    uint64_t millis=(raw.QuadPart-116444736000000000ULL)/10000ULL;
    if (millis > (uint64_t)INT64_MAX) k_resource_trap();
    return (int64_t)millis;
#else
    struct timespec t;
    if (clock_gettime(CLOCK_REALTIME,&t)) k_resource_trap();
    if (t.tv_nsec < 0 || t.tv_nsec >= 1000000000L) k_resource_trap();
    uint64_t seconds=(uint64_t)t.tv_sec;
    uint64_t millis=(uint64_t)t.tv_nsec/1000000UL;
    if (seconds > ((uint64_t)INT64_MAX-millis)/1000ULL) k_resource_trap();
    return (int64_t)(seconds*1000ULL+millis);
#endif
}
