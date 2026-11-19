/* Strict signed ASCII decimal shared by the argument and text APIs. */
#define Awl_DECIMAL_RUNTIME 1
// end is one past the last text byte, or NULL for a NUL-terminated argv item.
// Do not run strlen on argv or read past the explicit end of a text slice.
static inline bool k_decimal_i64(const unsigned char *p,const unsigned char *end,int64_t *out) {
    if(end&&p==end) return false;
    const bool negative=*p=='-';
    if(negative||*p=='+') ++p;
    if(end&&p==end) return false;
    unsigned digit=(unsigned)*p++-'0';
    if(digit>9) return false;
    uint64_t value=digit;
    for(;!end||p!=end;++p) {
        const unsigned char ch=*p;
        digit=(unsigned)ch-'0';
        if(digit>9) {
            if(!end&&!ch) break;
            return false;
        }
        // A twentieth significant digit cannot fit in i64. With at most 19,
        // the accumulation fits in u64; check the signed bound once below.
        if(value>=UINT64_C(1000000000000000000)) return false;
        value=value*10+digit;
    }
    const uint64_t limit=(uint64_t)INT64_MAX+negative;
    if(value>limit) return false;
    *out=negative?(value==limit?INT64_MIN:-(int64_t)value):(int64_t)value;
    return true;
}

#ifdef Awl_STRINGS_RUNTIME
static bool k_string_i64_valid(KString s) {
    int64_t value;return s.bytes&&k_decimal_i64(s.data,s.data+s.bytes,&value);
}
static int64_t k_string_to_i64(KString s) {
    int64_t value;
    if(!s.bytes||!k_decimal_i64(s.data,s.data+s.bytes,&value)) {
        fputs("Awl string trap: invalid signed integer\n",stderr);abort();
    }
    return value;
}
#endif
