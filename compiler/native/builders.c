/* Typed, explicitly released UTF-8 builders. Copies alias a checked identity;
 * no mutable buffer pointers escape. Snapshots COPY into the string region.
 * Single-threaded experimental runtime, not static ownership/borrow checking. */
typedef struct {uint64_t id;} KSpool;
_Static_assert(sizeof(KSpool)==8 && _Alignof(KSpool)==8,"builder ABI");
typedef struct {uint64_t id;unsigned char *data;size_t capacity,bytes,scalars;} KBuilderSlot;
static KBuilderSlot k_builder_slots[64];
static uint64_t k_builder_next_id=1;
static size_t k_builder_payload;
static bool k_builder_cleanup_registered;
static _Noreturn void k_builder_trap(void) {
    fputs("Awl text builder trap: invalid or released handle\n",stderr);abort();
}
static KBuilderSlot *k_builder_find(KSpool b) {
    if(b.id) for(size_t i=0;i<64;++i) if(k_builder_slots[i].id==b.id) return &k_builder_slots[i];
    return NULL;
}
static KBuilderSlot *k_builder_require(KSpool b) {
    KBuilderSlot *slot=k_builder_find(b);if(!slot) k_builder_trap();return slot;
}
static void k_builder_cleanup(void) {
    for(size_t i=0;i<64;++i) {free(k_builder_slots[i].data);k_builder_slots[i]=(KBuilderSlot){0};}
    k_builder_payload=0;
}
static KSpool k_spool_new(int64_t capacity) {
    if(capacity<0||capacity>16*1024*1024||(uint64_t)capacity>64u*1024u*1024u-k_builder_payload||k_builder_next_id==UINT64_MAX) return (KSpool){0};
    KBuilderSlot *slot=NULL;
    for(size_t i=0;i<64;++i) if(!k_builder_slots[i].id) {slot=&k_builder_slots[i];break;}
    if(!slot) return (KSpool){0};
    if(!k_builder_cleanup_registered) {
        if(atexit(k_builder_cleanup)) return (KSpool){0};
        k_builder_cleanup_registered=true;
    }
    unsigned char *p=malloc(capacity?(size_t)capacity:1);
    if(!p) return (KSpool){0};
    *slot=(KBuilderSlot){k_builder_next_id++,p,(size_t)capacity,0,0};
    k_builder_payload+=(size_t)capacity;
    return (KSpool){slot->id};
}
static bool k_spool_valid(KSpool b) {return k_builder_find(b)!=NULL;}
static void k_spool_free(KSpool b) {
    KBuilderSlot *slot=k_builder_require(b);k_builder_payload-=slot->capacity;
    free(slot->data);*slot=(KBuilderSlot){0};
}
static void k_spool_clear(KSpool b) {
    KBuilderSlot *slot=k_builder_require(b);slot->bytes=slot->scalars=0;
}
static bool k_spool_reserve(KSpool b,int64_t capacity) {
    KBuilderSlot *s=k_builder_require(b);
    if(capacity<0||capacity>16*1024*1024)return false;
    if((uint64_t)capacity<=s->capacity)return true;
    const size_t extra=(size_t)capacity-s->capacity;
    if(extra>64u*1024u*1024u-k_builder_payload)return false;
    unsigned char *data=realloc(s->data,(size_t)capacity);if(!data)return false;
    s->data=data;s->capacity=(size_t)capacity;k_builder_payload+=extra;return true;
}
static bool k_spool_truncate(KSpool b,int64_t length) {
    KBuilderSlot *s=k_builder_require(b);if(length<0||(uint64_t)length>s->scalars)return false;
    if((uint64_t)length==s->scalars)return true;
    size_t bytes=0;for(int64_t i=0;i<length;++i)bytes+=k_string_width(s->data[bytes]);
    s->bytes=bytes;s->scalars=(size_t)length;return true;
}
static int64_t k_spool_capacity(KSpool b) {return (int64_t)k_builder_require(b)->capacity;}
static int64_t k_spool_bytes(KSpool b) {return (int64_t)k_builder_require(b)->bytes;}
static int64_t k_spool_length(KSpool b) {return (int64_t)k_builder_require(b)->scalars;}
/* Return0 success,1 capacity,2 invalid scalar,3 I/O. Failed appends are atomic.
 * Capacity is fixed: no hidden reallocations or borrowed mutable string views. */
static int64_t k_builder_put(KBuilderSlot *slot,const unsigned char *data,size_t bytes,size_t scalars) {
    if(bytes>slot->capacity-slot->bytes) return 1;
    if(bytes) memcpy(slot->data+slot->bytes,data,bytes);
    slot->bytes+=bytes;slot->scalars+=scalars;return 0;
}
static int64_t k_spool_append(KSpool b,KString text) {
    return k_builder_put(k_builder_require(b),text.data,text.bytes,text.scalars);
}
static int64_t k_spool_codepoint(KSpool b,uint32_t cp) {
    KBuilderSlot *slot=k_builder_require(b);
    if(cp>0x10ffff||(cp>=0xd800&&cp<=0xdfff)) return 2;
    size_t n=cp<0x80?1:cp<0x800?2:cp<0x10000?3:4;unsigned char p[4];
    if(n==1) p[0]=(unsigned char)cp;
    else {
        p[0]=(unsigned char)((n==2?0xc0:n==3?0xe0:0xf0)|(cp>>(6*(n-1))));
        for(size_t i=1;i<n;++i) p[i]=(unsigned char)(0x80|((cp>>(6*(n-i-1)))&63));
    }
    return k_builder_put(slot,p,n,1);
}
static int64_t k_spool_i64(KSpool b,int64_t value) {
    KBuilderSlot *slot=k_builder_require(b);char data[32];int n=snprintf(data,sizeof(data),"%" PRId64,value);
    if(n<0||(size_t)n>=sizeof(data)) return 3;
    return k_builder_put(slot,(const unsigned char *)data,(size_t)n,(size_t)n);
}
static int64_t k_spool_u64(KSpool b,uint64_t value) {
    KBuilderSlot *slot=k_builder_require(b);char data[32];int n=snprintf(data,sizeof(data),"%" PRIu64,value);
    if(n<0||(size_t)n>=sizeof(data)) return 3;
    return k_builder_put(slot,(const unsigned char *)data,(size_t)n,(size_t)n);
}
static int64_t k_spool_print(KSpool b) {
    KBuilderSlot *slot=k_builder_require(b);
    if(fwrite(slot->data,1,slot->bytes,stdout)!=slot->bytes||fputc('\n',stdout)==EOF||fflush(stdout)) return 3;
    return 0;
}
static KString k_spool_snapshot(KSpool b) {
    KBuilderSlot *slot=k_builder_require(b);
    if(!slot->bytes) return (KString){(const unsigned char *)"",0,0};
    unsigned char *p=k_string_allocate(slot->bytes);memcpy(p,slot->data,slot->bytes);
    return (KString){p,slot->bytes,slot->scalars};
}
