#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include <sys/resource.h>
static bool fail_malloc,fail_realloc;
static void *fault_malloc(size_t n) {return fail_malloc?NULL:malloc(n);}
static void *fault_realloc(void *p,size_t n) {return fail_realloc?NULL:realloc(p,n);}
#define malloc fault_malloc
#define realloc fault_realloc
#include "../compiler/native/kgeneric.c"
#undef malloc
#undef realloc
static void check(KGenericVector v,size_t cap,size_t len,size_t bytes) {
    KGenericSlot *s=k_generic_require(v,4);assert(s->capacity==cap&&s->length==len&&k_generic_payload==bytes);
    for(size_t i=0;i<len;++i) {int64_t n=-1;k_generic_get(v,4,(int64_t)i,&n);assert(n==(int64_t)i);}
}
static void trap(KGenericVector v,unsigned kind,unsigned action) {
    pid_t child=fork();assert(child>=0);
    if(!child) {
        assert(freopen("/dev/null","w",stderr));int64_t result;
        if(action==0) k_generic_get(v,kind,0,&result);
        else if(action==1) k_generic_set(v,kind,0,&result);
        else if(action==2) k_generic_slice(v,kind,0,0);
        else if(action==3) k_generic_free(v,kind);
        else k_generic_reserve(v,kind,0);
        _exit(0);
    }
    int status;assert(waitpid(child,&status,0)==child);assert(WIFSIGNALED(status)&&WTERMSIG(status)==SIGABRT);
}
int main(void) {
    struct rlimit limit={0,0};assert(!setrlimit(RLIMIT_CORE,&limit));
    fail_malloc=true;assert(!k_generic_new(4,8,1).id);assert(k_generic_payload==0&&k_generic_next==1);
    KGenericVector zero=k_generic_new(4,8,0);assert(zero.id);k_generic_free(zero,4);fail_malloc=false;
    KGenericVector v=k_generic_new(4,8,8);assert(v.id);
    for(int64_t i=0;i<8;++i) assert(k_generic_push(v,4,&i));
    KGenericSlot *s=k_generic_require(v,4);unsigned char *old=s->data;uint64_t next=k_generic_next;int64_t nine=9;
    fail_realloc=true;
    assert(!k_generic_reserve(v,4,16));check(v,8,8,64);assert(s->data==old);
    assert(!k_generic_push(v,4,&nine));check(v,8,8,64);
    assert(!k_generic_insert(v,4,4,&nine));check(v,8,8,64);
    fail_malloc=true;assert(!k_generic_slice(v,4,0,8).id);check(v,8,8,64);assert(k_generic_next==next);
    fail_malloc=false;fail_realloc=false;
    assert(k_generic_insert(v,4,8,&nine));assert(s->length==9&&s->capacity==16);
    int64_t result=0;k_generic_remove(v,4,8,&result);assert(result==9);check(v,16,8,128);
    KGenericVector copy=k_generic_slice(v,4,2,3);assert(copy.id);k_generic_set(v,4,2,&nine);k_generic_get(copy,4,0,&result);assert(result==2);
    for(unsigned action=0;action<5;++action) trap(v,10,action);
    KGenericVector stale=v;k_generic_free(v,4);KGenericVector fresh=k_generic_new(4,8,0);assert(fresh.id!=stale.id&&!k_generic_find(stale,4));trap(stale,4,0);trap(stale,4,3);
    k_generic_free(copy,4);k_generic_free(fresh,4);assert(k_generic_payload==0);
    k_generic_next=UINT64_MAX;assert(!k_generic_new(4,8,0).id);
    puts("PASS allocation-failure preservation, independent slice copy, 7 wrong-tag/stale traps, id exhaustion");return 0;
}
