#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>
static char dir[4096];
static void location(char *out,const char *name){snprintf(out,8192,"%s/%s",dir,name);}
static void record_pid(void){char path[8192];location(path,"pids");int fd=open(path,O_WRONLY|O_APPEND|O_CREAT,0600);dprintf(fd,"%ld\n",(long)getpid());close(fd);}
static void copy(const char *source,const char *out){FILE *a=fopen(source,"rb"),*b=fopen(out,"wb");if(!a||!b)exit(18);char data[8192];size_t n;while((n=fread(data,1,sizeof data,a)))if(fwrite(data,1,n,b)!=n)exit(19);fclose(a);fclose(b);}
int main(int argc,char **argv){
 char exe[4096];ssize_t n=readlink("/proc/self/exe",exe,sizeof(exe)-1);if(n<0)return 16;exe[n]=0;*strrchr(exe,'/')=0;snprintf(dir,sizeof dir,"%s",exe);
 char path[8192],mode[128]={0};location(path,"mode");FILE *f=fopen(path,"r");if(!f)return 17;fgets(mode,sizeof mode,f);fclose(f);
 const char *out=NULL;for(int i=1;i+1<argc;i++)if(!strcmp(argv[i],"-o"))out=argv[i+1];if(!out)return 20;
 if(!strcmp(mode,"hang")||!strcmp(mode,"exit-tree")){
  signal(SIGINT,SIG_IGN);signal(SIGTERM,SIG_IGN);signal(SIGHUP,SIG_IGN);signal(SIGQUIT,SIG_IGN);record_pid();
  if(fork()==0){record_pid();if(fork()==0)record_pid();for(;;)pause();}
  if(!strcmp(mode,"exit-tree")){
   location(path,"pids");for(int i=0;i<1000;i++){int count=0,c;f=fopen(path,"r");while((c=fgetc(f))!=EOF)if(c=='\n')count++;fclose(f);if(count>=3)return 17;usleep(1000);}return 21;
  }
  for(;;)pause();
 }
 if(!strcmp(mode,"no-output"))return 0;
 if(!strcmp(mode,"symlink")){unlink(out);location(path,"image");return symlink(path,out)?22:0;}
 if(!strcmp(mode,"limits")){
  struct rlimit as,files,core,handles;getrlimit(RLIMIT_AS,&as);getrlimit(RLIMIT_FSIZE,&files);getrlimit(RLIMIT_CORE,&core);getrlimit(RLIMIT_NOFILE,&handles);
  void *p=mmap(NULL,(size_t)768*1024*1024,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);int limited=p==MAP_FAILED&&errno==ENOMEM;if(p!=MAP_FAILED)munmap(p,(size_t)768*1024*1024);
  int closed=fcntl(200,F_GETFD)==-1&&errno==EBADF;
  location(path,"limits.json");f=fopen(path,"w");fprintf(f,"{\"as\":%llu,\"file\":%llu,\"core\":%llu,\"fd_hard\":%llu,\"memory_enforced\":%d,\"fd_closed\":%d}",(unsigned long long)as.rlim_cur,(unsigned long long)files.rlim_cur,(unsigned long long)core.rlim_cur,(unsigned long long)handles.rlim_max,limited,closed);fclose(f);
 }
 location(path,"image");copy(path,out);return 0;
}
