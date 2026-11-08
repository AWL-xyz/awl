#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
int main(int argc,char **argv){
 if(argc<2)return 2;
 if(!strcmp(argv[1],"args")){for(int i=2;i<argc;++i)printf("%s\n",argv[i]);return 0;}
 if(!strcmp(argv[1],"exit")){fputs("output",stdout);fputs("diagnostic",stderr);return 7;}
 if(!strcmp(argv[1],"signal")){raise(SIGTERM);return 2;}
 if(!strcmp(argv[1],"bad")){fputs("valid",stdout);fputc(255,stderr);return 0;}
 if(!strcmp(argv[1],"nul")){fwrite("A\0B",1,3,stdout);return 0;}
 if(!strcmp(argv[1],"both")){char data[512];memset(data,'x',sizeof(data));for(int i=0;i<512;++i){if(fwrite(data,1,sizeof(data),stdout)!=sizeof(data)||fwrite(data,1,sizeof(data),stderr)!=sizeof(data))return 3;}return 0;}
 if(!strcmp(argv[1],"burst")){for(int i=0;i<8193;++i)fputc('x',stdout);return 0;}
 if(!strcmp(argv[1],"stdin")){return getchar()==EOF?0:4;}
 if(!strcmp(argv[1],"write")){FILE *f=fopen(argv[2],"w");if(!f)return 3;fputs("ran",f);return fclose(f)?3:0;}
 if(!strcmp(argv[1],"fds")){DIR *d=opendir("/proc/self/fd");if(!d)return 3;struct dirent *e;while((e=readdir(d))) {int n=atoi(e->d_name);if(n>2&&n!=dirfd(d)){closedir(d);return 4;}}closedir(d);return 0;}
 if(!strcmp(argv[1],"group")){pid_t pid=fork();if(pid<0)return 3;if(pid>0){FILE *f=fopen(argv[2],"w");if(!f)return 3;fprintf(f,"%ld %ld",(long)getpid(),(long)pid);fclose(f);}for(;;)pause();}
 if(!strcmp(argv[1],"leavegroup")){if(setpgid(0,getpgid(getppid())))return 5;for(;;)pause();}
 if(!strcmp(argv[1],"sleep")){struct timespec t={2,0};nanosleep(&t,NULL);return 0;}
 return 2;
}
