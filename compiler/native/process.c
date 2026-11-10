/* Single-threaded trusted-command supervision, not a sandbox or async task API. */
#if defined(__linux__) && !defined(__wasi__)
#include <spawn.h>
#include <sys/wait.h>
#include <sys/syscall.h>
#include <poll.h>
#include <fcntl.h>
#include <dirent.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <errno.h>
extern char **environ;
static int64_t k_process_now(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||(uint64_t)t.tv_sec>(uint64_t)INT64_MAX/1000-600001) return -1;
    return (int64_t)t.tv_sec*1000+t.tv_nsec/1000000;
}
static bool k_process_pipe(int p[2]) {
    if(pipe(p)) return false;
    for(unsigned i=0;i<2;++i) {
        if(p[i]<3) {int n=fcntl(p[i],F_DUPFD_CLOEXEC,3);close(p[i]);p[i]=n;}
        if(p[i]<0||fcntl(p[i],F_SETFD,FD_CLOEXEC)<0) {if(p[0]>=0)close(p[0]);if(p[1]>=0)close(p[1]);p[0]=p[1]=-1;return false;}
    }
    if(fcntl(p[0],F_SETFL,O_NONBLOCK)<0) {close(p[0]);close(p[1]);p[0]=p[1]=-1;return false;}return true;
}
static bool k_process_descriptors(posix_spawn_file_actions_t *actions) {
    DIR *d=opendir("/proc/self/fd");if(!d)return false;
    bool ok=true;unsigned count=0;struct dirent *entry;errno=0;
    while((entry=readdir(d))) {
        char *end=NULL;unsigned long fd=strtoul(entry->d_name,&end,10);
        if(*entry->d_name&&end&&!*end&&fd>=3&&fd<=INT_MAX&&(int)fd!=dirfd(d)) {
            if(++count>4096||posix_spawn_file_actions_addclose(actions,(int)fd)) {ok=false;break;}
        }
        errno=0;
    }
    if(errno)ok=false;
    if(closedir(d))ok=false;
    return ok;
}
#endif
static int64_t k_process_capture(KString program,KGenericView arguments,KSpool output,KSpool errors,int64_t timeout) {
    KGenericSlot *args=k_view_require(arguments,11);KBuilderSlot *builders[2]={k_builder_require(output),k_builder_require(errors)};
    if(args->width!=sizeof(KString)||output.id==errors.id||timeout<1||timeout>600000||program.bytes==0||program.bytes>4096||memchr(program.data,0,(size_t)program.bytes)||arguments.length>128) return -1;
#if defined(__linux__) && !defined(__wasi__)
    struct sigaction disposition;if(sigaction(SIGCHLD,NULL,&disposition)||disposition.sa_handler!=SIG_DFL||(disposition.sa_flags&SA_NOCLDWAIT))return -1;
    char *argv[130];size_t used=(size_t)program.bytes+1;
    for(size_t i=0;i<(size_t)arguments.length;++i) {KString s;memcpy(&s,args->data+((size_t)arguments.start+i)*sizeof(s),sizeof(s));if(s.bytes>4096||memchr(s.data,0,(size_t)s.bytes)||s.bytes+1>65536-used)return -1;used+=(size_t)s.bytes+1;}
    char *arena=malloc(used);if(!arena)return -3;memcpy(arena,program.data,(size_t)program.bytes);arena[program.bytes]=0;argv[0]=arena;used=(size_t)program.bytes+1;
    for(size_t i=0;i<(size_t)arguments.length;++i) {KString s;memcpy(&s,args->data+((size_t)arguments.start+i)*sizeof(s),sizeof(s));argv[i+1]=arena+used;memcpy(argv[i+1],s.data,(size_t)s.bytes);argv[i+1][s.bytes]=0;used+=(size_t)s.bytes+1;}argv[arguments.length+1]=NULL;
    size_t capacities[2],lengths[2]={0,0};unsigned char *data[2]={NULL,NULL};int pipes[2][2]={{-1,-1},{-1,-1}};int64_t result=-3;int pidfd=-1;pid_t child=-1;bool actions_ready=false,attr_ready=false;posix_spawn_file_actions_t actions;posix_spawnattr_t attr;
    int64_t begin=k_process_now();if(begin<0)goto cleanup;
    for(unsigned i=0;i<2;++i) {capacities[i]=builders[i]->capacity-builders[i]->bytes;data[i]=malloc(capacities[i]+1);if(!data[i]||!k_process_pipe(pipes[i]))goto cleanup;}
    if(posix_spawn_file_actions_init(&actions))goto cleanup;
    actions_ready=true;
    if(posix_spawnattr_init(&attr))goto cleanup;
    attr_ready=true;
    sigset_t empty,defaults;sigemptyset(&empty);sigfillset(&defaults);
    if(posix_spawnattr_setflags(&attr,POSIX_SPAWN_SETPGROUP|POSIX_SPAWN_SETSIGMASK|POSIX_SPAWN_SETSIGDEF)||posix_spawnattr_setpgroup(&attr,0)||posix_spawnattr_setsigmask(&attr,&empty)||posix_spawnattr_setsigdefault(&attr,&defaults))goto cleanup;
    if(posix_spawn_file_actions_addopen(&actions,0,"/dev/null",O_RDONLY,0)||posix_spawn_file_actions_adddup2(&actions,pipes[0][1],1)||posix_spawn_file_actions_adddup2(&actions,pipes[1][1],2)||!k_process_descriptors(&actions))goto cleanup;
    int spawned=posix_spawn(&child,arena,&actions,&attr,argv,environ);if(spawned) {child=-1;result=spawned==ENOENT?-2:-3;goto cleanup;}
#if defined(SYS_pidfd_open) && !defined(Awl_PROCESS_NO_PIDFD)
    pidfd=(int)syscall(SYS_pidfd_open,child,0);
#endif
    close(pipes[0][1]);pipes[0][1]=-1;close(pipes[1][1]);pipes[1][1]=-1;
    for(;;) {
        int64_t now=k_process_now();if(now<0){result=-7;break;}if(now-begin>=timeout){result=-4;break;}
        /* WNOWAIT retains the leader identity until group cleanup, avoiding PID reuse. */
        siginfo_t info={0};if(waitid(P_PID,(id_t)child,&info,WEXITED|WNOHANG|WNOWAIT)<0) {if(errno==EINTR)continue;if(errno==ECHILD)child=-1;result=-7;break;}
        if(info.si_pid&&pipes[0][0]<0&&pipes[1][0]<0) {result=0;break;}
        struct pollfd fds[3]={{pipes[0][0],POLLIN,0},{pipes[1][0],POLLIN,0},{info.si_pid?-1:pidfd,POLLIN,0}};int remaining=(int)(timeout-(now-begin));int ready=poll(fds,3,pidfd>=0?remaining:(remaining<10?remaining:10));
        if(ready<0){if(errno==EINTR)continue;result=-7;break;}
        if(fds[2].revents&POLLNVAL){result=-7;break;}
        bool failed=false;
        for(unsigned i=0;i<2;++i) if(fds[i].revents) {
            size_t room=capacities[i]+1-lengths[i];size_t take=room<8192?room:8192;
            ssize_t n=read(pipes[i][0],data[i]+lengths[i],take);
            if(n>0){lengths[i]+=(size_t)n;if(lengths[i]>capacities[i]){result=-5;failed=true;break;}}
            else if(n==0){close(pipes[i][0]);pipes[i][0]=-1;}
            else if(errno!=EAGAIN&&errno!=EWOULDBLOCK&&errno!=EINTR){result=-7;failed=true;break;}
        }
        if(failed)break;
    }
cleanup:
    if(child>0) {
        kill(-child,SIGKILL);kill(child,SIGKILL);int status=0;pid_t waited;do{waited=waitpid(child,&status,0);}while(waited<0&&errno==EINTR);
        if(result==0)result=waited==child?(WIFEXITED(status)?WEXITSTATUS(status):WIFSIGNALED(status)?-1000-WTERMSIG(status):-7):-7;
    }
    if(pidfd>=0)close(pidfd);
    if(actions_ready)posix_spawn_file_actions_destroy(&actions);
    if(attr_ready)posix_spawnattr_destroy(&attr);
    if(result>=0||result<=-1001) {
        size_t scalars[2];if(!k_utf8_scan(data[0],lengths[0],&scalars[0])||!k_utf8_scan(data[1],lengths[1],&scalars[1]))result=-6;
        else for(unsigned i=0;i<2;++i){if(lengths[i])memcpy(builders[i]->data+builders[i]->bytes,data[i],lengths[i]);builders[i]->bytes+=lengths[i];builders[i]->scalars+=scalars[i];}
    }
    for(unsigned i=0;i<2;++i){if(pipes[i][0]>=0)close(pipes[i][0]);if(pipes[i][1]>=0)close(pipes[i][1]);free(data[i]);}free(arena);return result;
#else
    (void)builders;return -8;
#endif
}
