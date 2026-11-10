#include "parse.h"
#include "build.h"
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
namespace {
bool number(const std::string &text,unsigned low,unsigned high,unsigned &value) {
    if(text.empty()||text.size()>10) return false;
    unsigned result=0;
    for(char c:text) {
        if(c<'0'||c>'9') return false;
        const unsigned digit=c-'0';
        if(result>high/10||(result==high/10&&digit>high%10)) return false;
        result=result*10+digit;
    }
    if(result<low) return false;
    value=result;return true;
}
}

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif
int Awl_compiler_main(int argc,char **argv);
#include "ASDK.inc"
int Awl_main(int argc,char **argv) {
    const auto invoked=Awl_toolkit::utf8(Awl_toolkit::path(argv[0]).filename());
    if(invoked=="acc"||invoked=="acc.exe"||invoked=="kcc"||invoked=="kcc.exe") return Awl_compiler_main(argc,argv);
    return Awl_toolkit::run(argc,argv,Awl_compiler_main);
}
int Awl_compiler_main(int argc,char **argv) {
    if(argc==2&&std::string(argv[1])=="--version") {std::cout<<"Awl Compiler Collection (ACC) 0.26.0-dev development candidate\n";return 0;}
    if(argc<3) {
        std::cerr<<"Usage: acc check|emit-ast|emit-checked-ast|emit-c|build|run source.aw [-o FILE] [-O 0|1|2|3] [--diagnostic-format text|json] [--syntax aesop]\n"
                 <<"Build/run require the complete Linux or Windows x86-64 Awl bundle. Limits: --build-timeout 1..3600 (default 120s), --build-memory-mib 512..16384 (default 4096), --run-timeout 0..86400 (run only; default unlimited).\n";return 2;
    }
    const std::string command=argv[1],path=argv[2]; bool json=false;std::string output;Awl_driver::Options options;
    const bool building=command=="build"||command=="run";
    if(command!="check"&&command!="emit-ast"&&command!="emit-checked-ast"&&command!="emit-c"&&!building) {
        std::cerr<<"acc: command not implemented in native-checker preview: "<<command<<"\n";return 2;
    }
    for(int i=3;i<argc;++i) {
        const std::string option=argv[i];
        if(i+1>=argc) {std::cerr<<"acc: missing option value\n";return 2;}
        const std::string value=argv[++i];
        if(option=="--syntax"&&value=="aesop") {}
        else if(option=="--diagnostic-format"&&(value=="text"||value=="json")) json=value=="json";
        else if(option=="-o"&&command=="build") output=value;
        else if(option=="-O"&&building&&value.size()==1&&value[0]>='0'&&value[0]<='3') options.optimization=value[0]-'0';
        else if(option=="--build-timeout"&&building&&number(value,1,3600,options.build_timeout_seconds)) {}
        else if(option=="--build-memory-mib"&&building&&number(value,512,16384,options.build_memory_mib)) {}
        else if(option=="--run-timeout"&&command=="run"&&number(value,0,86400,options.run_timeout_seconds)) {}
        else {std::cerr<<"acc: invalid option or value\n";return 2;}
    }
    if(!path.ends_with(".aw")) {std::cerr<<"acc: Awl source files must use .aw\n";return 1;}
    void *unit=nullptr;
    if(Awl_parse_file(path.c_str(),&unit)||!unit) {std::cerr<<"acc: internal project parse failure\n";return 2;}
    struct Cleanup { void *p; ~Cleanup(){Awl_parse_free(p);} } cleanup{unit};
    if(!Awl_diagnostic_count(unit)&&command!="emit-ast") {
        const auto status=Awl_check_unit(unit);
        if(status==2) {std::cerr<<"acc: internal semantic failure\n";return 2;}
    }
    const char *c_output=nullptr;size_t c_size=0;
    bool verification_failed=false;
    if(!Awl_diagnostic_count(unit)&&command!="emit-ast") {
        const auto status=(command=="emit-c"||building)?Awl_emit_c(unit,&c_output,&c_size):Awl_verify_unit(unit);
        if(status==2) {std::cerr<<"acc: internal verification failure\n";return 2;}
        verification_failed=status!=0;
    }
    if(Awl_diagnostic_count(unit)) {
        size_t size=0; const auto *report=Awl_render_diagnostics(unit,path.c_str(),json,&size);
        if(!report) {std::cerr<<"acc: diagnostic rendering failed\n";return 2;}
        std::cerr.write(report,static_cast<std::streamsize>(size)); return verification_failed?2:1;
    }
    for(uint32_t i=0;i<Awl_source_file_count(unit);++i) {
        const auto *file=Awl_source_file_path(unit,i);
        if(!file) {std::cerr<<"acc: source enumeration failed\n";return 2;}
        options.protected_sources.emplace_back(file);
    }
    if(building) return Awl_driver::build(c_output,c_size,argv[0],path,output,options,command=="run");
    if(command=="check") std::cout<<path<<": checked (native frontend)\n";
    else if(command=="emit-c") std::cout.write(c_output,static_cast<std::streamsize>(c_size));
    else {
        size_t size=0; const auto *syntax=Awl_parse_json(unit,&size);
        if(!syntax) {std::cerr<<"acc: syntax export failed\n";return 2;}
        std::cout.write(syntax,static_cast<std::streamsize>(size)); std::cout<<'\n';
    }
    std::cout.flush();if(!std::cout) {std::cerr<<"acc: cannot write output\n";return 2;}
    return 0;
}

#if defined(_WIN32)
int wmain(int argc,wchar_t **argv) {
    std::vector<std::string> args;
    for(int i=0;i<argc;++i){int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr);if(!n){std::cerr<<"acc: invalid Unicode argument\n";return 2;}std::string s(n,'\0');WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,s.data(),n,nullptr,nullptr);s.resize(n-1);args.push_back(std::move(s));}
    std::vector<char*> av;for(auto &s:args) av.push_back(s.data());av.push_back(nullptr);return Awl_main(argc,av.data());
}
#else
int main(int argc,char **argv) {return Awl_main(argc,argv);}
#endif
