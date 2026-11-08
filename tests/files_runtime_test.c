/* Linux contributor fault injection and UTF-8 oracle probe; NOT product I/O. */
#define _POSIX_C_SOURCE 200809L
#undef NDEBUG
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <limits.h>
#include <unistd.h>
#include <errno.h>
#include "../compiler/native/kstrings.c"
#include "../compiler/native/kplatform.c"
static int read_fault,write_fault,flush_fault,close_fault;
static ssize_t test_read(int fd,void *data,size_t size) {
    if(read_fault==1){read_fault=0;errno=EINTR;return -1;}
    if(read_fault==2){errno=EIO;return -1;}
    return read(fd,data,size>3?3:size);
}
static ssize_t test_write(int fd,const void *data,size_t size) {
    if(write_fault==1){write_fault=0;errno=EINTR;return -1;}
    if(write_fault==2){errno=ENOSPC;return -1;}
    return write(fd,data,size>7?7:size);
}
static int test_flush(int fd) {if(flush_fault){errno=EIO;return -1;}return fsync(fd);}
static int test_close(int fd) {int r=close(fd);if(close_fault){errno=EIO;return -1;}return r;}
#define read test_read
#define write test_write
#define fsync test_flush
#define close test_close
#include "../compiler/native/kfiles.c"
#undef read
#undef write
#undef fsync
#undef close
static KString text(const char *s){return (KString){(const unsigned char*)s,strlen(s),strlen(s)};}
int main(void) {
    char path[]="/tmp/Awl-file-fault-XXXXXX";int raw=mkstemp(path);assert(raw>=0);assert(close(raw)==0);
    int64_t f=k_file_open(text(path),2),b=k_buffer_new(32);assert(f>=K_FILE_BASE && b>0);
    assert(fcntl(k_file_require(f)->native,F_GETFD)&FD_CLOEXEC);
    for(int i=0;i<32;++i)k_buffer_set(b,i,(uint8_t)i);
    write_fault=1;assert(k_file_write(f,b,0,32)==7);assert(write_fault==0);
    size_t offset=7;while(offset<32){int64_t n=k_file_write(f,b,(int64_t)offset,32-(int64_t)offset);assert(n>0 && n<=7);offset+=(size_t)n;}
    write_fault=2;assert(k_file_write(f,b,0,1)==-8);write_fault=0;
    flush_fault=1;assert(k_file_flush(f)==-1);flush_fault=0;assert(k_file_flush(f)==0);
    raw=k_file_require(f)->native;close_fault=1;assert(k_file_close(f)==-1);close_fault=0;assert(!k_file_valid(f));assert(fcntl(raw,F_GETFD)==-1 && errno==EBADF);
    f=k_file_open(text(path),0);assert(f>=K_FILE_BASE);assert(k_file_size(f)==32);
    read_fault=1;assert(k_file_read(f,b,0,32)==3);assert(read_fault==0);
    read_fault=2;assert(k_file_read(f,b,0,1)==-1);read_fault=0;
    assert(k_file_seek(f,0)==0);offset=0;while(offset<32){int64_t n=k_file_read(f,b,(int64_t)offset,32-(int64_t)offset);assert(n>0 && n<=3);offset+=(size_t)n;}
    assert(k_file_read(f,b,0,1)==0);for(int i=0;i<32;++i)assert(k_buffer_get(b,i)==i);assert(k_file_close(f)==0);
    unsigned char longpath[4096];memset(longpath,'a',sizeof(longpath));assert(k_file_open((KString){longpath,sizeof(longpath),sizeof(longpath)},0)==-5);
    unsigned char bad[]={255};assert(k_file_open((KString){bad,1,1},0)==-5);
    for(int i=0;i<32;++i)assert(k_file_open(text(path),0)>=K_FILE_BASE);assert(k_file_open(text(path),0)==-7);
    assert(k_file_cleanup_registered);k_file_cleanup();for(int i=0;i<32;++i)assert(k_files[i].id==0);
    k_buffer_free(b);assert(unlink(path)==0);puts("PASS short read/write, EINTR retries, ENOSPC, flush/close errors, CLOEXEC, bounds and cleanup");
    char line[256];while(fgets(line,sizeof(line),stdin)) {
        unsigned char bytes[64];size_t count=0,scalars=0;
        for(size_t i=0;line[i] && line[i]!='\n';i+=2){unsigned int value=0;assert(count<sizeof(bytes));assert(sscanf(line+i,"%2x",&value)==1);bytes[count++]=(unsigned char)value;}
        bool valid=k_utf8_scan(bytes,count,&scalars);printf("%d %zu\n",valid,valid?scalars:0);
    }
    return 0;
}
