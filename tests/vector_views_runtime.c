#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
static bool fail_alloc;
static unsigned allocations;
static void *allocate(size_t n){++allocations;return fail_alloc?NULL:malloc(n);}
static void *resize(void *p,size_t n){++allocations;return fail_alloc?NULL:realloc(p,n);}
#define malloc allocate
#define realloc resize
#include "kgeneric.c"
#undef malloc
#undef realloc
int main(int argc,char **argv){
 KGenericVector owner=k_generic_new(4,8,2);assert(owner.id);int64_t a=7,b=9;assert(k_generic_push(owner,4,&a));assert(k_generic_push(owner,4,&b));KGenericView view=k_generic_view(owner,4,0,2);
 if(argc>1){
  if(!strcmp(argv[1],"epoch")){k_generic_require(owner,4)->epoch=UINT64_MAX;k_generic_clear(owner,4);}
  if(!strcmp(argv[1],"width")){k_view_get(view,4,0,&a,4);}
  if(!strcmp(argv[1],"stale")){k_generic_free(owner,4);k_view_get(view,4,0,&a,8);}
  if(!strcmp(argv[1],"forged")){view.start=UINT64_MAX;k_view_get(view,4,0,&a,8);}
  return 1;
 }
 KGenericView forged=view;forged.start=UINT64_MAX;assert(!k_view_find(forged,4));forged=view;forged.length=UINT64_MAX;assert(!k_view_find(forged,4));forged=view;++forged.epoch;assert(!k_view_find(forged,4));forged=view;forged.owner.id=0;assert(!k_view_find(forged,4));assert(!k_view_find(view,5));
 unsigned before=allocations;fail_alloc=true;
 for(unsigned i=0;i<100000;++i){KGenericView sub=k_view_slice(view,4,1,1);int64_t result=0;k_view_get(sub,4,0,&result,8);assert(result==9);}
 assert(allocations==before);assert(!k_generic_reserve(owner,4,4));assert(k_view_find(view,4));assert(k_generic_require(owner,4)->capacity==2);assert(!k_generic_push(owner,4,&a));assert(k_view_find(view,4));
 KGenericVector copy=k_generic_slice(owner,4,0,2);assert(!copy.id);assert(k_view_find(view,4));
 fail_alloc=false;k_generic_free(owner,4);assert(!k_view_find(view,4));
 for(unsigned i=0;i<10000;++i){KGenericVector fresh=k_generic_new(4,8,1);assert(fresh.id!=owner.id);assert(k_generic_push(fresh,4,&a));assert(!k_view_find(view,4));k_generic_free(fresh,4);}
 puts("PASS 100000 zero-allocation subviews, allocation failure rollback, stale/reused owner identity");return 0;
}
