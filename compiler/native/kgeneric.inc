// generated from kgeneric.c
constexpr char c_generic[]=R"KGENERIC(#include <string.h>
typedef struct {uint64_t id;} KGenericVector;
_Static_assert(sizeof(KGenericVector)==8 && _Alignof(KGenericVector)==8,"generic vector ABI");
typedef struct {uint64_t id;unsigned kind;size_t width,length,capacity;unsigned char *data;uint64_t epoch;} KGenericSlot;
static KGenericSlot k_generic_slots[64];
static uint64_t k_generic_next=1;
static size_t k_generic_payload;
static bool k_generic_cleanup_registered;
#define K_GENERIC_MAX ((size_t)1048576)
#define K_GENERIC_TOTAL ((size_t)67108864)
static _Noreturn void k_generic_trap(void) {fputs("Awl vector trap: invalid handle, element type, index or range\n",stderr);abort();}
static KGenericSlot *k_generic_find(KGenericVector v,unsigned kind) {
    if(!v.id) return NULL;
    KGenericSlot *s=&k_generic_slots[v.id&UINT64_C(63)];
    return s->id==v.id&&s->kind==kind?s:NULL;
}
static KGenericSlot *k_generic_require(KGenericVector v,unsigned kind) {KGenericSlot *s=k_generic_find(v,kind);if(!s) k_generic_trap();return s;}
static void k_generic_changed(KGenericSlot *s) {if(s->epoch==UINT64_MAX) k_generic_trap();++s->epoch;}
static void k_generic_clear(KGenericVector v,unsigned kind) {KGenericSlot *s=k_generic_require(v,kind);if(s->length) {s->length=0;k_generic_changed(s);}}
static void k_generic_cleanup(void) {
    for(size_t i=0;i<64;++i) {free(k_generic_slots[i].data);k_generic_slots[i]=(KGenericSlot){0};}
    k_generic_payload=0;
}
static KGenericVector k_generic_new(unsigned kind,size_t width,int64_t capacity) {
    if(capacity<0||(uint64_t)capacity>K_GENERIC_MAX||!width||width>24||k_generic_next>(UINT64_MAX>>6)) return (KGenericVector){0};
    size_t bytes=(size_t)capacity*width;
    if(bytes>K_GENERIC_TOTAL-k_generic_payload) return (KGenericVector){0};
    KGenericSlot *slot=NULL;for(size_t i=0;i<64;++i) if(!k_generic_slots[i].id) {slot=&k_generic_slots[i];break;}
    if(!slot) return (KGenericVector){0};
    if(!k_generic_cleanup_registered) {if(atexit(k_generic_cleanup)) return (KGenericVector){0};k_generic_cleanup_registered=true;}
    unsigned char *data=bytes?malloc(bytes):NULL;if(bytes&&!data) return (KGenericVector){0};
    *slot=(KGenericSlot){(k_generic_next++<<6)|(uint64_t)(slot-k_generic_slots),kind,width,0,(size_t)capacity,data,1};k_generic_payload+=bytes;return (KGenericVector){slot->id};
}
static void k_generic_free(KGenericVector v,unsigned kind) {
    KGenericSlot *s=k_generic_require(v,kind);k_generic_payload-=s->capacity*s->width;free(s->data);*s=(KGenericSlot){0};
}
static bool k_generic_reserve(KGenericVector v,unsigned kind,int64_t capacity) {
    KGenericSlot *s=k_generic_require(v,kind);
    if(capacity<0||(uint64_t)capacity>K_GENERIC_MAX) return false;
    if((size_t)capacity<=s->capacity) return true;
    size_t extra=((size_t)capacity-s->capacity)*s->width;
    if(extra>K_GENERIC_TOTAL-k_generic_payload) return false;
    // publish the new allocation only after success, failed growth preserves the full vector
    unsigned char *data=realloc(s->data,(size_t)capacity*s->width);if(!data) return false;
    s->data=data;s->capacity=(size_t)capacity;k_generic_payload+=extra;k_generic_changed(s);return true;
}
static bool k_generic_grow(KGenericVector v,KGenericSlot *s) {
    if(s->length<s->capacity) return true;
    if(s->capacity==K_GENERIC_MAX) return false;
    size_t next=s->capacity?s->capacity*2:8;if(next>K_GENERIC_MAX) next=K_GENERIC_MAX;
    return k_generic_reserve(v,s->kind,(int64_t)next);
}
static bool k_generic_push(KGenericVector v,unsigned kind,const void *value) {
    KGenericSlot *s=k_generic_require(v,kind);if(!k_generic_grow(v,s)) return false;
    memcpy(s->data+s->length*s->width,value,s->width);++s->length;k_generic_changed(s);return true;
}
static size_t k_generic_index(KGenericSlot *s,int64_t index,bool end) {
    if(index<0||(uint64_t)index>s->length||(!end&&(uint64_t)index==s->length)) k_generic_trap();
    return (size_t)index;
}
static void k_generic_get(KGenericVector v,unsigned kind,int64_t index,void *result) {
    KGenericSlot *s=k_generic_require(v,kind);const size_t i=k_generic_index(s,index,false);memcpy(result,s->data+i*s->width,s->width);
}
static void k_generic_set(KGenericVector v,unsigned kind,int64_t index,const void *value) {
    KGenericSlot *s=k_generic_require(v,kind);const size_t i=k_generic_index(s,index,false);memcpy(s->data+i*s->width,value,s->width);
}
static void k_generic_pop(KGenericVector v,unsigned kind,void *result) {
    KGenericSlot *s=k_generic_require(v,kind);if(!s->length) k_generic_trap();--s->length;k_generic_changed(s);memcpy(result,s->data+s->length*s->width,s->width);
}
static bool k_generic_insert(KGenericVector v,unsigned kind,int64_t index,const void *value) {
    KGenericSlot *s=k_generic_require(v,kind);const size_t i=k_generic_index(s,index,true);if(!k_generic_grow(v,s)) return false;
    memmove(s->data+(i+1)*s->width,s->data+i*s->width,(s->length-i)*s->width);memcpy(s->data+i*s->width,value,s->width);++s->length;k_generic_changed(s);return true;
}
static void k_generic_remove(KGenericVector v,unsigned kind,int64_t index,void *result) {
    KGenericSlot *s=k_generic_require(v,kind);const size_t i=k_generic_index(s,index,false);memcpy(result,s->data+i*s->width,s->width);
    memmove(s->data+i*s->width,s->data+(i+1)*s->width,(s->length-i-1)*s->width);--s->length;k_generic_changed(s);
}
static KGenericVector k_generic_slice(KGenericVector v,unsigned kind,int64_t start,int64_t count) {
    KGenericSlot *s=k_generic_require(v,kind);const size_t i=k_generic_index(s,start,true);
    if(count<0||(uint64_t)count>s->length-i) k_generic_trap();
    KGenericVector copy=k_generic_new(kind,s->width,count);if(!copy.id) return copy;
    KGenericSlot *to=k_generic_require(copy,kind);
    if(count) memcpy(to->data,s->data+i*s->width,(size_t)count*s->width);
    to->length=(size_t)count;return copy;
}

