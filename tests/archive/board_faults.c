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
int __real_renameat(int,const char *,int,const char *);
static int mode(const char *s){const char *m=getenv("BOARD_FAULT");return m&&!strcmp(m,s);}
static int kind(int fd){struct stat s;if(fstat(fd,&s))return 0;return S_ISREG(s.st_mode)?1:S_ISDIR(s.st_mode)?2:0;}
ssize_t __wrap_write(int fd,const void *p,size_t n){static unsigned calls;if(kind(fd)==1){if(mode("zero"))return 0;if(mode("partial")){if(calls++){errno=ENOSPC;return -1;}if(n>3)n=3;}if(mode("short")){if(!calls++){errno=EINTR;return -1;}if(n>3)n=3;}}return __real_write(fd,p,n);}
ssize_t __wrap_read(int fd,void *p,size_t n){static unsigned calls;if(kind(fd)==1&&mode("short")){if(!calls++){errno=EINTR;return -1;}if(n>2)n=2;}return __real_read(fd,p,n);}
int __wrap_fsync(int fd){static unsigned interrupted[3];int k=kind(fd);if((mode("file-sync")&&k==1)||(mode("dir-sync")&&k==2)){errno=EIO;return -1;}if(mode("short")&&k&&!interrupted[k]++){errno=EINTR;return -1;}return __real_fsync(fd);}
int __wrap_close(int fd){int k=kind(fd),writable=k==1&&(fcntl(fd,F_GETFL)&O_ACCMODE)!=O_RDONLY;int r=__real_close(fd);if((mode("file-close")&&writable)||(mode("dir-close")&&k==2)){errno=EIO;return -1;}return r;}
int __wrap_renameat(int a,const char *x,int b,const char *y){if(mode("rename")){errno=EACCES;return -1;}return __real_renameat(a,x,b,y);}
