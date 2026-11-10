// Native public ASDK Beta front door. Included by acc.cpp; compiler stays in-process.
#include <filesystem>
#include <algorithm>
#include <set>
#include <stdexcept>
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
bool project_name(const std::string &s) {
    if(s.empty()||s.size()>64) return false;
    auto alnum=[](char c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9');};
    if(!alnum(s[0])) return false;
    for(char c:s) if(!alnum(c)&&c!='_'&&c!='-') return false;
    std::string upper=s;for(char &c:upper) if(c>='a'&&c<='z') c-=32;
    if(upper=="CON"||upper=="PRN"||upper=="AUX"||upper=="NUL") return false;
    if(upper.size()==4&&(upper.substr(0,3)=="COM"||upper.substr(0,3)=="LPT")&&upper[3]>='1'&&upper[3]<='9') return false;
    return true;
}
std::string command_key(std::string s) {for(char &c:s) if(c>='A'&&c<='Z') c+=32;return s;}
void help() {
    std::cout<<"Awl Software Development Kit [Beta]\n"
        <<"Usage:\n"
        <<"  awl                         Show this help\n"
        <<"  awl init NAME               Create NAME.awproj and, if absent, main.aw here\n"
        <<"  awl init NAME --pkg         Create NAME.awpkg and, if absent, NAME.aw (a library package) here\n"
        <<"  awl build                   Build the sole .awproj project here\n"
        <<"  awl build NAME              Find NAME.awproj in an immediate child folder\n"
        <<"  awl build relative/file.aw   Compile a single .aw file (imports supported)\n\n"
        <<"Build options:\n"
        <<"  -o FILE                      Executable destination (relative to terminal cwd)\n"
        <<"  -O 0|1|2|3                   Optimization level (default 2)\n"
        <<"  --syntax aesop               Aesop is the only supported syntax\n"
        <<"  --build-timeout 1..3600       Backend timeout in seconds (default 120)\n"
        <<"  --build-memory-mib 512..16384 Backend memory bound (default 4096)\n\n"
        <<"Project output: <project>/build/<manifest-name> (.exe on Windows).\n"
        <<"Single-file output: <cwd>/<source-stem> (.exe on Windows).\n"
        <<"Init never overwrites existing files. NAME: 1..64 letters/digits/_/-, starts alphanumeric.\n"
        <<"Compilation needs the complete bundled backend, not Python or a host compiler.\n"
        <<"Only initialization and compilation are included; no run/install commands yet.\n";
}
// Exclusive creation, no shell and no truncation of pre-existing files/symlinks.
void create_new(const fs::path &p,const std::string &bytes) {
#if defined(_WIN32)
    HANDLE h=CreateFileW(p.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE) throw std::runtime_error("cannot exclusively create "+utf8(p));
    DWORD wrote=0;const bool ok=WriteFile(h,bytes.data(),static_cast<DWORD>(bytes.size()),&wrote,nullptr)&&wrote==bytes.size();
    const bool closed=CloseHandle(h)!=0;
    if(!ok||!closed) throw std::runtime_error("cannot write "+utf8(p)+"; initialization may be incomplete");
#else
    int fd=open(p.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0666);
    if(fd<0) throw std::runtime_error("cannot exclusively create "+utf8(p));
    size_t offset=0;bool ok=true;
    while(offset<bytes.size()) {const auto n=write(fd,bytes.data()+offset,bytes.size()-offset);if(n<0&&errno==EINTR) continue;if(n<=0){ok=false;break;}offset+=static_cast<size_t>(n);}
    const bool closed=close(fd)==0;
    if(!ok||!closed) throw std::runtime_error("cannot write "+utf8(p)+"; initialization may be incomplete");
#endif
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
        if(found.empty()) throw std::runtime_error("no .awproj project in current directory; use awl init NAME or awl build file.aw");
        if(found.size()!=1) throw std::runtime_error("multiple .awproj projects in current directory; keep one or build an entry .aw file directly");
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
    if(found.size()!=1) throw std::runtime_error("ambiguous project: multiple child folders contain "+name+".awproj; enter the desired folder and use awl build");
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
int run(int argc,char **argv,int (*compiler)(int,char**)) {
    try {
        if(argc==1||(argc==2&&(command_key(argv[1])=="--help"||std::string(argv[1])=="-h"))) {help();return std::cout?0:2;}
        if(argc==2&&command_key(argv[1])=="--version") {std::cout<<"Awl Software Development Kit [Beta] 0.26.0-dev\n";return std::cout?0:2;}
        const std::string command=command_key(argv[1]);const auto cwd=fs::current_path();
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
                std::cout<<"Initialized package "<<name<<" in "<<utf8(cwd)<<"\n"<<(made?"Created":"Preserved")<<" "<<name<<".aw\nCreated "<<name<<".awpkg\nInstall by copying this folder to <project>/packages/"<<name<<"/ and writing: use "<<name<<";\n";return std::cout?0:2;
            }
            if(argc!=3||!project_name(argv[2])) throw std::runtime_error("usage: awl init NAME (1..64 letters/digits/_/-, starts alphanumeric; no reserved device names) or awl init NAME --pkg");
            const auto manifest=cwd/path(std::string(argv[2])+".awproj"),source=cwd/"main.aw";
            if(fs::symlink_status(manifest).type()!=fs::file_type::not_found) throw std::runtime_error("manifest already exists; refusing to overwrite it");
            const auto source_status=fs::symlink_status(source);
            if(source_status.type()!=fs::file_type::not_found&&(fs::is_symlink(source_status)||!fs::is_regular_file(source_status))) throw std::runtime_error("main.aw exists but is not a regular non-symlink source");
            bool made=false;
            if(source_status.type()==fs::file_type::not_found) {create_new(source,"func main {\n    print(\"Hello from Awl!\");\n    return 0;\n};\n");made=true;}
            create_new(manifest,"format: 1\nentry: main.aw\nsyntax: aesop\n");
            std::cout<<"Initialized "<<argv[2]<<" in "<<utf8(cwd)<<"\n"<<(made?"Created":"Preserved")<<" main.aw\nCreated "<<utf8(manifest.filename())<<"\nBuild with: awl build\n";return std::cout?0:2;
        }
        if(command!="build") throw std::runtime_error("unknown command '"+command+"'; use Awl for help (beta includes only init/build)");
        int i=2;std::string target;
        if(i<argc&&argv[i][0]!='-') target=argv[i++];
        std::vector<std::string> flags;std::string override_syntax;bool explicit_output=false;std::set<std::string> seen;
        for(;i<argc;++i) {
            const std::string option=argv[i];
            if(!seen.insert(option).second) throw std::runtime_error("duplicate option: "+option);
            if(option!="-o"&&option!="-O"&&option!="--syntax"&&option!="--build-timeout"&&option!="--build-memory-mib") throw std::runtime_error("unknown build option: "+option);
            if(++i>=argc) throw std::runtime_error("missing value for "+option);
            const std::string value=argv[i];
            if(option=="--syntax") {if(value!="aesop") throw std::runtime_error("syntax must be aesop");override_syntax=value;}
            else {
                unsigned parsed=0;
                if(option=="-O"&&!(value.size()==1&&value[0]>='0'&&value[0]<='3')) throw std::runtime_error("optimization must be 0..3");
                if(option=="--build-timeout"&&!number(value,1,3600,parsed)) throw std::runtime_error("build timeout must be 1..3600");
                if(option=="--build-memory-mib"&&!number(value,512,16384,parsed)) throw std::runtime_error("build memory must be 512..16384 MiB");
                if(option=="-o") {if(value.empty()) throw std::runtime_error("empty output path");explicit_output=true;}
                flags.push_back(option);flags.push_back(value);
            }
        }
        fs::path source,output,manifest;std::string syntax="aesop";
        const bool single=!target.empty()&&path(target).extension()==".aw";
        if(single) {source=fs::canonical(path(target));if(!fs::is_regular_file(source)) throw std::runtime_error("source is not a regular .aw file");}
        else {const auto project=read_project(discover(cwd,target));source=project.entry;manifest=project.manifest;syntax=project.syntax;output=manifest.parent_path()/"build"/manifest.stem();}
        if(!override_syntax.empty()) syntax=override_syntax;
#if defined(_WIN32)
        if(!output.empty()) output+=".exe";
#endif
        if(!single&&!explicit_output) {
            // Protect manifest and source tree from output-directory symlink escapes.
            const auto parent=output.parent_path();
            if(fs::is_symlink(parent)|| (fs::exists(parent)&&!fs::is_directory(parent))) throw std::runtime_error("project build output directory must be a real directory, not a symlink");
            fs::create_directories(parent);flags.push_back("-o");flags.push_back(utf8(output));
        }
        // A user-specified output must never overwrite any .awproj manifest, even through a hardlink.
        if(explicit_output) {
            for(size_t f=0;f+1<flags.size();f+=2) if(flags[f]=="-o") {
                const auto dest=fs::absolute(path(flags[f+1]));
                if(dest.extension()==".awproj"||(!manifest.empty()&&(fs::weakly_canonical(dest)==manifest||(fs::exists(dest)&&fs::equivalent(dest,manifest))))) throw std::runtime_error("refusing to overwrite a .awproj project manifest");
                const auto parent=dest.parent_path();if(!fs::is_directory(parent)) throw std::runtime_error("output directory does not exist");
            }
        }
        std::vector<std::string> args={argv[0],"build",utf8(source),"--syntax",syntax};args.insert(args.end(),flags.begin(),flags.end());
        std::vector<char*> raw;for(auto &a:args) raw.push_back(a.data());raw.push_back(nullptr);
        return compiler(static_cast<int>(args.size()),raw.data());
    } catch(const std::exception &e) {std::cerr<<"Awl: "<<e.what()<<'\n';return 2;}
}
}
