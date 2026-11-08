#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#include <assert.h>
#ifdef NDEBUG
#error assertions required
#endif
#include "kstrings.c"
#include "kmaps.c"
static uint64_t random_state=981;
static uint64_t next(void){random_state=random_state*UINT64_C(6364136223846793005)+1;return random_state;}
int main(int argc,char **argv){
 KMap map=k_map_new(1,8,8,0,0,5);assert(k_map_valid(map,1));assert(k_map_require(map,1)->capacity==8);
 int64_t zero=0;
 if(argc>1&&!strcmp(argv[1],"stale")){k_map_free(map,1);k_map_has(map,1,(unsigned char *)&zero);return 2;}
 if(argc>1){k_map_free(map,1);map=k_map_new(2,8,sizeof(KString),0,1,5);unsigned char *data=k_string_allocate(8388608);memset(data,'x',8388608);KString value={data,8388608,8388608};for(int64_t i=0;i<8;++i)k_map_set(map,2,(unsigned char *)&i,(unsigned char *)&value);return 3;}
 bool present[128]={0};int64_t values[128]={0};unsigned count=0;
 for(unsigned step=0;step<10000;++step){int64_t key=(int64_t)((next()>>16)%128),value=(int64_t)(next()>>1);unsigned op=(unsigned)((next()>>32)%31);
  if(op<16){k_map_set(map,1,(unsigned char *)&key,(unsigned char *)&value);if(!present[key])++count;present[key]=true;values[key]=value;}
  else if(op<30){assert(k_map_remove(map,1,(unsigned char *)&key)==present[key]);if(present[key])--count;present[key]=false;}
  else{k_map_clear(map,1);memset(present,0,sizeof present);count=0;}
  assert(k_map_length(map,1)==count);
  for(int64_t k=0;k<128;++k){assert(k_map_has(map,1,(unsigned char *)&k)==present[k]);if(present[k]){int64_t got=0;k_map_get(map,1,(unsigned char *)&k,(unsigned char *)&got);assert(got==values[k]);}}
 }
 k_map_free(map,1);assert(k_map_payload==0);
 map=k_map_new(2,8,sizeof(KString),0,1,5);KString text={(const unsigned char *)"owl 🦉",8,5},saved={0};k_map_set(map,2,(unsigned char *)&zero,(unsigned char *)&text);size_t arrays=k_map_require(map,2)->capacity*33;assert(k_map_payload==arrays+8);
 k_map_get(map,2,(unsigned char *)&zero,(unsigned char *)&saved);for(unsigned i=0;i<10;++i){k_map_set(map,2,(unsigned char *)&zero,(unsigned char *)&text);assert(k_map_payload==arrays+8);}k_map_free(map,2);assert(!k_map_payload&&saved.bytes==8&&!memcmp(saved.data,text.data,8));
 map=k_map_new(3,sizeof(KString),0,1,0,5);k_map_set(map,3,(unsigned char *)&text,NULL);int64_t cursor=0;KString key={0};assert(k_map_iter_next(map,3,&cursor,(unsigned char *)&key,NULL));assert(k_map_remove(map,3,(unsigned char *)&text));k_map_free(map,3);assert(!k_map_payload&&key.bytes==8&&!memcmp(key.data,text.data,8));puts("PASS10000 independently modeled map operations, non-power-of-two capacity, zero-width set, text budget/update and immutable snapshots");return 0;
}
