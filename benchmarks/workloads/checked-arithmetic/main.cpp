#include <charconv>
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <string_view>
#include <system_error>

using i64 = std::int64_t;

i64 parse_i64(std::string_view text) {
    i64 value;
    const auto end = text.data() + text.size();
    const auto parsed = std::from_chars(text.data(), end, value);
    if (parsed.ec != std::errc{} || parsed.ptr != end) std::abort();
    return value;
}

int main(int argc, char **argv) {
    if (argc != 4) return 2;
    const i64 rounds = parse_i64(argv[1]);
    const i64 factor = parse_i64(argv[2]);
    i64 state = parse_i64(argv[3]);
    i64 total = 0;
    for (i64 i = 0; i < rounds; ++i) {
        i64 product, mixed;
        if (__builtin_mul_overflow(state, factor, &product) ||
            __builtin_sub_overflow(product, i, &mixed)) std::abort();
        state = mixed % 1048573;
        if (__builtin_add_overflow(total, state, &total)) std::abort();
    }
    std::printf("%" PRId64 "\n%" PRId64 "\n", total, state);
}
