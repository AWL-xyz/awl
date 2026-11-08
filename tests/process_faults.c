#define _GNU_SOURCE 1
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <inttypes.h>
#include <limits.h>
#include <string.h>
#ifdef NDEBUG
#error process fault oracle requires active assertions
#endif
#include <assert.h>
#include <spawn.h>
#include <sys/wait.h>
#include <poll.h>
#include <fcntl.h>
#include <dirent.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <errno.h>
#include "kstrings.c"
#include "kbuilders.c"
#include "kgeneric.c"
static unsigned kind,nth,seen;
static int live;
static bool hit(unsigned k){return kind==k&&++seen==nth;}
static void *allocate(size_t n){void *p=hit(1)?NULL:malloc(n);if(p)++live;return p;}
static void release(void *p){if(p)--live;free(p);}
static int makepipe(int p[2]){if(hit(2)){errno=EMFILE;return -1;}return pipe(p);}
static int control(int fd,int op,int value){if(hit(3)){errno=EMFILE;return -1;}return fcntl(fd,op,value);}
static int actions_init(posix_spawn_file_actions_t *a){return hit(4)?ENOMEM:posix_spawn_file_actions_init(a);}
static int attr_init(posix_spawnattr_t *a){return hit(5)?ENOMEM:posix_spawnattr_init(a);}
static int spawn(pid_t *p,const char *s,const posix_spawn_file_actions_t *a,const posix_spawnattr_t *t,char *const v[],char *const e[]){return hit(6)?ENOMEM:posix_spawn(p,s,a,t,v,e);}
static int watch(struct pollfd *p,nfds_t n,int timeout){if(hit(7)||hit(10)){errno=kind==10?EINTR:EIO;return -1;}return poll(p,n,timeout);}
static ssize_t consume(int fd,void *p,size_t n){if(hit(8)){errno=EIO;return -1;}return read(fd,p,n);}
static int clock_now(clockid_t c,struct timespec *p){if(hit(9)){errno=EIO;return -1;}return clock_gettime(c,p);}
static int observe(idtype_t t,id_t p,siginfo_t *i,int flags){if(hit(11)){errno=EINTR;return -1;}return waitid(t,p,i,flags);}
static DIR *directory(const char *p){if(hit(12)){errno=EMFILE;return NULL;}return opendir(p);}
#define malloc allocate
#define free release
#define pipe makepipe
#define fcntl control
#define posix_spawn_file_actions_init actions_init
#define posix_spawnattr_init attr_init
#define posix_spawn spawn
#define poll watch
#define read consume
#define clock_gettime clock_now
#define waitid observe
#define opendir directory
#include "kprocess.c"
#undef opendir
static unsigned fds(void){unsigned n=0;DIR *d=opendir("/proc/self/fd");assert(d);while(readdir(d))++n;closedir(d);return n;}
int main(int argc,char **argv){(void)argv;if(argc>1){close(0);close(1);close(2);}KGenericVector v=k_generic_new(11,sizeof(KString),0);KGenericView args=k_generic_view(v,11,0,0);KSpool out=k_spool_new(64),err=k_spool_new(64);KString program={(const unsigned char *)"/bin/echo",9,9};unsigned baseline=fds(),cases=0;
 for(unsigned k=1;k<=12;++k){unsigned total=k==1?3:k==2?2:k==3?6:k==9?2:1;for(unsigned n=1;n<=total;++n){kind=0;k_spool_clear(out);k_spool_clear(err);k_spool_codepoint(out,'P');k_spool_codepoint(err,'P');kind=k;nth=n;seen=0;int64_t r=k_process_capture(program,args,out,err,1000);kind=0;int64_t want=k==10||k==11?0:k==7||k==8||(k==9&&n==2)?-7:-3;assert(r==want);assert(k_spool_bytes(out)==(want==0?2:1)&&k_spool_bytes(err)==1);assert(fds()==baseline&&live==0);++cases;}}
 signal(SIGCHLD,SIG_IGN);assert(k_process_capture(program,args,out,err,1000)==-1);signal(SIGCHLD,SIG_DFL);++cases;
 assert(k_process_capture(program,args,out,out,1000)==-1);++cases;
 KString zero={(const unsigned char *)"\0",1,1};assert(k_generic_push(v,11,&zero));args=k_generic_view(v,11,0,1);assert(k_process_capture(program,args,out,err,1000)==-1);++cases;
 k_generic_clear(v,11);args=k_generic_view(v,11,0,0);for(unsigned repeat=0;repeat<200;++repeat){k_spool_clear(out);k_spool_clear(err);assert(k_process_capture(program,args,out,err,1000)==0);assert(k_spool_bytes(out)==1&&k_spool_bytes(err)==0&&live==0&&fds()==baseline);}
 assert(waitpid(-1,NULL,WNOHANG)==-1&&errno==ECHILD);assert(fds()==baseline);k_generic_free(v,11);k_spool_free(out);k_spool_free(err);printf("PASS %u process fault/rollback/fd/reaping cases\n",cases);puts("PASS 200 repeated captures, no temporary allocations/fds/zombies retained");return 0;}
