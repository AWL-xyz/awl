#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
ssize_t __real_write(int,const void *,size_t);
ssize_t __real_read(int,void *,size_t);
int __real_fsync(int);
int __real_close(int);
static int regular(int fd) {struct stat s;return fstat(fd,&s)==0 && S_ISREG(s.st_mode);}
static int mode(const char *name) {const char *m=getenv("KV_FAULT");return m && strcmp(m,name)==0;}
ssize_t __wrap_write(int fd,const void *data,size_t n) {
 static unsigned calls;
 if(regular(fd)) {
  if(mode("zero")) return 0;
  if(mode("partial")) {if(calls++) {errno=ENOSPC;return -1;} if(n>3)n=3;}
  if(mode("short")) {if(!calls++) {errno=EINTR;return -1;} if(n>3)n=3;}
 }
 return __real_write(fd,data,n);
}
ssize_t __wrap_read(int fd,void *data,size_t n) {
 static unsigned calls;
 if(regular(fd) && mode("short")) {if(!calls++) {errno=EINTR;return -1;} if(n>2)n=2;}
 return __real_read(fd,data,n);
}
int __wrap_fsync(int fd) {
 static unsigned calls;
 if(mode("fsync")) {errno=EIO;return -1;}
 if(mode("short") && !calls++) {errno=EINTR;return -1;}
 return __real_fsync(fd);
}
int __wrap_close(int fd) {
 int writable=regular(fd) && (fcntl(fd,F_GETFL)&O_ACCMODE)!=O_RDONLY;
 int result=__real_close(fd);
 if(writable && mode("close")) {errno=EIO;return -1;}
 return result;
}
