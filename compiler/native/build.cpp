#include "build.h"
#include <iostream>
#if defined(__linux__) && defined(__x86_64__)
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cerrno>
#include <csignal>
#include <fcntl.h>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <vector>
#include <sched.h>
#include <sys/auxv.h>
#include <sys/stat.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
namespace {
namespace fs=std::filesystem;
struct Temporary {
    fs::path path;
    explicit Temporary(const fs::path &base) {
        std::string name=(base/"Awl-XXXXXX").string();
        std::vector<char> bytes(name.begin(),name.end());bytes.push_back(0);
        const auto p=mkdtemp(bytes.data());if(!p) throw std::runtime_error("cannot create private temporary directory");path=p;
    }
    ~Temporary() {std::error_code ec;fs::remove_all(path,ec);}
};
struct Staging {
    fs::path path;
    explicit Staging(const fs::path &parent) {
        std::string name=(parent/".Awl-output-XXXXXX").string();std::vector<char> bytes(name.begin(),name.end());bytes.push_back(0);
        const int fd=mkstemp(bytes.data());if(fd<0) throw std::runtime_error("cannot stage output in destination directory");
        close(fd);path=bytes.data();
    }
    ~Staging() {std::error_code ec;if(!path.empty()) fs::remove(path,ec);}
};
fs::path self(const char *argv0) {
    std::vector<char> bytes(65536);const auto count=readlink("/proc/self/exe",bytes.data(),bytes.size());
    if(count>0&&static_cast<size_t>(count)<bytes.size()) return fs::canonical(std::string(bytes.data(),count));
    const auto execfn=reinterpret_cast<const char*>(getauxval(AT_EXECFN));
    if(execfn&&std::strchr(execfn,'/')) return fs::canonical(execfn);
    if(argv0&&std::strchr(argv0,'/')) return fs::canonical(argv0);
    throw std::runtime_error("cannot locate Awl installation; invoke kcc with its path");
}
volatile sig_atomic_t requested_signal=0;
constexpr int managed_signals[]={SIGINT,SIGTERM,SIGHUP,SIGQUIT,SIGCHLD};
void notice(int signal) {if(signal!=SIGCHLD&&!requested_signal) requested_signal=signal;}
struct SignalScope {
    struct sigaction saved[5]{};sigset_t mask{};int original_subreaper=0;
    SignalScope() {
        requested_signal=0;struct sigaction action{};action.sa_handler=notice;sigemptyset(&action.sa_mask);
        int count=0;
        for(auto signal:managed_signals) {
            if(sigaction(signal,&action,&saved[count])!=0) {
                while(count) {--count;sigaction(managed_signals[count],&saved[count],nullptr);}
                throw std::runtime_error("cannot install process supervision handlers");
            }
            ++count;
        }
        sigset_t set;sigemptyset(&set);for(auto signal:managed_signals) sigaddset(&set,signal);
        if(sigprocmask(SIG_UNBLOCK,&set,&mask)!=0) {
            for(int i=0;i<5;++i) sigaction(managed_signals[i],&saved[i],nullptr);
            throw std::runtime_error("cannot configure supervision signal mask");
        }
        if(prctl(PR_GET_CHILD_SUBREAPER,&original_subreaper)!=0||prctl(PR_SET_CHILD_SUBREAPER,1)!=0) {
            for(int i=0;i<5;++i) sigaction(managed_signals[i],&saved[i],nullptr);
            sigprocmask(SIG_SETMASK,&mask,nullptr);
            throw std::runtime_error("cannot supervise backend descendants");
        }
    }
    ~SignalScope() {
        prctl(PR_SET_CHILD_SUBREAPER,original_subreaper);
        for(int i=0;i<5;++i) sigaction(managed_signals[i],&saved[i],nullptr);
        sigprocmask(SIG_SETMASK,&mask,nullptr);
    }
};
struct WaitMask {
    sigset_t set{},saved{};
    WaitMask() {
        sigemptyset(&set);for(auto signal:managed_signals) sigaddset(&set,signal);
        if(sigprocmask(SIG_BLOCK,&set,&saved)!=0) throw std::runtime_error("cannot configure child wait mask");
    }
    ~WaitMask() {sigprocmask(SIG_SETMASK,&saved,nullptr);}
};
template<class R> bool tighten(R resource,rlim_t requested) {
    rlimit old{};if(getrlimit(resource,&old)!=0) return false;
    const rlim_t effective=std::min(requested,std::min(old.rlim_cur,old.rlim_max));
    const rlimit limit{effective,effective};return setrlimit(resource,&limit)==0;
}
bool descriptor_limit() {
    rlimit old{};if(getrlimit(RLIMIT_NOFILE,&old)!=0) return false;
    const auto hard=std::min<rlim_t>(old.rlim_max,32768);
    // Zig legitimately raises a shell's usual 1024 soft limit while compiling
    // bundled libc. Bound its hard limit without pinning that low soft limit.
    const rlimit limit{std::min(old.rlim_cur,hard),hard};return setrlimit(RLIMIT_NOFILE,&limit)==0;
}
[[noreturn]] void child_failure() {
    const char text[]="kcc: cannot configure or execute child process\n";
    const auto ignored=write(STDERR_FILENO,text,sizeof(text)-1);(void)ignored;_exit(126);
}
void kill_group(pid_t pid,int signal) {
    kill(-pid,signal);kill(pid,signal);
}
bool reap_descendants(pid_t group) {
    // SIGKILL was sent while the root child still held its PID (WNOWAIT),
    // avoiding a kill-after-PID-reuse race. Do not send group signals here.
    const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(1);
    for(;;) {
        int status=0;const auto result=waitpid(-group,&status,WNOHANG);
        if(result>0) continue;
        if(result<0) {if(errno==EINTR) continue;return errno==ECHILD;}
        if(std::chrono::steady_clock::now()>=end) return false;
        timespec pause{0,1000000};nanosleep(&pause,nullptr);
    }
}
struct ProcessResult {int status=2;bool timed_out=false;bool cleanup_failed=false;int cancellation=0;};
ProcessResult execute(std::vector<std::string> args,const std::vector<std::string> *environment,
                      bool backend,unsigned wall_seconds,unsigned memory_mib) {
    if(requested_signal) return {128+requested_signal,false,false,requested_signal};
    std::vector<char*> av,ev;for(auto &s:args) av.push_back(s.data());av.push_back(nullptr);
    if(environment) {for(const auto &s:*environment) ev.push_back(const_cast<char*>(s.c_str()));ev.push_back(nullptr);}
    WaitMask mask;
    const auto parent=getpid();const auto pid=fork();if(pid<0) throw std::runtime_error("cannot fork build process");
    if(pid==0) {
        struct sigaction action{};action.sa_handler=SIG_DFL;sigemptyset(&action.sa_mask);
        for(auto signal:managed_signals) if(sigaction(signal,&action,nullptr)!=0) child_failure();
        sigset_t empty;sigemptyset(&empty);
        if(sigprocmask(SIG_SETMASK,&empty,nullptr)!=0||setpgid(0,0)!=0) child_failure();
        if(prctl(PR_SET_PDEATHSIG,SIGKILL)!=0||getppid()!=parent) child_failure();
        if(!tighten(RLIMIT_CORE,0)) child_failure();
        if(backend) {
            if(!tighten(RLIMIT_AS,static_cast<rlim_t>(memory_mib)*1024*1024)||
               !tighten(RLIMIT_FSIZE,static_cast<rlim_t>(256)*1024*1024)||!descriptor_limit()) child_failure();
            cpu_set_t allowed,selected;CPU_ZERO(&selected);
            if(sched_getaffinity(0,sizeof(allowed),&allowed)==0) {
                int used=0;for(int cpu=0;cpu<CPU_SETSIZE&&used<4;++cpu) if(CPU_ISSET(cpu,&allowed)) {CPU_SET(cpu,&selected);++used;}
                if(used) {const int ignored=sched_setaffinity(0,sizeof(selected),&selected);(void)ignored;}
            }
        }
        // Do not leak the source stream or caller-owned descriptors into tools.
        if(syscall(SYS_close_range,3u,~0u,0u)!=0) child_failure();
        if(environment) execve(av[0],av.data(),ev.data());else execv(av[0],av.data());
        child_failure();
    }
    // The child also sets its group, covering both sides of the fork race.
    const int ignored=setpgid(pid,pid);(void)ignored;
    const auto start=std::chrono::steady_clock::now();
    const auto deadline=start+std::chrono::seconds(wall_seconds);
    auto kill_at=start;bool terminating=false,killed=false;ProcessResult result;
    for(;;) {
        siginfo_t info{};
        if(waitid(P_PID,static_cast<id_t>(pid),&info,WEXITED|WNOHANG|WNOWAIT)!=0) {
            if(errno==EINTR) continue;
            kill_group(pid,SIGKILL);int status=0;while(waitpid(pid,&status,0)<0&&errno==EINTR) {}
            reap_descendants(pid);throw std::runtime_error("cannot inspect child process");
        }
        if(info.si_pid) {
            // The unreaped root reserves its PID until all group signals end.
            kill(-pid,SIGKILL);
            int status=0;while(waitpid(pid,&status,0)<0) if(errno!=EINTR) throw std::runtime_error("cannot reap child process");
            result.cleanup_failed=!reap_descendants(pid);
            result.status=result.cancellation?128+result.cancellation:result.timed_out?124:
                WIFEXITED(status)?WEXITSTATUS(status):WIFSIGNALED(status)?128+WTERMSIG(status):2;
            return result;
        }
        const auto now=std::chrono::steady_clock::now();
        if(!terminating&&(requested_signal||(wall_seconds&&now>=deadline))) {
            result.cancellation=requested_signal;result.timed_out=!result.cancellation;
            kill_group(pid,result.cancellation?result.cancellation:SIGTERM);
            kill_at=now+std::chrono::milliseconds(500);terminating=true;
        }
        if(terminating&&!killed&&now>=kill_at) {kill_group(pid,SIGKILL);killed=true;}
        auto until=now+std::chrono::seconds(1);
        if(!terminating&&wall_seconds) until=std::min(until,deadline);
        if(terminating&&!killed) until=std::min(until,kill_at);
        auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(until-now).count();if(ns<0) ns=0;
        timespec wait{static_cast<time_t>(ns/1000000000),static_cast<long>(ns%1000000000)};
        const auto signal=sigtimedwait(&mask.set,nullptr,&wait);
        if(signal>0&&signal!=SIGCHLD&&!requested_signal) requested_signal=signal;
    }
}
uint64_t little(const unsigned char *bytes,size_t count) {
    uint64_t value=0;for(size_t i=0;i<count;++i) value|=uint64_t(bytes[i])<<(8*i);return value;
}
struct FileDescriptor {
    int fd;
    explicit FileDescriptor(const fs::path &path):fd(open(path.c_str(),O_RDONLY|O_CLOEXEC|O_NOFOLLOW)) {
        if(fd<0) throw std::runtime_error("cannot inspect generated executable");
    }
    ~FileDescriptor() {close(fd);}
};
void inspect_output(const fs::path &path,mode_t mode) {
    FileDescriptor file(path);struct stat stat{};std::array<unsigned char,64> h{};
    auto invalid=[](){throw std::runtime_error("backend output is not a supported static x86-64 ELF executable");};
    if(fstat(file.fd,&stat)!=0||!S_ISREG(stat.st_mode)||stat.st_size<64||stat.st_size>256LL*1024*1024||pread(file.fd,h.data(),64,0)!=64) invalid();
    if(h[0]!=127||h[1]!='E'||h[2]!='L'||h[3]!='F'||h[4]!=2||h[5]!=1||h[6]!=1||little(h.data()+16,2)!=2||little(h.data()+18,2)!=62||little(h.data()+20,4)!=1||little(h.data()+52,2)!=64||little(h.data()+54,2)!=56) invalid();
    const auto size=static_cast<uint64_t>(stat.st_size),offset=little(h.data()+32,8),count=little(h.data()+56,2),entry=little(h.data()+24,8);
    if(!count||count>128||offset<64||offset>size||count*56>size-offset) invalid();
    bool executable_entry=false;
    for(uint64_t i=0;i<count;++i) {
        std::array<unsigned char,56> p{};if(pread(file.fd,p.data(),56,static_cast<off_t>(offset+i*56))!=56) invalid();
        const auto type=little(p.data(),4),flags=little(p.data()+4,4),file_offset=little(p.data()+8,8),address=little(p.data()+16,8),file_size=little(p.data()+32,8),memory_size=little(p.data()+40,8);
        if(type==2||type==3) invalid(); // No PT_DYNAMIC or PT_INTERP.
        if(type==1) {
            if(file_size>memory_size||file_offset>size||file_size>size-file_offset||memory_size>UINT64_MAX-address) invalid();
            if((flags&1)&&entry>=address&&entry-address<memory_size) executable_entry=true;
        }
    }
    if(!executable_entry) invalid();
    if(fchmod(file.fd,mode)!=0) throw std::runtime_error("cannot set generated executable permissions");
}
}
#endif
#if defined(_WIN32) && (defined(__x86_64__) || defined(_M_X64))
#include "build_windows.inc"
#endif
namespace Awl_driver {
int build(const char *c_source,size_t length,const char *argv0,const std::string &source_path,const std::string &output,const Options &options,bool run) {
#if defined(__linux__) && defined(__x86_64__)
    try {
        SignalScope supervision;
        const auto root=self(argv0).parent_path().parent_path();const auto zig=root/"libexec/zig/zig",lib=root/"libexec/zig/lib";
        if(!fs::is_regular_file(zig)||!fs::is_directory(lib)) throw std::runtime_error("bundled toolchain missing; use the complete Awl Linux bundle (no system-tool fallback)");
        const char *tmpenv=std::getenv("TMPDIR");const fs::path tmpbase=tmpenv&&*tmpenv?fs::absolute(tmpenv):fs::path("/tmp");Temporary temp(tmpbase);
        fs::path cache;
        const char *xdg=std::getenv("XDG_CACHE_HOME"),*home=std::getenv("HOME");
        if(xdg&&*xdg) cache=fs::absolute(xdg)/"Awl/zig-0.15.2";
        else if(home&&*home) cache=fs::absolute(home)/".cache/Awl/zig-0.15.2";
        else cache=temp.path/"global-cache";
        fs::create_directories(cache);
        const auto cfile=temp.path/"program.c";
        {std::ofstream file(cfile,std::ios::binary);file.write(c_source,static_cast<std::streamsize>(length));file.close();if(!file) throw std::runtime_error("cannot write generated C");}
        fs::path destination;
        if(run) destination=temp.path/"program";
        else destination=fs::absolute(output.empty()?fs::path(source_path).stem():fs::path(output));
        const auto source=fs::canonical(source_path);
        if(fs::weakly_canonical(destination)==source||(fs::exists(destination)&&fs::equivalent(destination,source))) throw std::runtime_error("refusing to overwrite source with executable");
        for(const auto &path:options.protected_sources) {
            const auto imported=fs::canonical(path);
            if(fs::weakly_canonical(destination)==imported||(fs::exists(destination)&&fs::equivalent(destination,imported))) throw std::runtime_error("refusing to overwrite source with executable");
        }
        Staging staging(destination.parent_path());
        const std::vector<std::string> environment={"PATH=/no-host-tools","LC_ALL=C","HOME="+temp.path.string(),"TMPDIR="+temp.path.string(),
            "ZIG_LIB_DIR="+lib.string(),"ZIG_GLOBAL_CACHE_DIR="+cache.string(),"ZIG_LOCAL_CACHE_DIR="+(temp.path/"local-cache").string()};
        const auto status=execute({zig.string(),"cc","-std=c11","-target","x86_64-linux-musl","-mcpu=baseline","-static","-O"+std::to_string(options.optimization),"-g0","-s",cfile.string(),"-o",staging.path.string()},&environment,true,options.build_timeout_seconds,options.build_memory_mib);
        if(status.cancellation) {std::cerr<<"kcc: build interrupted\n";return 128+status.cancellation;}
        if(status.timed_out) {std::cerr<<"kcc: backend wall-time limit exceeded\n";return 124;}
        if(status.cleanup_failed) throw std::runtime_error("cannot reap backend descendants");
        if(status.status) {std::cerr<<"kcc: bundled code generation/linking failed ("<<status.status<<")\n";return 2;}
        const auto mask=umask(0);umask(mask);
        inspect_output(staging.path,run?0700:static_cast<mode_t>(0777&~mask));
        if(requested_signal) {std::cerr<<"kcc: build interrupted before publication\n";return 128+requested_signal;}
        fs::rename(staging.path,destination);staging.path.clear();
        if(run) {
            const auto program=execute({destination.string()},nullptr,false,options.run_timeout_seconds,0);
            if(program.cancellation) std::cerr<<"kcc: run interrupted\n";
            else if(program.timed_out) std::cerr<<"kcc: program wall-time limit exceeded\n";
            else if(program.cleanup_failed) throw std::runtime_error("cannot reap program descendants");
            return program.status;
        }
        std::cout<<destination.string()<<'\n';std::cout.flush();return std::cout?0:2;
    } catch(const std::exception &e) {std::cerr<<"kcc: "<<e.what()<<'\n';return 2;}
#elif defined(_WIN32) && (defined(__x86_64__) || defined(_M_X64))
    (void)argv0;return Awl_windows::build(c_source,length,source_path,output,options,run);
#else
    (void)c_source;(void)length;(void)argv0;(void)source_path;(void)output;(void)options;(void)run;
    std::cerr<<"kcc: bundled build/run not implemented for this host; preview supports Linux/Windows x86-64 only\n";return 2;
#endif
}
}
