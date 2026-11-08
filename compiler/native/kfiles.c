/* Bounded regular-file handles, synchronous and single-threaded. No pointers
 * escape. OS errors are negative results; forged handles/ranges trap. */
#include <errno.h>
#if defined(_WIN32)
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#endif
#define K_FILE_BASE INT64_C(4611686018427387904)
typedef struct {
    int64_t id;int mode;
#if defined(_WIN32)
    HANDLE native;
#else
    int native;
#endif
} KFile;
static KFile k_files[32];
static int64_t k_file_next=K_FILE_BASE;
static bool k_file_cleanup_registered;
static int64_t k_file_error(void) {
#if defined(_WIN32)
    switch(GetLastError()) {
    case ERROR_FILE_NOT_FOUND:case ERROR_PATH_NOT_FOUND:return -2;
    case ERROR_FILE_EXISTS:case ERROR_ALREADY_EXISTS:return -3;
    case ERROR_ACCESS_DENIED:case ERROR_SHARING_VIOLATION:case ERROR_WRITE_PROTECT:return -4;
    case ERROR_INVALID_NAME:case ERROR_BAD_PATHNAME:case ERROR_FILENAME_EXCED_RANGE:case ERROR_INVALID_PARAMETER:return -5;
    case ERROR_TOO_MANY_OPEN_FILES:return -7;
    case ERROR_DISK_FULL:case ERROR_HANDLE_DISK_FULL:case ERROR_FILE_TOO_LARGE:return -8;
    case ERROR_NOT_ENOUGH_MEMORY:case ERROR_OUTOFMEMORY:return -9;
    default:return -1;
    }
#else
    switch(errno) {
    case ENOENT:case ENOTDIR:return -2;
    case EEXIST:return -3;
    case EACCES:case EPERM:case EROFS:return -4;
    case EINVAL:case ENAMETOOLONG:return -5;
    case ELOOP:return -6;
    case EMFILE:case ENFILE:return -7;
    case ENOSPC:case EDQUOT:case EFBIG:return -8;
    case ENOMEM:return -9;
    default:return -1;
    }
#endif
}
static KFile *k_file_require(int64_t id) {
    for(size_t i=0;i<32;++i) if(id>=K_FILE_BASE && k_files[i].id==id) return &k_files[i];
    k_resource_trap();
}
static bool k_file_valid(int64_t id) {
    for(size_t i=0;i<32;++i) if(id>=K_FILE_BASE && k_files[i].id==id) return true;
    return false;
}
static int64_t k_file_close(int64_t id) {
    KFile *f=k_file_require(id);
#if defined(_WIN32)
    bool ok=CloseHandle(f->native)!=0;
#else
    /* On Linux close(EINTR) has released the descriptor: never retry it. */
    bool ok=close(f->native)==0;
#endif
    int64_t result=ok?0:k_file_error();memset(f,0,sizeof(*f));return result;
}
static void k_file_cleanup(void) {for(size_t i=0;i<32;++i) if(k_files[i].id) (void)k_file_close(k_files[i].id);}
static int64_t k_file_open(KString path,int64_t mode) {
    size_t scalars=0;
    if(mode<0 || mode>2 || !path.bytes || path.bytes>4095 || memchr(path.data,0,path.bytes) || !k_utf8_scan(path.data,path.bytes,&scalars)) return -5;
    if(k_file_next==INT64_MAX) return -7;
    KFile *f=NULL;for(size_t i=0;i<32;++i) if(!k_files[i].id) {f=&k_files[i];break;}if(!f) return -7;
    if(!k_file_cleanup_registered) {if(atexit(k_file_cleanup)) return -9;k_file_cleanup_registered=true;}
#if defined(_WIN32)
    wchar_t text[4096];int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,(const char*)path.data,(int)path.bytes,text,4095);if(!n) return -5;text[n]=0;
    /* No NT device namespaces/alternate streams. Ordinary UNC disk paths allowed. */
    if(n>=4 && (text[0]=='\\' || text[0]=='/') && (text[1]=='\\' || text[1]=='/') && (text[2]=='.' || text[2]=='?')) return -5;
    for(int i=0;i<n;++i) if(text[i]==':' && !(i==1 && ((text[0]>='A' && text[0]<='Z') || (text[0]>='a' && text[0]<='z')))) return -5;
    HANDLE native=CreateFileW(text,mode?GENERIC_WRITE:GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,mode==0?OPEN_EXISTING:mode==1?CREATE_NEW:OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
    if(native==INVALID_HANDLE_VALUE) return k_file_error();
    BY_HANDLE_FILE_INFORMATION info;
    if(GetFileType(native)!=FILE_TYPE_DISK || !GetFileInformationByHandle(native,&info) || (info.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))) {CloseHandle(native);return -6;}
    if(mode==2) {LARGE_INTEGER zero;zero.QuadPart=0;if(!SetFilePointerEx(native,zero,NULL,FILE_BEGIN) || !SetEndOfFile(native)) {int64_t error=k_file_error();CloseHandle(native);return error;}}
