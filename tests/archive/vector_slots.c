#include <assert.h>
#ifdef NDEBUG
#error slot oracle requires active assertions
#endif
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static bool fail_allocation;
static void *test_malloc(size_t n) {return fail_allocation?NULL:malloc(n);}
static void *test_realloc(void *p,size_t n) {return fail_allocation?NULL:realloc(p,n);}
#define malloc test_malloc
#define realloc test_realloc
#include "../compiler/native/generic.c"
#include "../compiler/native/vectors.c"
#undef malloc
#undef realloc
static uint64_t random_state=7149;
static uint64_t random64(void) {random_state^=random_state<<13;random_state^=random_state>>7;random_state^=random_state<<17;return random_state;}
int main(void) {
    KGenericVector generic[64];KIntVector legacy[64];uint64_t assertions=0;
    for(size_t i=0;i<64;++i) {
        generic[i]=k_generic_new((unsigned)i%11+1,8,4);legacy[i]=k_int_vector_new(4);
        assert(generic[i].id && legacy[i].id && (generic[i].id&63)==i && (legacy[i].id&63)==i);++assertions;
    }
    assert(!k_generic_new(1,8,0).id && !k_int_vector_new(0).id);++assertions;
    for(size_t i=0;i<200000;++i) {
        const uint64_t id=i%3?random64():generic[random64()%64].id;
        const unsigned kind=(unsigned)(random64()%13);KGenericSlot *want=NULL;KVectorSlot *old=NULL;
        for(size_t j=0;j<64;++j) {if(id && k_generic_slots[j].id==id && k_generic_slots[j].kind==kind)want=&k_generic_slots[j];if(id && k_vector_slots[j].id==id)old=&k_vector_slots[j];}
        assert(k_generic_find((KGenericVector){id},kind)==want);assert(k_vector_find((KIntVector){id})==old);assertions+=2;
    }
    for(size_t i=0;i<20000;++i) {
        const size_t j=random64()%64;const KGenericVector stale=generic[j];const KIntVector old=legacy[j];const unsigned kind=(unsigned)j%11+1;
        k_generic_free(stale,kind);k_int_vector_free(old);
        assert(!k_generic_find(stale,kind)&&!k_vector_find(old));
        generic[j]=k_generic_new(kind,8,4);legacy[j]=k_int_vector_new(4);
        assert(generic[j].id!=stale.id && legacy[j].id!=old.id && !k_generic_find(stale,kind)&&!k_vector_find(old));assertions+=2;
    }
    k_generic_cleanup();k_vector_cleanup();
    fail_allocation=true;const uint64_t serial=k_generic_next,oldserial=k_vector_next_id;
    assert(!k_generic_new(1,8,4).id && !k_int_vector_new(4).id);assert(k_generic_next==serial && k_vector_next_id==oldserial && !k_generic_payload && !k_vector_payload);assertions+=2;fail_allocation=false;
    KGenericVector v=k_generic_new(4,8,4);const int64_t a=11,b=22;assert(k_generic_push(v,4,&a)&&k_generic_push(v,4,&b));
    k_generic_swap(v,4,0,1);int64_t x;k_generic_get(v,4,0,&x);assert(x==22);k_generic_swap(v,4,0,0);k_generic_get(v,4,0,&x);assert(x==22);
    assert(!k_generic_truncate(v,4,-1)&&!k_generic_truncate(v,4,3)&&k_generic_require(v,4)->length==2);assert(k_generic_truncate(v,4,1)&&k_generic_require(v,4)->capacity==4);assertions+=5;
    fail_allocation=true;assert(!k_generic_reserve(v,4,20));assert(k_generic_require(v,4)->capacity==4&&k_generic_require(v,4)->length==1);k_generic_get(v,4,0,&x);assert(x==22);fail_allocation=false;assertions+=3;k_generic_free(v,4);
    for(size_t i=0;i<63;++i) {generic[i]=k_generic_new(1,8,0);legacy[i]=k_int_vector_new(0);}
    k_generic_next=UINT64_MAX>>6;k_vector_next_id=UINT64_MAX>>6;
    v=k_generic_new(1,8,0);KIntVector last=k_int_vector_new(0);
    assert(v.id==UINT64_MAX && last.id==UINT64_MAX && k_generic_find(v,1) && k_vector_find(last));
    k_generic_free(v,1);k_int_vector_free(last);assert(!k_generic_new(1,8,0).id && !k_int_vector_new(0).id && !k_generic_find(v,1) && !k_vector_find(last));assertions+=2;
    k_generic_cleanup();k_vector_cleanup();assert(!k_generic_payload&&!k_vector_payload);++assertions;
    printf("PASS %llu slot identity/kind/stale/churn/allocation/exhaustion assertions\n",(unsigned long long)assertions);return 0;
}
