/* Single-threaded, reclaimable growable i64 vectors. No pointers escape.
 * Manual copies alias an identity; scoped/borrow/own rules restrict owner copies. */
#include <string.h>
typedef struct {uint64_t id;} KIntVector;
_Static_assert(sizeof(KIntVector)==8 && _Alignof(KIntVector)==8,"vector ABI");
typedef struct {uint64_t id;int64_t *data;size_t capacity,length;} KVectorSlot;
static KVectorSlot k_vector_slots[64];
static uint64_t k_vector_next_id=1;
static size_t k_vector_payload;
static bool k_vector_cleanup_registered;
#define K_VECTOR_MAX ((size_t)1048576)
#define K_VECTOR_TOTAL ((size_t)67108864)
static _Noreturn void k_vector_trap(void) {fputs("Awl int vector trap: invalid handle or index\n",stderr);abort();}
static KVectorSlot *k_vector_find(KIntVector v) {
    if(!v.id) return NULL;
    KVectorSlot *s=&k_vector_slots[v.id&UINT64_C(63)];
    return s->id==v.id?s:NULL;
}
static KVectorSlot *k_vector_require(KIntVector v) {KVectorSlot *s=k_vector_find(v);if(!s) k_vector_trap();return s;}
static void k_vector_cleanup(void) {
    for(size_t i=0;i<64;++i) {free(k_vector_slots[i].data);k_vector_slots[i]=(KVectorSlot){0};}
    k_vector_payload=0;
}
static KIntVector k_int_vector_new(int64_t capacity) {
    if(capacity<0||(uint64_t)capacity>K_VECTOR_MAX||k_vector_next_id>(UINT64_MAX>>6)) return (KIntVector){0};
    size_t bytes=(size_t)capacity*sizeof(int64_t);
    if(bytes>K_VECTOR_TOTAL-k_vector_payload) return (KIntVector){0};
    KVectorSlot *s=NULL;for(size_t i=0;i<64;++i) if(!k_vector_slots[i].id) {s=&k_vector_slots[i];break;}
    if(!s) return (KIntVector){0};
    if(!k_vector_cleanup_registered) {if(atexit(k_vector_cleanup)) return (KIntVector){0};k_vector_cleanup_registered=true;}
    int64_t *p=bytes?malloc(bytes):NULL;if(bytes&&!p) return (KIntVector){0};
    *s=(KVectorSlot){(k_vector_next_id++<<6)|(uint64_t)(s-k_vector_slots),p,(size_t)capacity,0};k_vector_payload+=bytes;
    return (KIntVector){s->id};
}
static bool k_int_vector_valid(KIntVector v) {return k_vector_find(v)!=NULL;}
static void k_int_vector_free(KIntVector v) {
    KVectorSlot *s=k_vector_require(v);k_vector_payload-=s->capacity*sizeof(int64_t);free(s->data);*s=(KVectorSlot){0};
}
static int64_t k_int_vector_length(KIntVector v) {return (int64_t)k_vector_require(v)->length;}
static int64_t k_int_vector_capacity(KIntVector v) {return (int64_t)k_vector_require(v)->capacity;}
/* Failure leaves length, capacity and all existing elements unchanged. */
static bool k_int_vector_reserve(KIntVector v,int64_t capacity) {
    KVectorSlot *s=k_vector_require(v);
    if(capacity<0||(uint64_t)capacity>K_VECTOR_MAX) return false;
    if((size_t)capacity<=s->capacity) return true;
    size_t extra=((size_t)capacity-s->capacity)*sizeof(int64_t);
    if(extra>K_VECTOR_TOTAL-k_vector_payload) return false;
    int64_t *p=realloc(s->data,(size_t)capacity*sizeof(int64_t));if(!p) return false;
    s->data=p;s->capacity=(size_t)capacity;k_vector_payload+=extra;return true;
}
static bool k_vector_grow(KIntVector v,KVectorSlot *s) {
    if(s->length<s->capacity) return true;
    if(s->capacity==K_VECTOR_MAX) return false;
    size_t next=s->capacity?s->capacity*2:8;if(next>K_VECTOR_MAX) next=K_VECTOR_MAX;
    return k_int_vector_reserve(v,(int64_t)next);
}
static bool k_int_vector_push(KIntVector v,int64_t value) {
    KVectorSlot *s=k_vector_require(v);if(!k_vector_grow(v,s)) return false;s->data[s->length++]=value;return true;
}
static int64_t k_int_vector_get(KIntVector v,int64_t index) {
    KVectorSlot *s=k_vector_require(v);if(index<0||(uint64_t)index>=s->length) k_vector_trap();return s->data[(size_t)index];
}
static void k_int_vector_set(KIntVector v,int64_t index,int64_t value) {
    KVectorSlot *s=k_vector_require(v);if(index<0||(uint64_t)index>=s->length) k_vector_trap();s->data[(size_t)index]=value;
}
static int64_t k_int_vector_pop(KIntVector v) {
    KVectorSlot *s=k_vector_require(v);if(!s->length) k_vector_trap();return s->data[--s->length];
}
static void k_int_vector_clear(KIntVector v) {k_vector_require(v)->length=0;}
static bool k_int_vector_insert(KIntVector v,int64_t index,int64_t value) {
    KVectorSlot *s=k_vector_require(v);if(index<0||(uint64_t)index>s->length) k_vector_trap();
    if(!k_vector_grow(v,s)) return false;
    size_t i=(size_t)index;memmove(s->data+i+1,s->data+i,(s->length-i)*sizeof(int64_t));s->data[i]=value;++s->length;return true;
}
static int64_t k_int_vector_remove(KIntVector v,int64_t index) {
    KVectorSlot *s=k_vector_require(v);if(index<0||(uint64_t)index>=s->length) k_vector_trap();
    size_t i=(size_t)index;int64_t value=s->data[i];memmove(s->data+i,s->data+i+1,(s->length-i-1)*sizeof(int64_t));--s->length;return value;
}