#else
    char text[4096];memcpy(text,path.data,path.bytes);text[path.bytes]=0;
    int flags=(mode?O_WRONLY:O_RDONLY)|O_CLOEXEC|O_NONBLOCK|O_NOFOLLOW;
    if(mode) flags|=O_CREAT;
    if(mode==1) flags|=O_EXCL;
    int native;do {native=open(text,flags,0600);} while(native<0 && errno==EINTR);
    if(native<0) return k_file_error();
    struct stat info;if(fstat(native,&info) || !S_ISREG(info.st_mode)) {close(native);return -6;}
    if(mode==2) {int result;do {result=ftruncate(native,0);} while(result<0 && errno==EINTR);if(result<0) {int64_t error=k_file_error();close(native);return error;}}
#endif
    *f=(KFile){k_file_next++,(int)mode,native};return f->id;
}
static int64_t k_file_size(int64_t id) {
    KFile *f=k_file_require(id);
#if defined(_WIN32)
    LARGE_INTEGER size;if(!GetFileSizeEx(f->native,&size)) return k_file_error();return size.QuadPart<0?-1:(int64_t)size.QuadPart;
#else
    struct stat info;if(fstat(f->native,&info)) return k_file_error();return info.st_size<0?-1:(int64_t)info.st_size;
#endif
}
static int64_t k_file_seek(int64_t id,int64_t offset) {
    KFile *f=k_file_require(id);if(offset<0) return -5;
#if defined(_WIN32)
    LARGE_INTEGER at;at.QuadPart=offset;return SetFilePointerEx(f->native,at,NULL,FILE_BEGIN)?0:k_file_error();
#else
    _Static_assert(sizeof(off_t)>=8,"64-bit file offsets required");off_t result;do {result=lseek(f->native,(off_t)offset,SEEK_SET);} while(result<0 && errno==EINTR);return result<0?k_file_error():0;
#endif
}
static unsigned char *k_file_range(int64_t buffer,int64_t offset,int64_t count) {
    KBuffer *b=k_buffer(buffer);if(offset<0 || count<0 || (uint64_t)offset>b->size || (uint64_t)count>b->size-(size_t)offset) k_resource_trap();return b->data+(size_t)offset;
}
static int64_t k_file_read(int64_t id,int64_t buffer,int64_t offset,int64_t count) {
    KFile *f=k_file_require(id);unsigned char *data=k_file_range(buffer,offset,count);if(f->mode) return -5;if(!count) return 0;
#if defined(_WIN32)
    DWORD bytes=0;if(!ReadFile(f->native,data,(DWORD)count,&bytes,NULL)) return k_file_error();return (int64_t)bytes;
#else
    ssize_t bytes;do {bytes=read(f->native,data,(size_t)count);} while(bytes<0 && errno==EINTR);return bytes<0?k_file_error():(int64_t)bytes;
#endif
}
static int64_t k_file_write(int64_t id,int64_t buffer,int64_t offset,int64_t count) {
    KFile *f=k_file_require(id);unsigned char *data=k_file_range(buffer,offset,count);if(!f->mode) return -5;if(!count) return 0;
#if defined(_WIN32)
    DWORD bytes=0;if(!WriteFile(f->native,data,(DWORD)count,&bytes,NULL)) return k_file_error();return (int64_t)bytes;
#else
    ssize_t bytes;do {bytes=write(f->native,data,(size_t)count);} while(bytes<0 && errno==EINTR);return bytes<0?k_file_error():(int64_t)bytes;
#endif
}
static int64_t k_file_flush(int64_t id) {
    KFile *f=k_file_require(id);if(!f->mode) return -5;
#if defined(_WIN32)
    return FlushFileBuffers(f->native)?0:k_file_error();
#else
    int result;do {result=fsync(f->native);} while(result<0 && errno==EINTR);return result<0?k_file_error():0;
#endif
}
static bool k_file_replace_name(KString name) {
    size_t scalars=0;
    return name.bytes && name.bytes<=255 && !memchr(name.data,0,name.bytes) && !memchr(name.data,'/',name.bytes) && k_utf8_scan(name.data,name.bytes,&scalars) && !(name.bytes==1 && name.data[0]=='.') && !(name.bytes==2 && name.data[0]=='.' && name.data[1]=='.');
}
#if defined(__linux__) && !defined(K_REPLACE_UNSUPPORTED)
static int64_t k_file_replace_abort(int directory,int file,int64_t error) {
    if(file>=0) (void)close(file);
    (void)close(directory);
    return error;
}
#endif
static int64_t k_file_replace(KString directory,KString temporary,KString target) {
    size_t scalars=0;
    if(!directory.bytes || directory.bytes>4095 || memchr(directory.data,0,directory.bytes) || !k_utf8_scan(directory.data,directory.bytes,&scalars) || !k_file_replace_name(temporary) || !k_file_replace_name(target)) return -5;
    if(temporary.bytes==target.bytes && !memcmp(temporary.data,target.data,target.bytes)) return -5;
#if defined(__linux__) && !defined(K_REPLACE_UNSUPPORTED)
    char parent[4096],source[256],destination[256];
    memcpy(parent,directory.data,directory.bytes);parent[directory.bytes]=0;
    memcpy(source,temporary.data,temporary.bytes);source[temporary.bytes]=0;
    memcpy(destination,target.data,target.bytes);destination[target.bytes]=0;
    int dir;do {dir=open(parent,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);} while(dir<0 && errno==EINTR);
    if(dir<0) return k_file_error();
    int file;do {file=openat(dir,source,O_RDONLY|O_NONBLOCK|O_CLOEXEC|O_NOFOLLOW);} while(file<0 && errno==EINTR);
    if(file<0) return k_file_replace_abort(dir,-1,k_file_error());
    struct stat from,to;
    if(fstat(file,&from)) return k_file_replace_abort(dir,file,k_file_error());
    if(!S_ISREG(from.st_mode)) return k_file_replace_abort(dir,file,-6);
    if(fstatat(dir,destination,&to,AT_SYMLINK_NOFOLLOW)==0) {
        if(!S_ISREG(to.st_mode)) return k_file_replace_abort(dir,file,-6);
        if(from.st_dev==to.st_dev && from.st_ino==to.st_ino) return k_file_replace_abort(dir,file,-5);
    } else if(errno!=ENOENT) return k_file_replace_abort(dir,file,k_file_error());
    int result;do {result=fsync(file);} while(result<0 && errno==EINTR);
    if(result<0) return k_file_replace_abort(dir,file,k_file_error());
    if(close(file)<0) return k_file_replace_abort(dir,-1,k_file_error());
    if(renameat(dir,source,dir,destination)<0) return k_file_replace_abort(dir,-1,k_file_error());
    /* Once rename succeeds, negative pre-commit errors would conceal publication. */
    do {result=fsync(dir);} while(result<0 && errno==EINTR);
    int64_t status=result<0?1:0;
    if(close(dir)<0) status=1;
    return status;
#else
    return -6;
#endif
}
