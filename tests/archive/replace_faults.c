#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
int __real_fsync(int);
int __real_close(int);
int __real_renameat(int,const char *,int,const char *);
static int mode(const char *s) {const char *value=getenv("REPLACE_FAULT");return value && !strcmp(value,s);}
static int kind(int fd) {struct stat s;if(fstat(fd,&s))return 0;return S_ISDIR(s.st_mode)?2:S_ISREG(s.st_mode)?1:0;}
int __wrap_fsync(int fd) {
 static unsigned interrupted[3];int k=kind(fd);
 if((mode("file-sync") && k==1) || (mode("dir-sync") && k==2)) {errno=EIO;return -1;}
 if(mode("eintr") && k && !interrupted[k]++) {errno=EINTR;return -1;}
 return __real_fsync(fd);
}
int __wrap_close(int fd) {
 int k=kind(fd),r=__real_close(fd);
 if((mode("file-close") && k==1) || (mode("dir-close") && k==2)) {errno=EIO;return -1;}
 return r;
}
int __wrap_renameat(int a,const char *x,int b,const char *y) {
 if(mode("rename")) {errno=EACCES;return -1;}
 return __real_renameat(a,x,b,y);
}
