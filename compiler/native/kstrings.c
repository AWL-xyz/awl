/* Immutable UTF-8 values. Literal storage is static; dynamic storage belongs to
 * a bounded process-lifetime region, reclaimed on normal exit. This is not GC,
 * reference counting, ownership inference or an unbounded production heap. */
#include <string.h>
#define Awl_STRINGS_RUNTIME 1
typedef struct { const unsigned char *data; uint64_t bytes,scalars; } KString;
_Static_assert(sizeof(KString)==24 && _Alignof(KString)==8,"Awl string ABI requires 24-byte size and 8-byte alignment");
typedef struct KStringAllocation {struct KStringAllocation *next;size_t bytes;} KStringAllocation;
static KStringAllocation *k_string_allocations;
static size_t k_string_heap_bytes,k_string_heap_count;
static int k_string_cleanup_registered;
static _Noreturn void k_string_trap(void) {
    fputs("Awl string trap: bounds, scalar, I/O, or allocation limit\n",stderr);abort();
}
static void k_string_cleanup(void) {
    while(k_string_allocations) {
        KStringAllocation *next=k_string_allocations->next;
        free(k_string_allocations);k_string_allocations=next;
    }
    k_string_heap_bytes=0;k_string_heap_count=0;
}
static unsigned char *k_string_allocate(size_t size) {
    if(size>64u*1024u*1024u-k_string_heap_bytes||k_string_heap_count>=65536) k_string_trap();
    if(!k_string_cleanup_registered) {
        if(atexit(k_string_cleanup)) k_string_trap();
        k_string_cleanup_registered=1;
    }
    KStringAllocation *p=malloc(sizeof(*p)+(size?size:1));
    if(!p) k_string_trap();
    p->next=k_string_allocations;p->bytes=size;k_string_allocations=p;
    k_string_heap_bytes+=size;++k_string_heap_count;
    return (unsigned char *)(p+1);
}
static int64_t k_string_bytes(KString s) {return (int64_t)s.bytes;}
static int64_t k_string_length(KString s) {return (int64_t)s.scalars;}
static uint8_t k_string_byte_at(KString s,int64_t index) {
    if(index<0||(uint64_t)index>=s.bytes) k_string_trap();
    return s.data[index];
}
/* Strict scalar validation for external UTF-8. No region allocation on probe. */
static bool k_utf8_scan(const unsigned char *data,size_t bytes,size_t *scalars) {
    size_t i=0,count=0;
    while(i<bytes) {
        unsigned a=data[i++];uint32_t cp;size_t rest;uint32_t minimum;
        if(a<0x80) {++count;continue;}
        if(a>=0xc2 && a<=0xdf) {cp=a&31;rest=1;minimum=0x80;}
        else if(a>=0xe0 && a<=0xef) {cp=a&15;rest=2;minimum=0x800;}
        else if(a>=0xf0 && a<=0xf4) {cp=a&7;rest=3;minimum=0x10000;}
        else return false;
        if(rest>bytes-i) return false;
        for(size_t j=0;j<rest;++j) {unsigned b=data[i++];if((b&0xc0)!=0x80) return false;cp=cp<<6|(b&63);}
        if(cp<minimum || cp>0x10ffff || (cp>=0xd800 && cp<=0xdfff)) return false;
        ++count;
    }
    *scalars=count;return true;
}
/* Only valid UTF-8 can enter this type through verified literals and these
 * constructors. These helpers are private generated-code ABI, not public FFI. */