static bool k_generic_truncate(KGenericVector v,unsigned kind,int64_t length) {
    KGenericSlot *s=k_generic_require(v,kind);
    if(length<0||(uint64_t)length>s->length) return false;
    if(s->length!=(size_t)length) {s->length=(size_t)length;k_generic_changed(s);}return true;
}
static void k_generic_swap(KGenericVector v,unsigned kind,int64_t first,int64_t second) {
    KGenericSlot *s=k_generic_require(v,kind);
    const size_t a=k_generic_index(s,first,false),b=k_generic_index(s,second,false);
    if(a==b) return;
    unsigned char temporary[24];
    memcpy(temporary,s->data+a*s->width,s->width);
    memcpy(s->data+a*s->width,s->data+b*s->width,s->width);
    memcpy(s->data+b*s->width,temporary,s->width);
}

typedef struct {KGenericVector owner;uint64_t epoch,start,length;} KGenericView;
_Static_assert(sizeof(KGenericView)==32 && _Alignof(KGenericView)==8,"view ABI");
static KGenericSlot *k_view_find(KGenericView v,unsigned kind) {
    KGenericSlot *s=k_generic_find(v.owner,kind);
    return s&&s->epoch==v.epoch&&v.start<=s->length&&v.length<=s->length-v.start?s:NULL;
}
static KGenericSlot *k_view_require(KGenericView v,unsigned kind) {KGenericSlot *s=k_view_find(v,kind);if(!s) k_generic_trap();return s;}
static KGenericView k_generic_view(KGenericVector v,unsigned kind,int64_t start,int64_t count) {
    KGenericSlot *s=k_generic_require(v,kind);const size_t i=k_generic_index(s,start,true);
    if(count<0||(uint64_t)count>s->length-i) k_generic_trap();
    return (KGenericView){v,s->epoch,(uint64_t)i,(uint64_t)count};
}
static KGenericView k_view_slice(KGenericView v,unsigned kind,int64_t start,int64_t count) {
    k_view_require(v,kind);
    if(start<0||count<0||(uint64_t)start>v.length||(uint64_t)count>v.length-(uint64_t)start) k_generic_trap();
    v.start+=(uint64_t)start;v.length=(uint64_t)count;return v;
}
static void k_view_get(KGenericView v,unsigned kind,int64_t index,void *result,size_t width) {
    KGenericSlot *s=k_view_require(v,kind);
    if(index<0||(uint64_t)index>=v.length||s->width!=width) k_generic_trap();
    memcpy(result,s->data+((size_t)v.start+(size_t)index)*width,width);
}
)KGENERIC";
