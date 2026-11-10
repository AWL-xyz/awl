// generated from kstreams.c
constexpr char c_streams[]=R"KSTREAMS(#if defined(__linux__)
#include <sys/auxv.h>
#endif
static int64_t k_stream_error(void) {
#if defined(__linux__)
    if(errno==EAGAIN || errno==EWOULDBLOCK) return -10;
    if(errno==EPIPE) return -11;
#endif
    return k_file_error();
}
static int64_t k_stdin_read(int64_t buffer,int64_t offset,int64_t count) {
    unsigned char *data=k_file_range(buffer,offset,count);
    if(!count) return 0;
#if defined(__linux__)
    ssize_t n;
    do {n=read(STDIN_FILENO,data,(size_t)count);} while(n<0 && errno==EINTR);
    return n<0?k_stream_error():(int64_t)n;
#else
    (void)data;return -6;
#endif
}
static int64_t k_stream_write(int descriptor,FILE *stream,int64_t buffer,int64_t offset,int64_t count) {
    unsigned char *data=k_file_range(buffer,offset,count);
    if(!count) return 0;
#if defined(__linux__)
    // print uses stdio, flush it before writing raw bytes to preserve program order
    if(fflush(stream)) return k_stream_error();
    ssize_t n;
    do {n=write(descriptor,data,(size_t)count);} while(n<0 && errno==EINTR);
    return n<0?k_stream_error():(int64_t)n;
#else
    (void)descriptor;(void)stream;(void)data;return -6;
#endif
}
static int64_t k_stdout_write(int64_t buffer,int64_t offset,int64_t count) {return k_stream_write(1,stdout,buffer,offset,count);}
static int64_t k_stderr_write(int64_t buffer,int64_t offset,int64_t count) {return k_stream_write(2,stderr,buffer,offset,count);}
static int64_t k_stream_flush(FILE *stream) {
#if defined(__linux__)
    return fflush(stream)?k_stream_error():0;
#else
    (void)stream;return -6;
#endif
}
static int64_t k_stdout_flush(void) {return k_stream_flush(stdout);}
static int64_t k_stderr_flush(void) {return k_stream_flush(stderr);}
static int64_t k_env_lookup(KString name,const char **value,size_t *length) {
    if(!name.bytes || name.bytes>4095 || memchr(name.data,0,name.bytes) || memchr(name.data,'=',name.bytes)) return -5;
#if defined(__linux__)
    if(getauxval(AT_SECURE)) return -4;
    char key[4096];memcpy(key,name.data,name.bytes);key[name.bytes]=0;
    const char *found=getenv(key);
    if(!found) return -2;
    size_t n=0;
    while(n<=1048576 && found[n]) ++n;
    if(n>1048576) return -5;
    *value=found;*length=n;return 0;
#else
    (void)value;(void)length;return -6;
#endif
}
static int64_t k_env_size(KString name) {
    const char *value=NULL;size_t length=0;int64_t error=k_env_lookup(name,&value,&length);
    return error?error:(int64_t)length;
}
static int64_t k_env_read(KString name,int64_t buffer,int64_t offset,int64_t count) {
    unsigned char *data=k_file_range(buffer,offset,count);const char *value=NULL;size_t length=0;
    int64_t error=k_env_lookup(name,&value,&length);
    if(error) return error;
    if(length>(uint64_t)count) return -5;
    memcpy(data,value,length);return (int64_t)length;
}
)KSTREAMS";
