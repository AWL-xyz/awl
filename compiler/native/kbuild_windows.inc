// Windows x86-64 host driver. Included only on Windows; no shell/tool PATH fallback.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <sddl.h>
#include <bcrypt.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <vector>
namespace Awl_windows {
namespace fs=std::filesystem;
struct Handle {
    HANDLE h=INVALID_HANDLE_VALUE;
    Handle()=default;explicit Handle(HANDLE p):h(p) {}
    Handle(const Handle&)=delete;Handle& operator=(const Handle&)=delete;
    ~Handle(){if(h&&h!=INVALID_HANDLE_VALUE) CloseHandle(h);}
    bool valid() const{return h&&h!=INVALID_HANDLE_VALUE;}
};
[[noreturn]] void fail(const char *s){throw std::runtime_error(std::string(s)+" (Windows error "+std::to_string(GetLastError())+")");}
std::wstring wide(const std::string &s) {
    if(s.empty()) return {};
    int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),static_cast<int>(s.size()),nullptr,0);
    if(!n) fail("invalid UTF-8 argument");
    std::wstring r(n,L'\0');if(!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),static_cast<int>(s.size()),r.data(),n)) fail("invalid UTF-8 argument");return r;
}
std::wstring env(const wchar_t *name) {
    DWORD n=GetEnvironmentVariableW(name,nullptr,0);if(!n) return {};
    std::wstring r(n,L'\0');DWORD used=GetEnvironmentVariableW(name,r.data(),n);if(!used||used>=n) fail("cannot read environment");r.resize(used);return r;
}
fs::path self() {
    std::wstring r(32768,L'\0');DWORD n=GetModuleFileNameW(nullptr,r.data(),static_cast<DWORD>(r.size()));
    if(!n||n>=r.size()) fail("cannot locate Awl installation");r.resize(n);return fs::canonical(r);
}
std::wstring nonce() {
    std::array<unsigned char,16> b{};if(BCryptGenRandom(nullptr,b.data(),static_cast<ULONG>(b.size()),BCRYPT_USE_SYSTEM_PREFERRED_RNG)) throw std::runtime_error("cannot create secure temporary name");
    std::wstring r;for(auto v:b){r+=L"0123456789abcdef"[v>>4];r+=L"0123456789abcdef"[v&15];}return r;
}
struct Temporary {
    fs::path path;
    Temporary() {
        std::wstring base(32768,L'\0');DWORD n=GetTempPathW(static_cast<DWORD>(base.size()),base.data());if(!n||n>=base.size()) fail("cannot locate temporary directory");base.resize(n);
        Handle token;if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token.h)) fail("cannot query user token");
        DWORD bytes=0;GetTokenInformation(token.h,TokenUser,nullptr,0,&bytes);std::vector<unsigned char> info(bytes);
        if(!bytes||!GetTokenInformation(token.h,TokenUser,info.data(),bytes,&bytes)) fail("cannot query user identity");
        LPWSTR sid=nullptr;if(!ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(info.data())->User.Sid,&sid)) fail("cannot encode user identity");
        const std::wstring acl=L"D:P(A;;FA;;;SY)(A;;FA;;;"+std::wstring(sid)+L")";LocalFree(sid);
        PSECURITY_DESCRIPTOR sd=nullptr;if(!ConvertStringSecurityDescriptorToSecurityDescriptorW(acl.c_str(),SDDL_REVISION_1,&sd,nullptr)) fail("cannot secure temporary directory");
        SECURITY_ATTRIBUTES sa{sizeof(sa),sd,FALSE};bool ok=false;
        for(int i=0;i<32&&!ok;++i){path=fs::path(base)/(L"Awl-"+nonce());ok=CreateDirectoryW(path.c_str(),&sa)!=0;if(!ok&&GetLastError()!=ERROR_ALREADY_EXISTS) break;}
        DWORD error=GetLastError();LocalFree(sd);if(!ok){SetLastError(error);fail("cannot create private temporary directory");}
    }
    ~Temporary(){std::error_code ec;fs::remove_all(path,ec);}
};
struct Staging {
    fs::path path;
    explicit Staging(const fs::path &parent) {
        for(int i=0;i<32;++i){path=parent/(L".Awl-output-"+nonce()+L".exe");Handle f(CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr));if(f.valid()) return;if(GetLastError()!=ERROR_FILE_EXISTS) break;}
        fail("cannot stage output in destination directory");
    }
    ~Staging(){if(!path.empty()) DeleteFileW(path.c_str());}
};
// Microsoft CRT command-line escaping, including trailing backslashes/empty args.
std::wstring quote(const std::wstring &s) {
    std::wstring r=L"\"";size_t slashes=0;
    for(wchar_t c:s){if(c==L'\\'){++slashes;continue;}if(c==L'\"'){r.append(slashes*2+1,L'\\');r+=c;}else{r.append(slashes,L'\\');r+=c;}slashes=0;}
    r.append(slashes*2,L'\\');return r+L'\"';
}
volatile LONG cancelled=0;
BOOL WINAPI cancel(DWORD event) {if(event==CTRL_C_EVENT||event==CTRL_BREAK_EVENT){InterlockedExchange(&cancelled,1);return TRUE;}return FALSE;}
struct Cancellation {
    Cancellation(){InterlockedExchange(&cancelled,0);if(!SetConsoleCtrlHandler(cancel,TRUE)) fail("cannot install console handler");}
    ~Cancellation(){SetConsoleCtrlHandler(cancel,FALSE);}
};
struct Attributes {
    std::vector<unsigned char> data;LPPROC_THREAD_ATTRIBUTE_LIST list=nullptr;
    explicit Attributes(HANDLE *handles) {
        SIZE_T n=0;InitializeProcThreadAttributeList(nullptr,1,0,&n);data.resize(n);list=reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(data.data());
        if(!InitializeProcThreadAttributeList(list,1,0,&n)) fail("cannot initialize handle isolation");
        if(!UpdateProcThreadAttribute(list,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,handles,3*sizeof(HANDLE),nullptr,nullptr)){DeleteProcThreadAttributeList(list);list=nullptr;fail("cannot isolate inherited handles");}
    }
    ~Attributes(){if(list) DeleteProcThreadAttributeList(list);}
};
int execute(const std::vector<std::wstring> &args,const std::vector<wchar_t> *environment,unsigned timeout,unsigned memory) {
    if(cancelled) return 130;
    Handle job(CreateJobObjectW(nullptr,nullptr));if(!job.valid()) fail("cannot create child job");
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if(memory){limits.BasicLimitInformation.LimitFlags|=JOB_OBJECT_LIMIT_JOB_MEMORY;limits.JobMemoryLimit=static_cast<SIZE_T>(memory)*1024*1024;}
    if(!SetInformationJobObject(job.h,JobObjectExtendedLimitInformation,&limits,sizeof(limits))) fail("cannot configure child job");
    Handle in,out,err;Handle *streams[]={&in,&out,&err};DWORD ids[]={STD_INPUT_HANDLE,STD_OUTPUT_HANDLE,STD_ERROR_HANDLE};HANDLE inherited[3];
    for(int i=0;i<3;++i){HANDLE source=GetStdHandle(ids[i]);if(source&&source!=INVALID_HANDLE_VALUE){if(!DuplicateHandle(GetCurrentProcess(),source,GetCurrentProcess(),&streams[i]->h,0,TRUE,DUPLICATE_SAME_ACCESS)) fail("cannot duplicate standard handle");}
        else {SECURITY_ATTRIBUTES sa{sizeof(sa),nullptr,TRUE};streams[i]->h=CreateFileW(L"NUL",i?GENERIC_WRITE:GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&sa,OPEN_EXISTING,0,nullptr);if(!streams[i]->valid()) fail("cannot open standard handle");}inherited[i]=streams[i]->h;}
    Attributes attrs(inherited);STARTUPINFOEXW si{};si.StartupInfo.cb=sizeof(si);si.StartupInfo.dwFlags=STARTF_USESTDHANDLES;si.StartupInfo.hStdInput=in.h;si.StartupInfo.hStdOutput=out.h;si.StartupInfo.hStdError=err.h;si.lpAttributeList=attrs.list;
    std::wstring command;for(const auto &a:args){if(!command.empty()) command+=L' ';command+=quote(a);}if(command.size()>=32767) throw std::runtime_error("backend command line exceeds Windows limit");
    PROCESS_INFORMATION pi{};
    if(!CreateProcessW(args.at(0).c_str(),command.data(),nullptr,nullptr,TRUE,CREATE_SUSPENDED|CREATE_UNICODE_ENVIRONMENT|EXTENDED_STARTUPINFO_PRESENT,environment?const_cast<wchar_t*>(environment->data()):nullptr,nullptr,&si.StartupInfo,&pi)) fail("cannot execute bundled tool/program");
    Handle process(pi.hProcess),thread(pi.hThread);
    if(!AssignProcessToJobObject(job.h,process.h)){TerminateProcess(process.h,2);WaitForSingleObject(process.h,INFINITE);fail("cannot supervise child descendants");}
    if(ResumeThread(thread.h)==static_cast<DWORD>(-1)){TerminateJobObject(job.h,2);WaitForSingleObject(process.h,INFINITE);fail("cannot start supervised process");}
    const ULONGLONG start=GetTickCount64();int status=2;
    for(;;){DWORD w=WaitForSingleObject(process.h,25);if(w==WAIT_OBJECT_0){DWORD code=0;if(!GetExitCodeProcess(process.h,&code)) fail("cannot read child exit status");status=cancelled||code==0xc000013a?130:code>255?2:static_cast<int>(code);break;}if(w!=WAIT_TIMEOUT) fail("cannot wait for child");
        if(cancelled||(timeout&&GetTickCount64()-start>=static_cast<ULONGLONG>(timeout)*1000)){status=cancelled?130:124;break;}}
    if(!TerminateJobObject(job.h,status)) fail("cannot terminate child job");
    if(WaitForSingleObject(process.h,5000)!=WAIT_OBJECT_0) fail("cannot reap child process");
    const ULONGLONG cleanup=GetTickCount64();
    for(;;){JOBOBJECT_BASIC_ACCOUNTING_INFORMATION info{};if(!QueryInformationJobObject(job.h,JobObjectBasicAccountingInformation,&info,sizeof(info),nullptr)) fail("cannot inspect child job cleanup");if(!info.ActiveProcesses)break;if(GetTickCount64()-cleanup>=5000) fail("cannot reap child descendants");Sleep(10);}
    // Closing the non-inherited job handle also kills descendants on exceptions/parent death.
    return status;
}
uint64_t little(const unsigned char *p,size_t n){uint64_t v=0;for(size_t i=0;i<n;++i)v|=uint64_t(p[i])<<(i*8);return v;}
void inspect(const fs::path &path) {
    Handle f(CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr));if(!f.valid()) fail("cannot inspect generated executable");
    BY_HANDLE_FILE_INFORMATION info{};LARGE_INTEGER length{};
    auto invalid=[](){throw std::runtime_error("backend output is not a supported x86-64 PE executable");};
    if(!GetFileInformationByHandle(f.h,&info)||info.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY)||!GetFileSizeEx(f.h,&length)||length.QuadPart<256||length.QuadPart>256LL*1024*1024) invalid();
    auto read=[&](uint64_t at,unsigned char *p,DWORD n){LARGE_INTEGER offset{};offset.QuadPart=at;DWORD got=0;if(at>static_cast<uint64_t>(length.QuadPart)||n>static_cast<uint64_t>(length.QuadPart)-at||!SetFilePointerEx(f.h,offset,nullptr,FILE_BEGIN)||!ReadFile(f.h,p,n,&got,nullptr)||got!=n) invalid();};
    std::array<unsigned char,64> dos{};read(0,dos.data(),64);if(dos[0]!='M'||dos[1]!='Z') invalid();uint64_t offset=little(dos.data()+60,4);
    std::array<unsigned char,264> pe{};read(offset,pe.data(),264);
    if(little(pe.data(),4)!=0x4550||little(pe.data()+4,2)!=0x8664||little(pe.data()+24,2)!=0x20b||!(little(pe.data()+22,2)&2)||(little(pe.data()+22,2)&0x2000)) invalid();
    const auto count=little(pe.data()+6,2),optional=little(pe.data()+20,2),entry=little(pe.data()+40,4);if(!count||count>96||optional<240) invalid();
    bool executable=false;
    for(uint64_t i=0;i<count;++i){std::array<unsigned char,40> section{};read(offset+24+optional+i*40,section.data(),40);auto address=little(section.data()+12,4),size=little(section.data()+8,4),bytes=little(section.data()+16,4),at=little(section.data()+20,4);if(at>static_cast<uint64_t>(length.QuadPart)||bytes>static_cast<uint64_t>(length.QuadPart)-at) invalid();if((little(section.data()+36,4)&0x20000000)&&entry>=address&&entry-address<size) executable=true;}
    if(!executable) invalid();
}
int build(const char *c_source,size_t length,const std::string &source_path,const std::string &output,const Awl_driver::Options &options,bool run) {
    try {
        Cancellation cancellation;const auto root=self().parent_path().parent_path();const auto zig=root/L"libexec/zig/zig.exe",lib=root/L"libexec/zig/lib";
        if(!fs::is_regular_file(zig)||!fs::is_directory(lib)) throw std::runtime_error("bundled toolchain missing; use the complete Awl Windows bundle (no system-tool fallback)");
        Temporary temp;auto local=env(L"LOCALAPPDATA");fs::path cache=local.empty()?temp.path/L"global-cache":fs::path(local)/L"Awl/zig-0.15.2";fs::create_directories(cache);
        auto cfile=temp.path/L"program.c";{std::ofstream file(cfile,std::ios::binary);file.write(c_source,static_cast<std::streamsize>(length));file.close();if(!file) throw std::runtime_error("cannot write generated C");}
        fs::path destination=run?temp.path/L"program.exe":fs::absolute(output.empty()?fs::path(wide(source_path)).stem().wstring()+L".exe":wide(output));
        std::vector<std::string> sources=options.protected_sources;sources.push_back(source_path);
        for(const auto &p:sources){const auto source=fs::canonical(fs::path(wide(p)));if(fs::weakly_canonical(destination)==source||(fs::exists(destination)&&fs::equivalent(destination,source))) throw std::runtime_error("refusing to overwrite source with executable");}
        Staging staging(destination.parent_path());
        std::vector<std::wstring> vars={L"HOME="+temp.path.wstring(),L"PATH=C:\\no-host-tools",L"TEMP="+temp.path.wstring(),L"TMP="+temp.path.wstring(),L"ZIG_LIB_DIR="+lib.wstring(),L"ZIG_GLOBAL_CACHE_DIR="+cache.wstring(),L"ZIG_LOCAL_CACHE_DIR="+(temp.path/L"local-cache").wstring()};
        for(auto name:{L"SystemRoot",L"WINDIR"}){auto value=env(name);if(!value.empty()) vars.push_back(std::wstring(name)+L"="+value);}
        std::sort(vars.begin(),vars.end(),[](const auto &a,const auto &b){return _wcsicmp(a.c_str(),b.c_str())<0;});std::vector<wchar_t> environment;for(const auto &v:vars){environment.insert(environment.end(),v.begin(),v.end());environment.push_back(0);}environment.push_back(0);
        int status=execute({zig.wstring(),L"cc",L"-std=c11",L"-target",L"x86_64-windows-gnu",L"-mcpu=baseline",L"-O"+std::to_wstring(options.optimization),L"-g0",L"-s",cfile.wstring(),L"-luser32",L"-lgdi32",L"-lshell32",L"-o",staging.path.wstring()},&environment,options.build_timeout_seconds,options.build_memory_mib);
        if(status){std::cerr<<"kcc: bundled backend failed/interrupted or wall-time limit exceeded ("<<status<<")\n";return status==124||status==130?status:2;}
        inspect(staging.path);if(cancelled) return 130;
        if(!MoveFileExW(staging.path.c_str(),destination.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) fail("cannot publish executable");staging.path.clear();
        if(run){status=execute({destination.wstring()},nullptr,options.run_timeout_seconds,0);if(status==124)std::cerr<<"kcc: program wall-time limit exceeded\n";return status;}
        auto utf8=destination.u8string();std::cout.write(reinterpret_cast<const char*>(utf8.data()),utf8.size());std::cout<<'\n';std::cout.flush();return std::cout?0:2;
    }catch(const std::exception &e){std::cerr<<"kcc: "<<e.what()<<'\n';return 2;}
}
}