static size_t k_string_width(unsigned char c) {
    return c<0x80?1:c<0xe0?2:c<0xf0?3:4;
}
static size_t k_string_offset(KString s,size_t scalar) {
    if(scalar>s.scalars) k_string_trap();
    size_t p=0;
    for(size_t i=0;i<scalar;++i) p+=k_string_width(s.data[p]);
    return p;
}
static uint32_t k_string_codepoint(KString s,int64_t index) {
    if(index<0||(uint64_t)index>=s.scalars) k_string_trap();
    size_t p=k_string_offset(s,(size_t)index),width=k_string_width(s.data[p]);
    uint32_t cp=width==1?s.data[p]:s.data[p]&((1u<<(7-width))-1u);
    for(size_t i=1;i<width;++i) cp=(cp<<6)|(s.data[p+i]&63);
    return cp;
}
static KString k_string_from_codepoint(uint32_t cp) {
    if(cp>0x10ffff||(cp>=0xd800&&cp<=0xdfff)) k_string_trap();
    size_t n=cp<0x80?1:cp<0x800?2:cp<0x10000?3:4;
    unsigned char *p=k_string_allocate(n);
    if(n==1) p[0]=(unsigned char)cp;
    else {
        p[0]=(unsigned char)((n==2?0xc0:n==3?0xe0:0xf0)|(cp>>(6*(n-1))));
        for(size_t i=1;i<n;++i) p[i]=(unsigned char)(0x80|((cp>>(6*(n-i-1)))&63));
    }
    return (KString){p,n,1};
}
static KString k_string_from_i64(int64_t value) {
    char data[32];int n=snprintf(data,sizeof(data),"%" PRId64,value);
    if(n<0||(size_t)n>=sizeof(data)) k_string_trap();
    unsigned char *p=k_string_allocate((size_t)n);memcpy(p,data,(size_t)n);
    return (KString){p,(size_t)n,(size_t)n};
}
static KString k_string_from_u64(uint64_t value) {
    char data[32];int n=snprintf(data,sizeof(data),"%" PRIu64,value);
    if(n<0||(size_t)n>=sizeof(data)) k_string_trap();
    unsigned char *p=k_string_allocate((size_t)n);memcpy(p,data,(size_t)n);
    return (KString){p,(size_t)n,(size_t)n};
}
static KString k_string_concat(KString a,KString b) {
    if(!a.bytes) return b;
    if(!b.bytes) return a;
    if(a.bytes>64u*1024u*1024u||b.bytes>64u*1024u*1024u-a.bytes) k_string_trap();
    size_t n=a.bytes+b.bytes;
    unsigned char *p=k_string_allocate(n);
    memcpy(p,a.data,a.bytes);memcpy(p+a.bytes,b.data,b.bytes);
    return (KString){p,n,a.scalars+b.scalars};
}
static bool k_string_equal(KString a,KString b) {
    return a.bytes==b.bytes && (!a.bytes||!memcmp(a.data,b.data,a.bytes));
}
static int64_t k_string_compare(KString a,KString b) {
    size_t n=a.bytes<b.bytes?a.bytes:b.bytes;
    int comparison=n?memcmp(a.data,b.data,n):0;
    if(comparison) return comparison<0?-1:1;
    return a.bytes<b.bytes?-1:a.bytes>b.bytes?1:0;
}
static KString k_string_slice(KString s,int64_t start,int64_t count) {
    if(start<0||count<0||(uint64_t)start>s.scalars||(uint64_t)count>s.scalars-(uint64_t)start) k_string_trap();
    size_t a=k_string_offset(s,(size_t)start),end=a;
    for(size_t i=0;i<(size_t)count;++i) end+=k_string_width(s.data[end]);
    return (KString){s.data+a,end-a,(size_t)count};
}
/* byte-offset cursor, O(1) per step so for-in over text is linear */
static bool k_string_next(KString s,int64_t *offset,uint32_t *out) {
    if((uint64_t)*offset>=s.bytes) return false;
    size_t p=(size_t)*offset,width=k_string_width(s.data[p]);
    uint32_t cp=width==1?s.data[p]:s.data[p]&((1u<<(7-width))-1u);
    for(size_t i=1;i<width;++i) cp=(cp<<6)|(s.data[p+i]&63);
    *offset+=(int64_t)width;*out=cp;return true;
}
/* scalar index of the first match or -1, an empty needle matches at 0 */
static int64_t k_string_find(KString s,KString needle) {
    if(needle.bytes>s.bytes) return -1;
    size_t scalar=0;
    for(size_t p=0;p+needle.bytes<=s.bytes;p+=k_string_width(s.data[p]),++scalar)
        if(!needle.bytes||!memcmp(s.data+p,needle.data,needle.bytes)) return (int64_t)scalar;
    return -1;
}
static bool k_string_contains(KString s,KString needle) { return k_string_find(s,needle)>=0; }
static bool k_string_starts_with(KString s,KString prefix) { return prefix.bytes<=s.bytes&&(!prefix.bytes||!memcmp(s.data,prefix.data,prefix.bytes)); }
static bool k_string_ends_with(KString s,KString suffix) { return suffix.bytes<=s.bytes&&(!suffix.bytes||!memcmp(s.data+s.bytes-suffix.bytes,suffix.data,suffix.bytes)); }
static KString k_string_replace(KString s,KString from,KString to) {
    if(!from.bytes) k_string_trap();
    KString out={s.data,0,0};bool first=true;size_t p=0,start=0;
    while(p+from.bytes<=s.bytes) {
        if(!memcmp(s.data+p,from.data,from.bytes)) {
            KString part={s.data+start,p-start,0};for(size_t i=start;i<p;i+=k_string_width(s.data[i])) ++part.scalars;
            out=first?part:k_string_concat(out,part);first=false;out=k_string_concat(out,to);p+=from.bytes;start=p;
        } else p+=k_string_width(s.data[p]);
    }
    if(first) return s;
    KString tail={s.data+start,s.bytes-start,0};for(size_t i=start;i<s.bytes;i+=k_string_width(s.data[i])) ++tail.scalars;
    return k_string_concat(out,tail);
}
static KString k_string_from_bool(bool v) { return v?(KString){(const unsigned char *)"true",4,4}:(KString){(const unsigned char *)"false",5,5}; }
static void k_print_string(KString s) {
    if(fwrite(s.data,1,s.bytes,stdout)!=s.bytes || fputc('\n',stdout)==EOF || fflush(stdout)) k_string_trap();
}

static KString k_string_from_f64(double value) {
    char data[64];int n=snprintf(data,sizeof(data),"%.17g",value);
    if(n<0||(size_t)n>=sizeof(data))k_string_trap();
    unsigned char *p=k_string_allocate((size_t)n);memcpy(p,data,(size_t)n);return (KString){p,(size_t)n,(size_t)n};
}
