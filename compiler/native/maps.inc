// generated from kmaps.c
constexpr char c_maps[]=R"KMAPS(#include <string.h>
// Open addressing hash table shared by map<K,V> and set<T>. Records live in
// parallel arrays so growth moves them verbatim, text keys and values own a
// heap copy and map_get returns its own copy of a text payload.
typedef struct {uint64_t id;} KMap;
_Static_assert(sizeof(KMap)==8 && _Alignof(KMap)==8,"map ABI");
typedef struct {
    uint64_t id;
    unsigned kind,key_text,value_text;
    size_t key_width,value_width,capacity,count,tombs;
    unsigned char *state,*keys,*values;
} KMapSlot;
static KMapSlot k_map_slots[32];
static uint64_t k_map_next=1;
static size_t k_map_payload;
static bool k_map_cleanup_registered;
#define K_MAP_MAX ((size_t)1048576)
#define K_MAP_TOTAL ((size_t)67108864)
static _Noreturn void k_map_trap(void) {fputs("Awl map trap: invalid handle, key, capacity or memory budget\n",stderr);abort();}
static KMapSlot *k_map_find(KMap h,unsigned kind) {
    if(!h.id) return NULL;
    KMapSlot *s=&k_map_slots[h.id&UINT64_C(31)];
    return s->id==h.id&&s->kind==kind?s:NULL;
}
static KMapSlot *k_map_require(KMap h,unsigned kind) {KMapSlot *s=k_map_find(h,kind);if(!s) k_map_trap();return s;}
static uint64_t k_map_hash(const unsigned char *data,size_t width,bool text) {
    uint64_t hash=UINT64_C(1469598103934665603);
    if(text) {
        uint64_t bytes=0;const unsigned char *contents=NULL;
        memcpy(&bytes,data+8,sizeof bytes);memcpy(&contents,data,sizeof contents);
        for(uint64_t i=0;i<bytes;++i) {hash^=contents[i];hash*=UINT64_C(1099511628211);}
        hash^=bytes;hash*=UINT64_C(1099511628211);
        return hash;
    }
    for(size_t i=0;i<width;++i) {hash^=data[i];hash*=UINT64_C(1099511628211);}
    return hash;
}
static bool k_map_equal(const unsigned char *a,const unsigned char *b,size_t width,bool text) {
    if(!text) return memcmp(a,b,width)==0;
    uint64_t ab=0,bb=0;memcpy(&ab,a+8,sizeof ab);memcpy(&bb,b+8,sizeof bb);
    if(ab!=bb) return false;
    const unsigned char *ad=NULL,*bd=NULL;memcpy(&ad,a,sizeof ad);memcpy(&bd,b,sizeof bd);
    if(!ab) return true;
    return ad&&bd&&memcmp(ad,bd,(size_t)ab)==0;
}
static void k_map_release_text(unsigned char *record) {
    void *data=NULL;uint64_t bytes=0;memcpy(&data,record,sizeof data);memcpy(&bytes,record+8,sizeof bytes);
    if(bytes>k_map_payload) k_map_trap();
    free(data);k_map_payload-=(size_t)bytes;
}
static void k_map_release_record(unsigned char *key,unsigned char *value,const KMapSlot *s) {
    if(s->key_text) k_map_release_text(key);
    if(s->value_text) k_map_release_text(value);
}
static void k_map_copy_record(unsigned char *target,const unsigned char *source,size_t width,bool text) {
    memcpy(target,source,width);
    if(!text) return;
    uint64_t bytes=0;memcpy(&bytes,source+8,sizeof bytes);void *own=NULL;
    if(bytes) {
        if(bytes>K_MAP_TOTAL-k_map_payload) k_map_trap();
        unsigned char *copy=malloc((size_t)bytes);
        if(!copy) k_map_trap();
        const unsigned char *data=NULL;memcpy(&data,source,sizeof data);
        memcpy(copy,data,(size_t)bytes);own=copy;k_map_payload+=(size_t)bytes;
    }
    memcpy(target,&own,sizeof own);
}
static void k_map_snapshot_record(unsigned char *target,const unsigned char *source,size_t width,bool text) {
    memcpy(target,source,width);
    if(text) {
#ifdef Awl_STRINGS_RUNTIME
        KString value;memcpy(&value,source,sizeof value);
        unsigned char *copy=k_string_allocate((size_t)value.bytes);
        if(value.bytes) memcpy(copy,value.data,(size_t)value.bytes);
        value.data=copy;memcpy(target,&value,sizeof value);
#else
        k_map_trap();
#endif
    }
}
static void k_map_cleanup(void) {
    for(size_t i=0;i<32;++i) {
        KMapSlot *s=&k_map_slots[i];
        for(size_t j=0;s->state&&j<s->capacity;++j) if(s->state[j]==1) k_map_release_record(s->keys+j*s->key_width,s->value_width?s->values+j*s->value_width:NULL,s);
        free(s->state);free(s->keys);free(s->values);*s=(KMapSlot){0};
    }
    k_map_payload=0;
}
static bool k_map_allocate(KMapSlot *s,size_t capacity) {
    const size_t keys=capacity*s->key_width,values=capacity*s->value_width,states=capacity;
    const size_t bytes=keys+values+states;
    if(bytes>K_MAP_TOTAL-k_map_payload) return false;
    unsigned char *state=calloc(states?states:1,1);
    unsigned char *keydata=keys?malloc(keys):NULL;
    unsigned char *valuedata=values?malloc(values):NULL;
    if(!state||(keys&&!keydata)||(values&&!valuedata)) {free(state);free(keydata);free(valuedata);return false;}
    if(keys) memset(keydata,0,keys);
    if(values) memset(valuedata,0,values);
    free(s->state);free(s->keys);free(s->values);
    s->state=state;s->keys=keydata;s->values=valuedata;s->capacity=capacity;s->tombs=0;k_map_payload+=bytes;
    return true;
}
static KMap k_map_new(unsigned kind,size_t key_width,size_t value_width,unsigned key_text,unsigned value_text,int64_t capacity) {
    if(capacity<0||(uint64_t)capacity>K_MAP_MAX||!key_width||k_map_next>(UINT64_MAX>>5)) return (KMap){0};
    KMapSlot *slot=NULL;for(size_t i=0;i<32;++i) if(!k_map_slots[i].id) {slot=&k_map_slots[i];break;}
    if(!slot) return (KMap){0};
    if(!k_map_cleanup_registered) {if(atexit(k_map_cleanup)) return (KMap){0};k_map_cleanup_registered=true;}
    size_t initial=4;while(initial<(size_t)capacity) initial*=2;
    *slot=(KMapSlot){(k_map_next++<<5)|(uint64_t)(slot-k_map_slots),kind,key_text,value_text,key_width,value_width,0,0,0,NULL,NULL,NULL};
    if(!k_map_allocate(slot,initial)) {*slot=(KMapSlot){0};return (KMap){0};}
    return (KMap){slot->id};
}
static void k_map_free(KMap h,unsigned kind) {
    KMapSlot *s=k_map_require(h,kind);
    for(size_t i=0;i<s->capacity;++i) if(s->state[i]==1) k_map_release_record(s->keys+i*s->key_width,s->value_width?s->values+i*s->value_width:NULL,s);
    k_map_payload-=s->capacity*s->key_width+s->capacity*s->value_width+s->capacity;
    free(s->state);free(s->keys);free(s->values);*s=(KMapSlot){0};
}
static bool k_map_valid(KMap h,unsigned kind) {return k_map_find(h,kind)!=NULL;}
static int64_t k_map_length(KMap h,unsigned kind) {return (int64_t)k_map_require(h,kind)->count;}
static void k_map_clear(KMap h,unsigned kind) {
    KMapSlot *s=k_map_require(h,kind);
    for(size_t i=0;i<s->capacity;++i) if(s->state[i]==1) k_map_release_record(s->keys+i*s->key_width,s->value_width?s->values+i*s->value_width:NULL,s);
    if(s->state) memset(s->state,0,s->capacity);
    s->count=0;s->tombs=0;
}
// Returns the record index for a key, or SIZE_MAX when absent. `free` selects
// the first tombstone on the probe path so insertion can reuse it.
static size_t k_map_slot_for(KMapSlot *s,const unsigned char *key,bool insert) {
    if(!s->capacity) return SIZE_MAX;
    const uint64_t hash=k_map_hash(key,s->key_width,s->key_text!=0);
    size_t mask=s->capacity-1,index=(size_t)hash&mask,reusable=SIZE_MAX;
    for(size_t probe=0;probe<s->capacity;++probe) {
        const unsigned char state=s->state[index];
        if(state==1) {if(k_map_equal(s->keys+index*s->key_width,key,s->key_width,s->key_text!=0)) return index;}
        else if(state==2) {if(reusable==SIZE_MAX) reusable=index;}
        else {if(!insert) return SIZE_MAX;return reusable!=SIZE_MAX?reusable:index;}
        index=(index+1)&mask;
    }
    return insert?reusable:SIZE_MAX;
}
static bool k_map_grow(KMapSlot *s) {
    if((s->count+1)*4<=s->capacity*3) return true;
    const size_t capacity=s->capacity*2;
    if(capacity>K_MAP_MAX) return false;
    const size_t bytes=capacity*s->key_width+capacity*s->value_width+capacity;
    if(bytes>K_MAP_TOTAL-k_map_payload) return false;
    unsigned char *state=calloc(capacity,1);
    unsigned char *keys=malloc(capacity*s->key_width);
    unsigned char *values=s->value_width?malloc(capacity*s->value_width):NULL;
    if(!state||!keys||(s->value_width&&!values)) {free(state);free(keys);free(values);return false;}
    for(size_t i=0;i<s->capacity;++i) if(s->state[i]==1) {
        const uint64_t hash=k_map_hash(s->keys+i*s->key_width,s->key_width,s->key_text!=0);
        size_t mask=capacity-1,index=(size_t)hash&mask;
        while(state[index]) index=(index+1)&mask;
        state[index]=1;
        memcpy(keys+index*s->key_width,s->keys+i*s->key_width,s->key_width);
        if(s->value_width) memcpy(values+index*s->value_width,s->values+i*s->value_width,s->value_width);
    }
    k_map_payload-=s->capacity*s->key_width+s->capacity*s->value_width+s->capacity;
    k_map_payload+=bytes;
    free(s->state);free(s->keys);free(s->values);
    s->state=state;s->keys=keys;s->values=values;s->capacity=capacity;s->tombs=0;
    return true;
}
static void k_map_set(KMap h,unsigned kind,const unsigned char *key,const unsigned char *value) {
    KMapSlot *s=k_map_require(h,kind);
    const size_t found=k_map_slot_for(s,key,false);
    if(found!=SIZE_MAX) {
        if(s->value_width) {
            unsigned char *slot=s->values+found*s->value_width;
            if(s->value_text) k_map_release_text(slot);
            k_map_copy_record(slot,value,s->value_width,s->value_text!=0);
        }
        return;
    }
    if(!k_map_grow(s)) k_map_trap();
    const size_t index=k_map_slot_for(s,key,true);
    if(index==SIZE_MAX) k_map_trap();
    if(s->state[index]==2) --s->tombs;
    s->state[index]=1;
    k_map_copy_record(s->keys+index*s->key_width,key,s->key_width,s->key_text!=0);
    if(s->value_width) k_map_copy_record(s->values+index*s->value_width,value,s->value_width,s->value_text!=0);
    ++s->count;
}
static void k_map_get(KMap h,unsigned kind,const unsigned char *key,unsigned char *result) {
    KMapSlot *s=k_map_require(h,kind);
    const size_t index=k_map_slot_for(s,key,false);
    if(index==SIZE_MAX||!s->value_width) k_map_trap();
    k_map_snapshot_record(result,s->values+index*s->value_width,s->value_width,s->value_text!=0);
}
static bool k_map_has(KMap h,unsigned kind,const unsigned char *key) {
    KMapSlot *s=k_map_require(h,kind);
    return k_map_slot_for(s,key,false)!=SIZE_MAX;
}
static bool k_map_remove(KMap h,unsigned kind,const unsigned char *key) {
    KMapSlot *s=k_map_require(h,kind);
    const size_t index=k_map_slot_for(s,key,false);
    if(index==SIZE_MAX) return false;
    k_map_release_record(s->keys+index*s->key_width,s->value_width?s->values+index*s->value_width:NULL,s);
    s->state[index]=2;++s->tombs;--s->count;
    return true;
}
// Dense scan over occupied slots, used by for-in and by map_keys/map_values.
static bool k_map_iter_next(KMap h,unsigned kind,int64_t *cursor,unsigned char *key,unsigned char *value) {
    KMapSlot *s=k_map_require(h,kind);
    if(!cursor||*cursor<0) k_map_trap();
    for(size_t index=(size_t)*cursor;index<s->capacity;++index) {
        if(s->state[index]!=1) continue;
        *cursor=(int64_t)index+1;
        if(key) k_map_snapshot_record(key,s->keys+index*s->key_width,s->key_width,s->key_text!=0);
        if(value&&s->value_width) k_map_snapshot_record(value,s->values+index*s->value_width,s->value_width,s->value_text!=0);
        return true;
    }
    *cursor=(int64_t)s->capacity;
    return false;
}
)KMAPS";
