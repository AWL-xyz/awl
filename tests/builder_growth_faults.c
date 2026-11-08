#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#ifdef NDEBUG
#error builder oracle requires assertions
#endif
#include <assert.h>
#include "kstrings.c"
static bool fail;static unsigned reallocs;
static void *resize(void *p,size_t n){++reallocs;return fail?NULL:realloc(p,n);}
#define realloc resize
#include "kbuilders.c"
#undef realloc
int main(int argc,char **argv){
 KTextBuilder b=k_text_builder_new(10);KString text={(const unsigned char *)"aé🦉é",10,5};assert(!k_text_builder_append(b,text));
 if(argc>1){k_text_builder_free(b);if(!strcmp(argv[1],"reserve"))k_text_builder_reserve(b,20);else k_text_builder_truncate(b,0);return 2;}
 KBuilderSlot *slot=k_builder_require(b);unsigned char *pointer=slot->data;size_t payload=k_builder_payload;fail=true;
 assert(!k_text_builder_reserve(b,100));assert(slot->data==pointer&&slot->capacity==10&&slot->bytes==10&&slot->scalars==5&&k_builder_payload==payload&&!memcmp(slot->data,text.data,10));
 unsigned before=reallocs;assert(k_text_builder_reserve(b,0)&&k_text_builder_reserve(b,10));assert(!k_text_builder_reserve(b,-1)&&!k_text_builder_reserve(b,16777217));assert(reallocs==before);
 assert(!k_text_builder_truncate(b,-1)&&!k_text_builder_truncate(b,6));assert(slot->bytes==10&&slot->scalars==5);KString snapshot=k_text_builder_snapshot(b);fail=false;
 assert(k_text_builder_reserve(b,4096));assert(k_builder_payload==4096);assert(k_text_builder_truncate(b,3));assert(slot->bytes==7&&slot->scalars==3&&!memcmp(snapshot.data,text.data,10));
 assert(!k_text_builder_codepoint(b,0));assert(slot->bytes==8&&slot->scalars==4);assert(k_text_builder_truncate(b,0)&&slot->bytes==0&&slot->capacity==4096);k_text_builder_free(b);assert(!k_builder_payload);
 KTextBuilder big[4];for(unsigned i=0;i<4;++i){big[i]=k_text_builder_new(16777216);assert(k_text_builder_valid(big[i]));}b=k_text_builder_new(0);assert(k_text_builder_valid(b));before=reallocs;assert(!k_text_builder_reserve(b,1)&&reallocs==before);assert(k_builder_payload==67108864);k_text_builder_free(big[0]);assert(k_text_builder_reserve(b,1));for(unsigned i=1;i<4;++i)k_text_builder_free(big[i]);k_text_builder_free(b);assert(k_builder_payload==0);
 puts("PASS failed realloc atomicity, no-op/invalid limits, UTF8 boundaries, immutable snapshot, 64MiB budget/reuse");return 0;
}
