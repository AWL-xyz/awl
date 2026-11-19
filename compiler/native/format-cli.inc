// Included inside Awl_toolkit. Formatting is explicitly per file, never
// recursive and never driven by a manifest or the import graph.
std::string formatter_stdin() {
    std::string input;
    char chunk[8192];
    while(std::cin.read(chunk,sizeof(chunk))||std::cin.gcount()) {
        const auto size=static_cast<size_t>(std::cin.gcount());
        if(size>Awl_package::source_limit-input.size()) throw std::runtime_error("formatter input exceeds 1 MiB");
        input.append(chunk,size);
    }
    if(std::cin.bad()||!std::cin.eof()) throw std::runtime_error("cannot read formatter input");
    return input;
}

#if !defined(_WIN32)
void replace_formatted(const fs::path &file,const std::string &before,const std::string &after) {
    const auto label=utf8(file);
    struct stat original{};
    if(lstat(file.c_str(),&original)!=0||!S_ISREG(original.st_mode))
        throw std::runtime_error("expected a regular non-symlink source: "+label);
    if(original.st_nlink!=1) throw std::runtime_error("refusing to format a hard-linked source: "+label);
    if(original.st_uid!=geteuid()||!(original.st_mode&S_IWUSR)||(original.st_mode&(S_ISUID|S_ISGID|S_ISVTX)))
        throw std::runtime_error("--write requires an owned, writable source with ordinary permission bits: "+label);

    struct Stage {
        std::string name;
        int fd;
        ~Stage() {if(fd>=0) close(fd);if(!name.empty()) unlink(name.c_str());}
    } stage{(file.parent_path()/".Awl-fmt-XXXXXX").string(),-1};
    stage.fd=mkstemp(stage.name.data());
    if(stage.fd<0) {stage.name.clear();throw std::runtime_error("cannot stage formatted source: "+label);}
    // mkstemp starts private. Write first, then copy the ordinary mode bits.
    if(!write_all(stage.fd,after)) throw std::runtime_error("cannot write staged source: "+label);
    struct stat metadata{};
    if(fstat(stage.fd,&metadata)!=0||(metadata.st_gid!=original.st_gid&&fchown(stage.fd,static_cast<uid_t>(-1),original.st_gid)!=0)||
       fchmod(stage.fd,original.st_mode&0777)!=0)
        throw std::runtime_error("cannot preserve source permissions: "+label);
    const bool closed=close(stage.fd)==0;stage.fd=-1;
    if(!closed) throw std::runtime_error("cannot close staged source: "+label);

    // Catch ordinary concurrent editor saves before replacing; this is not
    // a filesystem lock or protection against a hostile parent directory.
    if(Awl_package::read_file(file,Awl_package::source_limit)!=before)
        throw std::runtime_error("source changed while formatting: "+label);
    struct stat current{};
    if(lstat(file.c_str(),&current)!=0||current.st_dev!=original.st_dev||current.st_ino!=original.st_ino||
       current.st_nlink!=1||current.st_mode!=original.st_mode||current.st_uid!=original.st_uid||current.st_gid!=original.st_gid)
        throw std::runtime_error("source changed while formatting: "+label);
    fs::rename(stage.name,file);
    stage.name.clear();
}
#endif

int format_command(int argc,char **argv) {
    enum class Mode { Stdout, Check, Write };
    Mode mode=Mode::Stdout;
    bool options=true,json=false,seen_diagnostic=false;
    std::vector<std::string> files;
    for(int i=2;i<argc;++i) {
        const std::string arg=argv[i];
        if(options&&arg=="--") {options=false;continue;}
        if(options&&(arg=="--check"||arg=="--write")) {
            if(mode!=Mode::Stdout) throw std::runtime_error("specify --check or --write only once");
            mode=arg=="--check"?Mode::Check:Mode::Write;
        } else if(options&&arg=="--diagnostic-format") {
            if(seen_diagnostic||++i==argc) throw std::runtime_error("expected one --diagnostic-format text|json");
            const std::string value=argv[i];
            if(value!="text"&&value!="json") throw std::runtime_error("diagnostic format must be text or json");
            seen_diagnostic=true;json=value=="json";
        } else {
            if(options&&arg.starts_with('-')&&arg!="-") throw std::runtime_error("unknown fmt option: "+arg);
            if(arg!="-"&&path(arg).extension()!=".aw") throw std::runtime_error("fmt expects a .aw file or - for stdin");
            files.push_back(arg);
            if(files.size()>64) throw std::runtime_error("fmt accepts at most 64 files");
        }
    }
    if(files.empty()||(mode==Mode::Stdout&&files.size()!=1))
        throw std::runtime_error("usage: awl fmt [--check|--write] FILE.aw ... (one input for stdout)");
    const bool use_stdin=std::find(files.begin(),files.end(),"-")!=files.end();
    if(use_stdin&&(files.size()!=1||mode==Mode::Write)) throw std::runtime_error("stdin must be the only input and cannot be written in place");
#if defined(_WIN32)
    if(mode==Mode::Write) throw std::runtime_error("fmt --write is supported on Unix hosts only; use stdout or --check");
    if(use_stdin&&_setmode(_fileno(stdin),_O_BINARY)==-1) throw std::runtime_error("cannot set binary stdin");
    if(mode==Mode::Stdout&&_setmode(_fileno(stdout),_O_BINARY)==-1) throw std::runtime_error("cannot set binary stdout");
#endif
    int code=0;
    for(const auto &name:files) {
        fs::path file;
        if(!use_stdin) {
            const auto absolute=fs::absolute(path(name));
            file=fs::canonical(absolute.parent_path())/absolute.filename();
        }
        const auto text=use_stdin?formatter_stdin():Awl_package::read_file(file,Awl_package::source_limit);
        const auto result=Awl_format::source(text,use_stdin?"<stdin>":name,json);
        if(!result.diagnostic.empty()) {std::cerr<<result.diagnostic;code=1;continue;}
        if(mode==Mode::Stdout) {
            std::cout.write(result.source.data(),static_cast<std::streamsize>(result.source.size()));
        } else if(text!=result.source) {
            if(mode==Mode::Check) {std::cout<<"Would reformat "<<name<<'\n';code=1;}
#if !defined(_WIN32)
            else {replace_formatted(file,text,result.source);std::cout<<"Formatted "<<name<<'\n';}
#endif
        }
    }
    return (std::cout<<std::flush)?code:2;
}
