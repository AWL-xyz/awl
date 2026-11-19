// Native public ASDK Beta front door. Included by acc.cpp; compiler stays in-process.
#include "package.h"
#include <filesystem>
#include <algorithm>
#include <set>
#include <stdexcept>
#include <utility>
#include <cerrno>
#if !defined(_WIN32)
#include <fcntl.h>
#include <unistd.h>
#endif
namespace Awl_toolkit {
namespace fs=std::filesystem;
std::string utf8(const fs::path &p) {const auto s=p.u8string();return std::string(s.begin(),s.end());}
fs::path path(const std::string &s) {return fs::path(std::u8string(s.begin(),s.end()));}
std::string trim(const std::string &s) {
    const auto a=s.find_first_not_of(" \t\r"),b=s.find_last_not_of(" \t\r");
    return a==std::string::npos?std::string():s.substr(a,b-a+1);
}
bool project_name(const std::string &s) {return Awl_package::valid_name(s)&&Awl_package::ascii_alnum(s.front());}
std::string command_key(std::string s) {for(char &c:s) if(c>='A'&&c<='Z') c+=32;return s;}
constexpr unsigned test_timeout_seconds=30;
void help() {
    std::cout<<"Awl Software Development Kit [Beta]\n"
        <<"Usage:\n"
        <<"  awl                         Show this help\n"
        <<"  awl new NAME                Create a new project directory with a starter test\n"
        <<"  awl init NAME               Create NAME.awproj and, if absent, main.aw here\n"
        <<"  awl init NAME --pkg         Create NAME.awpkg and, if absent, NAME.aw (a library package) here\n"
        <<"  awl add FILE.awpkg          Copy a local Package into the current project (no network)\n"
        <<"  awl check [TARGET]          Check syntax and types without a backend\n"
        <<"  awl build [TARGET]          Build a native executable\n"
        <<"  awl run [TARGET] [options] [-- ARG ...]  Build and run a temporary executable\n"
        <<"  awl test [TARGET]           Run .test.aw files beside the project entry, or one .aw file\n\n"
        <<"TARGET: omit for the sole .awproj here, use NAME for an immediate child\n"
        <<"project, or pass a .aw source path (imports supported).\n\n"
        <<"Check/build/run/test options:\n"
        <<"  --syntax aesop               Aesop is the only supported syntax\n"
        <<"  --diagnostic-format text|json Source diagnostic format (default text)\n"
        <<"Build/run/test options:\n"
        <<"  --cc ABSOLUTE_PATH           Use a host C compiler (Linux x86-64 only)\n"
        <<"  -O 0|1|2|3                   Optimization level (default 2)\n"
        <<"  --build-timeout 1..3600       Backend timeout in seconds (default 120)\n"
        <<"  --build-memory-mib 512..16384 Backend memory bound (default 4096)\n"
        <<"Build only: -o FILE             Executable destination (relative to terminal cwd)\n"
        <<"Run/test: --run-timeout 0..86400  Per-program timeout in seconds (0 = unlimited)\n"
        <<"                                Default: unlimited for run, "<<test_timeout_seconds<<" seconds for test\n"
        <<"Test-only options:\n"
        <<"  --filter TEXT                Select filenames containing TEXT (case-sensitive)\n"
        <<"  --list                       List the selected tests without compiling\n"
        <<"  --check                      Check the selected tests without a backend\n"
        <<"  --fail-fast                  Stop after the first failure\n\n"
        <<"Project output: <project>/build/<manifest-name> (.exe on Windows).\n"
        <<"Single-file output: <cwd>/<source-stem> (.exe on Windows).\n"
        <<"New and init never overwrite files. NAME: 1..64 letters/digits/_/-, starts alphanumeric.\n"
        <<"Build/run/test use the bundled backend unless --cc is specified.\n";
}
// Exclusive creation, no shell and no truncation of pre-existing files/symlinks.
void create_new(const fs::path &p,const std::string &bytes) {
#if defined(_WIN32)
    HANDLE h=CreateFileW(p.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE) throw std::runtime_error("cannot exclusively create "+utf8(p));
    DWORD wrote=0;const bool ok=WriteFile(h,bytes.data(),static_cast<DWORD>(bytes.size()),&wrote,nullptr)&&wrote==bytes.size();
    const bool closed=CloseHandle(h)!=0;
#else
    int fd=open(p.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0666);
    if(fd<0) throw std::runtime_error("cannot exclusively create "+utf8(p));
    size_t offset=0;bool ok=true;
    while(offset<bytes.size()) {const auto n=write(fd,bytes.data()+offset,bytes.size()-offset);if(n<0&&errno==EINTR) continue;if(n<=0){ok=false;break;}offset+=static_cast<size_t>(n);}
    const bool closed=close(fd)==0;
#endif
    if(!ok||!closed) {
        std::error_code ec;fs::remove(p,ec);
        throw std::runtime_error("cannot write "+utf8(p));
    }
}
constexpr const char *project_manifest="format: 1\nentry: main.aw\nsyntax: aesop\n";
fs::path new_project(const fs::path &cwd,const std::string &name) {
    const auto folder=cwd/path(name);
    const std::pair<fs::path,std::string> files[]={
        {folder/"App.aw",R"AWL(exports {
    @r func greet :: who:text {
        return "Hello, " + who + "!";
    };
};
)AWL"},
        {folder/"main.aw",R"AWL(use App.aw as app;

func main {
    print(app.greet("Awl"));
    return 0;
};
)AWL"},
        {folder/"Smoke.test.aw",R"AWL(use App.aw as app;

func main {
    if app.greet("Awl") != "Hello, Awl!" {
        print("the starter greeting changed unexpectedly");
        return 1;
    };
    return 0;
};
)AWL"},
        {folder/".gitignore","/build/\n"},
        {folder/path(name+".awproj"),project_manifest} // Publish the manifest last.
    };
    if(fs::symlink_status(folder).type()!=fs::file_type::not_found||!fs::create_directory(folder))
        throw std::runtime_error("project path already exists; refusing to overwrite "+utf8(folder));
    size_t written=0;
    try {
        for(const auto &[file,bytes]:files) {create_new(file,bytes);++written;}
    } catch(...) {
        std::error_code ec;
        while(written) fs::remove(files[--written].first,ec);
        fs::remove(folder,ec); // Leave the directory alone if it is no longer empty.
        throw;
    }
    return folder;
}
std::vector<fs::path> manifests(const fs::path &folder) {
    std::vector<fs::path> found;size_t seen=0;
    for(const auto &e:fs::directory_iterator(folder)) {
        if(++seen>4096) throw std::runtime_error("project discovery exceeds 4096 entries per directory");
        if(e.path().extension()==".awproj"&&!e.is_symlink()&&e.is_regular_file()) found.push_back(e.path());
    }
    std::sort(found.begin(),found.end());return found;
}
fs::path discover(const fs::path &cwd,const std::string &name) {
    if(name.empty()) {
        const auto found=manifests(cwd);
        if(found.empty()) throw std::runtime_error("no .awproj project in current directory; use awl init NAME or specify a .aw file");
        if(found.size()!=1) throw std::runtime_error("multiple .awproj projects in current directory; keep one or specify an entry .aw file directly");
        return found[0];
    }
    if(!project_name(name)) throw std::runtime_error("invalid project name; use a simple NAME or a relative path ending in .aw");
    std::vector<fs::path> found;size_t seen=0,folders=0;
    for(const auto &e:fs::directory_iterator(cwd)) {
        if(++seen>4096) throw std::runtime_error("project discovery exceeds 4096 entries");
        if(!e.is_symlink()&&e.is_directory()) {
            if(++folders>512) throw std::runtime_error("project discovery exceeds 512 child folders");
            // Enumerating filenames makes project-name matching case-sensitive on all hosts.
            for(const auto &m:manifests(e.path())) if(utf8(m.filename())==name+".awproj") found.push_back(m);
        }
    }
    if(found.empty()) throw std::runtime_error("no immediate child folder contains "+name+".awproj");
    if(found.size()!=1) throw std::runtime_error("ambiguous project: multiple child folders contain "+name+".awproj; enter the desired folder or specify an entry .aw file");
    return found[0];
}
struct Project {fs::path manifest,entry;std::string syntax="aesop";};
Project read_project(const fs::path &file) {
    if(fs::is_symlink(file)||!fs::is_regular_file(file)||fs::file_size(file)>16384) throw std::runtime_error("manifest must be a regular non-symlink file of at most 16 KiB");
    std::ifstream in(file,std::ios::binary);if(!in) throw std::runtime_error("cannot read manifest");
    Project result;result.manifest=fs::canonical(file);std::string line,entry;std::set<std::string> keys;bool format=false;
    while(std::getline(in,line)) {
        line=trim(line);if(line.empty()||line[0]=='#') continue;
        if(line.find('\0')!=std::string::npos) throw std::runtime_error("NUL byte in manifest");
        const auto colon=line.find(':');if(colon==std::string::npos) throw std::runtime_error("invalid manifest line: expected key: value");
        const auto key=trim(line.substr(0,colon)),value=trim(line.substr(colon+1));
        if(!keys.insert(key).second) throw std::runtime_error("duplicate manifest key: "+key);
        if(key=="format") {if(value!="1") throw std::runtime_error("unsupported project manifest format");format=true;}
        else if(key=="entry") entry=value;
        else if(key=="syntax") {if(value!="aesop") throw std::runtime_error("manifest syntax must be aesop");result.syntax=value;}
        else throw std::runtime_error("unknown manifest key: "+key);
    }
    if(in.bad()) throw std::runtime_error("manifest read failed");
    if(!format||entry.empty()) throw std::runtime_error("manifest requires format: 1 and entry: relative/file.aw");
    const auto relative=path(entry);
    if(relative.is_absolute()||relative.has_root_name()||relative.extension()!=".aw") throw std::runtime_error("manifest entry must be a relative .aw path");
    const auto root=result.manifest.parent_path();result.entry=fs::canonical(root/relative);
    const auto within=result.entry.lexically_relative(root);
    if(within.empty()||*within.begin()==".."||!fs::is_regular_file(result.entry)) throw std::runtime_error("manifest entry must be a regular source inside the project folder");
    return result;
}
fs::path add_package(const Project &project,const fs::path &input) {
    if(input.extension()!=".awpkg") throw std::runtime_error("usage: awl add FILE.awpkg (a local manifest)");
    const auto name=utf8(input.stem());
    const auto folder=fs::canonical(fs::absolute(input).parent_path());
    const auto manifest_path=folder/input.filename();
    const auto manifest=Awl_package::read_manifest(manifest_path,name);
    // The standalone loader resolves use NAME relative to the entry's directory,
    // including when the project manifest names an entry in a subdirectory.
    const auto packages=project.entry.parent_path()/"packages";
    const auto package_status=fs::symlink_status(packages);
    if(package_status.type()!=fs::file_type::not_found&&!fs::is_directory(package_status))
        throw std::runtime_error("packages must be a real directory, not a symlink or file");
    const auto destination=packages/path(name);
    if(fs::symlink_status(destination).type()!=fs::file_type::not_found)
        throw std::runtime_error("Package '"+name+"' already exists; refusing to overwrite it");

    // Preflight all selected files before modifying the project. The walk is
    // bounded and never follows directory links or loads non-source assets.
    std::vector<std::pair<fs::path,std::string>> sources;
    size_t seen=0,total=0;bool has_entry=false;
    const auto entry=path(manifest.entry);
    for(auto it=fs::recursive_directory_iterator(folder);it!=fs::recursive_directory_iterator();++it) {
        if(++seen>512) throw std::runtime_error("Package source tree exceeds 512 directory entries");
        const auto &file=it->path();const auto filename=utf8(file.filename());
        if(filename.starts_with('.')||filename=="build"||filename=="packages") {
            it.disable_recursion_pending();continue;
        }
        if(it.depth()>8) throw std::runtime_error("Package source tree exceeds eight nested directories");
        const auto status=it->symlink_status();
        if(fs::is_symlink(status)) throw std::runtime_error("Package source tree contains a symlink: "+utf8(file));
        if(fs::is_directory(status)||file.extension()!=".aw") continue;
        if(sources.size()>=64) throw std::runtime_error("Package exceeds 64 .aw source files");
        auto bytes=Awl_package::read_file(file,Awl_package::source_limit-total);
        total+=bytes.size();auto relative=file.lexically_relative(folder);
        if(relative==entry) has_entry=true;
        sources.emplace_back(std::move(relative),std::move(bytes));
    }
    if(!has_entry) throw std::runtime_error("missing or wrong-case Package entry: "+manifest.entry);

    struct Pending {
        const fs::path &packages,&destination;
        bool made_packages=false,made_destination=false,complete=false;
        ~Pending() {
            if(complete) return;
            std::error_code ec;
            if(made_destination) fs::remove_all(destination,ec);
            if(made_packages) fs::remove(packages,ec); // Only remove this parent if it is still empty.
        }
    } pending{packages,destination};
    if(package_status.type()==fs::file_type::not_found) pending.made_packages=fs::create_directory(packages);
    if(!fs::is_directory(fs::symlink_status(packages))) throw std::runtime_error("packages must be a real directory");
    pending.made_destination=fs::create_directory(destination);
    if(!pending.made_destination) throw std::runtime_error("Package '"+name+"' already exists; refusing to overwrite it");
    for(const auto &[relative,bytes]:sources) {
        const auto file=destination/relative;
        fs::create_directories(file.parent_path());create_new(file,bytes);
    }
    // Write the manifest last so the loader cannot see a package before its sources.
    create_new(destination/manifest_path.filename(),manifest.bytes);
    pending.complete=true;
    return destination;
}
std::vector<fs::path> discover_tests(const fs::path &entry) {
    std::vector<fs::path> tests;size_t seen=0;
    for(const auto &file:fs::directory_iterator(entry.parent_path())) {
        if(++seen>4096) throw std::runtime_error("test discovery exceeds 4096 directory entries");
        const auto name=utf8(file.path().filename());
        if(!name.ends_with(".test.aw")||name.starts_with('.')||file.path()==entry) continue;
        if(!fs::is_regular_file(file.symlink_status()))
            throw std::runtime_error("test must be a regular non-symlink file: "+utf8(file.path()));
        if(tests.size()==64) throw std::runtime_error("test discovery exceeds 64 .test.aw files");
        tests.push_back(file.path());
    }
    if(tests.empty()) throw std::runtime_error("no .test.aw files beside the project entry; add one or pass a .aw test file directly");
    std::sort(tests.begin(),tests.end(),[](const auto &a,const auto &b){return utf8(a.filename())<utf8(b.filename());});
    return tests;
}
Awl_driver::Result invoke_compiler(std::vector<std::string> &args,bool stdin_eof=false) {
    std::vector<char*> raw;raw.reserve(args.size()+1);
    for(auto &a:args) raw.push_back(a.data());
    raw.push_back(nullptr);
    return Awl_compiler_main(static_cast<int>(args.size()),raw.data(),stdin_eof);
}
int run_tests(const char *argv0,const std::vector<fs::path> &tests,const fs::path &cwd,
              const std::string &syntax,const std::vector<std::string> &flags,bool check_only,bool fail_fast) {
    // Test sources are already absolute. Named and local project invocations
    // use the same working directory for relative fixtures.
    fs::current_path(cwd);
    size_t passed=0,failed=0;
    for(const auto &test:tests) {
        const auto name=utf8(test.filename());
        std::cout<<(check_only?"Checking ":"Testing ")<<name<<'\n'<<std::flush;
        if(!std::cout) return 2;
        std::vector<std::string> args={argv0,check_only?"check":"run",utf8(test),"--syntax",syntax};
        args.insert(args.end(),flags.begin(),flags.end());
        const auto result=invoke_compiler(args,!check_only);
        if(result.termination==Awl_driver::Termination::Interrupted) {
            std::cout<<"INTERRUPTED "<<name<<'\n'<<std::flush;
            return result.code;
        }
        if(!result.code) {++passed;std::cout<<"PASS "<<name<<'\n';}
        else {
            ++failed;
            if(result.termination==Awl_driver::Termination::TimedOut) std::cout<<"TIMEOUT "<<name<<'\n';
            else std::cout<<"FAIL "<<name<<" (status "<<result.code<<")\n";
            if(fail_fast) break;
        }
    }
    std::cout<<"Test result: "<<passed<<" passed, "<<failed<<" failed";
    const auto skipped=tests.size()-passed-failed;
    if(skipped) std::cout<<", "<<skipped<<" skipped";
    std::cout<<'\n'<<std::flush;
    if(!std::cout) return 2;
    return failed?1:0;
}
int run(int argc,char **argv) {
    try {
        if(argc==1||(argc==2&&(command_key(argv[1])=="--help"||std::string(argv[1])=="-h"))) {help();return std::cout?0:2;}
        if(argc==2&&command_key(argv[1])=="--version") {std::cout<<"Awl Software Development Kit [Beta] 0.26.0-dev\n";return std::cout?0:2;}
        const std::string command=command_key(argv[1]);const auto cwd=fs::current_path();
        if(command=="new") {
            if(argc!=3||!project_name(argv[2])) throw std::runtime_error("usage: awl new NAME (1..64 letters/digits/_/-, starts alphanumeric; no reserved device names)");
            const auto folder=new_project(cwd,argv[2]);
            std::cout<<"Created "<<utf8(folder)<<" with a starter test.\nCheck with: awl check "<<argv[2]<<"\nTest with: awl test "<<argv[2]<<'\n';
            return std::cout?0:2;
        }
        if(command=="init") {
            const bool package=argc==4&&(std::string(argv[3])=="--pkg"||std::string(argv[2])=="--pkg");
            const char *project_arg=package&&std::string(argv[2])=="--pkg"?argv[3]:argv[2];
            if(package) {
                if(!project_name(project_arg)) throw std::runtime_error("usage: awl init NAME --pkg (1..64 letters/digits/_/-, starts alphanumeric; no reserved device names)");
                const std::string name=project_arg;
                const auto manifest=cwd/path(name+".awpkg"),source=cwd/path(name+".aw");
                if(fs::symlink_status(manifest).type()!=fs::file_type::not_found) throw std::runtime_error("package manifest already exists; refusing to overwrite it");
                const auto source_status=fs::symlink_status(source);
                if(source_status.type()!=fs::file_type::not_found&&(fs::is_symlink(source_status)||!fs::is_regular_file(source_status))) throw std::runtime_error(name+".aw exists but is not a regular non-symlink file; refusing to use it");
                bool made=false;
                if(source_status.type()==fs::file_type::not_found) {create_new(source,"exports{\n    @r func hello :: who:text {\n        return \"Hello, \" + who + \"!\";\n    };\n};\n");made=true;}
                create_new(manifest,"format: 1\nkind: package\nname: "+name+"\nversion: 0.1.0\nentry: "+name+".aw\nsyntax: aesop\n");
                std::cout<<"Initialized package "<<name<<" in "<<utf8(cwd)<<"\n"<<(made?"Created":"Preserved")<<" "<<name<<".aw\nCreated "<<name<<".awpkg\nFrom a project directory, install with awl add PATH_TO_MANIFEST.\n";return std::cout?0:2;
            }
            if(argc!=3||!project_name(argv[2])) throw std::runtime_error("usage: awl init NAME (1..64 letters/digits/_/-, starts alphanumeric; no reserved device names) or awl init NAME --pkg");
            const auto manifest=cwd/path(std::string(argv[2])+".awproj"),source=cwd/"main.aw";
            if(fs::symlink_status(manifest).type()!=fs::file_type::not_found) throw std::runtime_error("manifest already exists; refusing to overwrite it");
            const auto source_status=fs::symlink_status(source);
            if(source_status.type()!=fs::file_type::not_found&&(fs::is_symlink(source_status)||!fs::is_regular_file(source_status))) throw std::runtime_error("main.aw exists but is not a regular non-symlink source");
            bool made=false;
            if(source_status.type()==fs::file_type::not_found) {create_new(source,"func main {\n    print(\"Hello from Awl!\");\n    return 0;\n};\n");made=true;}
            create_new(manifest,project_manifest);
            std::cout<<"Initialized "<<argv[2]<<" in "<<utf8(cwd)<<"\n"<<(made?"Created":"Preserved")<<" main.aw\nCreated "<<utf8(manifest.filename())<<"\nCheck with: awl check\n";return std::cout?0:2;
        }
        if(command=="add") {
            if(argc!=3) throw std::runtime_error("usage: awl add FILE.awpkg (a local manifest)");
            const auto project=read_project(discover(cwd,{}));
            const auto installed=add_package(project,path(argv[2]));
            std::cout<<"Added Package "<<utf8(installed.filename())<<" at "<<utf8(installed)<<'\n';
            return std::cout?0:2;
        }
        const bool build=command=="build",run=command=="run",test=command=="test";
        const bool running=run||test,building=build||running;
        if(command!="check"&&!building) throw std::runtime_error("unknown command '"+command+"'; use awl --help");
        int i=2;std::string target,explicit_output,test_filter;
        if(i<argc&&argv[i][0]!='-') target=argv[i++];
        std::vector<std::string> flags;std::set<std::string> seen;
        for(;i<argc;++i) {
            const std::string option=argv[i];
            if(run&&option=="--") break; // Forward the delimiter and all following arguments unchanged.
            if(!seen.insert(option).second) throw std::runtime_error("duplicate option: "+option);
            if(test&&(option=="--list"||option=="--check"||option=="--fail-fast")) continue;
            const bool common=option=="--syntax"||option=="--diagnostic-format";
            const bool backend=option=="--cc"||option=="-O"||option=="--build-timeout"||option=="--build-memory-mib";
            if(!(common||(building&&backend)||(build&&option=="-o")||(running&&option=="--run-timeout")||(test&&option=="--filter")))
                throw std::runtime_error("unknown "+command+" option: "+option);
            if(++i>=argc||(running&&std::string(argv[i])=="--")) throw std::runtime_error("missing value for "+option);
            const std::string value=argv[i];unsigned parsed=0;
            if(option=="--filter") {
                if(value.empty()) throw std::runtime_error("--filter requires a nonempty filename substring");
                test_filter=value;continue;
            }
            if(option=="--syntax"&&value!="aesop") throw std::runtime_error("syntax must be aesop");
            if(option=="--diagnostic-format"&&value!="text"&&value!="json") throw std::runtime_error("diagnostic format must be text or json");
            if(option=="--cc"&&value.empty()) throw std::runtime_error("--cc requires an absolute compiler path");
            if(option=="-O"&&!(value.size()==1&&value[0]>='0'&&value[0]<='3')) throw std::runtime_error("optimization must be 0..3");
            if(option=="--build-timeout"&&!number(value,1,3600,parsed)) throw std::runtime_error("build timeout must be 1..3600");
            if(option=="--build-memory-mib"&&!number(value,512,16384,parsed)) throw std::runtime_error("build memory must be 512..16384 MiB");
            if(option=="--run-timeout"&&!number(value,0,86400,parsed)) throw std::runtime_error("run timeout must be 0..86400");
            if(option=="-o") {if(value.empty()) throw std::runtime_error("empty output path");explicit_output=value;}
            else if(option!="--syntax") {flags.push_back(option);flags.push_back(value);}
        }
        const bool list_only=seen.contains("--list"),check_only=seen.contains("--check"),fail_fast=seen.contains("--fail-fast");
        if(list_only&&(check_only||fail_fast)) throw std::runtime_error("--list cannot be combined with --check or --fail-fast");
        if(list_only||check_only) {
            for(const auto *option:{"--cc","-O","--build-timeout","--build-memory-mib","--run-timeout"})
                if(seen.contains(option)) throw std::runtime_error(std::string(option)+" requires building and running tests");
        }
        Project project;
        const bool single=!target.empty()&&path(target).extension()==".aw";
        if(single) {
            project.entry=fs::canonical(path(target));
            if(!fs::is_regular_file(project.entry)) throw std::runtime_error("source is not a regular .aw file");
        } else project=read_project(discover(cwd,target));
        const auto &source=project.entry,&manifest=project.manifest;
        if(test) {
            auto tests=single?std::vector<fs::path>{source}:discover_tests(source);
            if(!test_filter.empty()) {
                tests.erase(std::remove_if(tests.begin(),tests.end(),[&](const fs::path &file) {
                    return utf8(file.filename()).find(test_filter)==std::string::npos;
                }),tests.end());
                if(tests.empty()) throw std::runtime_error("no tests match --filter: "+test_filter);
            }
            if(list_only) {
                for(const auto &file:tests) std::cout<<utf8(file.filename())<<'\n';
                return (std::cout<<std::flush)?0:2;
            }
            if(!check_only&&!seen.contains("--run-timeout")) {
                flags.push_back("--run-timeout");flags.push_back(std::to_string(test_timeout_seconds));
            }
            return run_tests(argv[0],tests,single?cwd:manifest.parent_path(),project.syntax,flags,check_only,fail_fast);
        }
        if(build&&!explicit_output.empty()) {
            // Protect the selected manifest (even through a hardlink) and .awproj destinations.
            const auto dest=fs::absolute(path(explicit_output));
            if(dest.extension()==".awproj"||(!manifest.empty()&&(fs::weakly_canonical(dest)==manifest||(fs::exists(dest)&&fs::equivalent(dest,manifest))))) throw std::runtime_error("refusing to overwrite a .awproj project manifest");
            if(!fs::is_directory(dest.parent_path())) throw std::runtime_error("output directory does not exist");
            flags.push_back("-o");flags.push_back(explicit_output);
        } else if(build&&!single) {
            auto output=manifest.parent_path()/"build"/manifest.stem();
#if defined(_WIN32)
            output+=".exe";
#endif
            const auto parent=output.parent_path();
            if(fs::is_symlink(parent)||(fs::exists(parent)&&!fs::is_directory(parent))) throw std::runtime_error("project build output directory must be a real directory, not a symlink");
            fs::create_directories(parent);flags.push_back("-o");flags.push_back(utf8(output));
        }
        std::vector<std::string> args={argv[0],command,utf8(source),"--syntax",project.syntax};args.insert(args.end(),flags.begin(),flags.end());
        args.insert(args.end(),argv+i,argv+argc);
        return invoke_compiler(args).code;
    } catch(const std::exception &e) {std::cerr<<"Awl: "<<e.what()<<'\n';return 2;}
}
}
