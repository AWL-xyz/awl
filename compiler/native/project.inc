// Native filesystem project loader and static namespace lowering. Included
// after parse_source; byte-source APIs intentionally remain filesystem-free.
// Aesop functions require explicit exports. No
// runtime initializers, wildcard imports, re-exports or binary separate objects.
// Public provenance paths are UTF-8 on Windows, not the active ANSI codepage.
static std::string project_path_text(const std::filesystem::path &path) {
    const auto text=path.generic_u8string();return std::string(reinterpret_cast<const char*>(text.data()),text.size());
}
struct ProjectAbort { size_t module; };
struct ProjectReadError:std::runtime_error {using std::runtime_error::runtime_error;};
class Project {
    using Path=std::filesystem::path;
    struct Definition { std::string name,kind,mode; };
    struct Module {
        Path path;
        std::unique_ptr<Unit> unit;
        std::unordered_map<std::string,size_t> aliases;
        std::unordered_map<std::string,Definition> definitions;
        unsigned state=1;
    };
    Path root;
    static constexpr bool aesop=true;
    std::vector<Module> modules;
    std::vector<uint32_t> module_order;
    size_t source_bytes=0,tokens=0,nodes=0,edges=0;
    [[noreturn]] void fail(size_t module,uint32_t token,const std::string &message,const std::string &code="E300") {
        modules.at(module).unit->diagnostics={{code,message,token}};
        throw ProjectAbort{module};
    }
    bool within(const Path &path) const {
        auto r=root.begin(),p=path.begin();
        for(;r!=root.end();++r,++p) if(p==path.end()||*r!=*p) return false;
        return true;
    }
    bool builtin(const std::string &name) const {return (aesop&&(generic_call(name)||view_call(name)||map_call(name)||set_call(name)||map_specialization(name)||set_specialization(name)||bool(new_container_type(name))))||name=="print"||name=="array_length"||name=="isnum"||platform_signatures.contains(name)||(aesop&&(name=="pi"||name=="tau"||math_signatures.contains(name)));}
    size_t load(const Path &requested,unsigned depth,size_t importer=SIZE_MAX,uint32_t token=0) {
        std::error_code ec;
        if(aesop) {
            const auto absolute=std::filesystem::absolute(requested).lexically_normal();auto current=absolute.root_path();
            for(const auto &part:absolute.relative_path()) {
                bool exact=false;
                if(std::filesystem::is_directory(current,ec)&&!ec) for(const auto &entry:std::filesystem::directory_iterator(current)) if(entry.path().filename()==part) {current=entry.path();exact=true;break;}
                if(!exact) {
                    if(importer!=SIZE_MAX) fail(importer,token,"missing or wrong-case use path: "+project_path_text(requested),"E300");
                    throw ProjectReadError("missing or wrong-case entry path: "+project_path_text(requested));
                }
            }
        }
        const auto path=std::filesystem::canonical(requested,ec);
        auto problem=[&](const std::string &message)->void {
            if(importer!=SIZE_MAX) fail(importer,token,message);
            throw ProjectReadError(message);
        };
        if(ec) problem("cannot resolve module source: "+project_path_text(requested));
        if(importer==SIZE_MAX) root=path.parent_path();
        if(!within(path)) problem("module source escapes project root: "+project_path_text(requested));
        if(depth>32) problem("module import depth exceeds 32");
        if(!std::filesystem::is_regular_file(path,ec)||ec) problem("module source is not a regular file: "+project_path_text(path));
        for(size_t i=0;i<modules.size();++i) {
            // Canonical aliases and hard links denote one module, including
            // cycles hidden behind alternate spellings or filesystem links.
            bool same=path==modules[i].path;
            if(!same) {same=std::filesystem::equivalent(path,modules[i].path,ec);if(ec) problem("cannot compare module source identity");}
            if(same) {
                if(modules[i].state==1) fail(importer,token,"cyclic module import: "+project_path_text(path),"E301");
                return i;
            }
        }
        if(modules.size()>=64) problem("module count exceeds 64");
        std::ifstream file(path,std::ios::binary);
        if(!file) problem("cannot read module source: "+project_path_text(path));
        std::string source(1048577,'\0');file.read(source.data(),static_cast<std::streamsize>(source.size()));source.resize(static_cast<size_t>(file.gcount()));
        if(file.bad()) problem("cannot read module source: "+project_path_text(path));
        file.close();
        auto unit=parse_source(source.data(),source.size());
        const auto id=modules.size();
        modules.push_back({path,std::move(unit),{},{},1});
        if(!modules[id].unit->diagnostics.empty()) throw ProjectAbort{id};
        source_bytes+=source.size();tokens+=modules[id].unit->tokens.size();nodes+=modules[id].unit->arena.size();
        if(source_bytes>1048576||tokens>100001||nodes>max_nodes) {
            if(importer!=SIZE_MAX) fail(importer,token,"aggregate project source/token/arena budget exceeded");
            fail(id,0,"aggregate project source/token/arena budget exceeded");
        }
        // Never hold a vector element/reference across recursive load: appends
        // may reallocate modules. Index-based access is intentional.
        const auto roots=modules[id].unit->roots;
        for(auto declaration:roots) {
            const auto node=modules[id].unit->arena.at(declaration);
            if(node.kind!="import") continue;
            if(++edges>256) fail(id,node.token,"module import edge count exceeds 256");
            if(builtin(node.second)) fail(id,node.token,"reserved import alias "+node.second,"E303");
            if(modules[id].aliases.contains(node.second)) fail(id,node.token,"duplicate import alias "+node.second,"E303");
            if(aesop) {
                Path target=modules[id].path.parent_path();
                std::string spelled=node.value;
                if(spelled.starts_with("pkg:")) {
                    // installed package: <root>/packages/NAME/NAME.awpkg names the entry, a missing package is an error, never a local-file fallback
                    const auto name=spelled.substr(4);const auto folder=root/"packages"/name;const auto manifest=folder/(name+".awpkg");
                    std::error_code manifest_error;
                    if(!std::filesystem::is_regular_file(manifest,manifest_error)||std::filesystem::is_symlink(manifest)) fail(id,node.token,"package '"+name+"' is not installed (expected packages/"+name+"/"+name+".awpkg)","E300");
                    std::ifstream in(manifest,std::ios::binary);std::string line,entry=name+".aw",kind,found_name;bool format_ok=false;size_t lines=0;
                    while(std::getline(in,line)&&++lines<=64) {
                        if(!line.empty()&&line.back()=='\r') line.pop_back();
                        const auto colon=line.find(": ");if(colon==std::string::npos) continue;
                        const auto key=line.substr(0,colon),value=line.substr(colon+2);
                        if(key=="format") format_ok=value=="1"; else if(key=="kind") kind=value; else if(key=="name") found_name=value; else if(key=="entry") entry=value;
                    }
                    if(!format_ok||kind!="package"||found_name!=name) fail(id,node.token,"package manifest packages/"+name+"/"+name+".awpkg must declare format: 1, kind: package and name: "+name,"E300");
                    if(entry.empty()||entry.size()>128||entry.find('/')!=std::string::npos||entry.find('\\')!=std::string::npos||entry.starts_with(".")||!entry.ends_with(".aw")) fail(id,node.token,"package entry must be a plain .aw file name","E300");
                    target=root;spelled="packages/"+name+"/"+entry;
                }
                const Path rel=Path(std::u8string(reinterpret_cast<const char8_t*>(spelled.c_str())));
                unsigned component_count=0;
                for(const auto &component:rel) {
                    if(++component_count>32) fail(id,node.token,"use path component budget exceeded","E300");
                    if(component=="."||component==".."||component.is_absolute()) fail(id,node.token,"use path must stay within project with explicit components","E300");
                    bool exact=false;std::error_code error;
                    if(std::filesystem::is_directory(target,error)&&!error) for(const auto &entry:std::filesystem::directory_iterator(target)) if(entry.path().filename()==component) {target=entry.path();exact=true;break;}
                    if(!exact) fail(id,node.token,"missing or wrong-case use component: "+project_path_text(component),"E300");
                }
                const auto target_id=load(target,depth+1,id,node.token);modules[id].aliases[node.second]=target_id;continue;
            }
        }
        modules[id].state=2;module_order.push_back(static_cast<uint32_t>(id));return id;
    }
    void collect() {
        for(size_t i=0;i<modules.size();++i) {
            auto &m=modules[i];size_t number=0;
            for(auto id:m.unit->roots) {
                const auto &d=m.unit->arena.at(id);
                if(d.kind=="import") continue;
                if(builtin(d.value)||m.definitions.contains(d.value)) fail(i,d.token,"duplicate/reserved declaration "+d.value,"E210");
                if(m.aliases.contains(d.value)) fail(i,d.token,"declaration conflicts with import alias "+d.value,"E303");
                const auto linked=i==0&&d.value=="main"?"main":"km_"+std::to_string(i)+"_"+std::to_string(number++);
                m.definitions.emplace(d.value,Definition{linked,d.kind,d.result_mode});
            }
        }
    }
    const Definition &definition(size_t module,const std::string &name,uint32_t token) {
        const auto dot=name.find('.');
        size_t owner=module;std::string member=name;
        if(dot!=std::string::npos) {
            const auto alias=name.substr(0,dot);member=name.substr(dot+1);
            if(!modules[module].aliases.contains(alias)) fail(module,token,"unknown module alias "+alias,"E302");
            owner=modules[module].aliases.at(alias);
        }
        const auto found=modules[owner].definitions.find(member);
        if(found==modules[owner].definitions.end()) fail(module,token,"unknown module declaration "+name,"E302");
        if(aesop&&owner!=module&&!modules[owner].unit->public_functions.contains(member)&&!(found->second.kind=="global"&&(found->second.mode=="r"||found->second.mode=="rw"))&&!((found->second.kind=="union"||found->second.kind=="struct")&&found->second.mode=="r")) fail(module,token,"module member is private/not exported: "+name,"E302");
        return found->second;
    }
    std::string type(size_t module,const std::string &name,uint32_t token) {
        if(auto a=array_type(name)) {const auto resolved=array_name(type(module,a->element,token),a->count);if(resolved.size()>128) fail(module,token,"resolved array type exceeds budget","E302");return resolved;}
        if(aesop&&name.empty()) return name;
        if((aesop&&(name=="f64"||generic_type(name)||view_type(name)||map_type(name)||set_type(name)))||name=="unit"||name=="bool"||name=="string"||name=="spool"||name=="int_vector"||integers.contains(name)) return name;
        const auto &d=definition(module,name,token);
        if(d.kind!="struct"&&d.kind!="union") fail(module,token,"declaration is not a type: "+name,"E302");
        return d.name;
    }
    void lower() {
        for(size_t i=0;i<modules.size();++i) {
            auto &m=modules[i];
            std::unordered_set<Id> roots(m.unit->roots.begin(),m.unit->roots.end());
            for(Id id=0;id<m.unit->arena.size();++id) {
                auto &n=m.unit->arena[id];const auto kind=n.kind;
                if(kind=="import") continue;
                const bool binding_kind=kind=="param"||kind=="borrow_param"||kind=="own_param"||kind=="mut_param"||kind=="local"||kind=="scoped_local";
                if((binding_kind||kind=="pattern_bind")&&m.aliases.contains(n.value)) fail(i,n.token,"local binding conflicts with import alias "+n.value,"E303");
                if(kind=="global"||kind=="function"||binding_kind||kind=="field_decl") n.second=type(i,n.second,n.token);
                if(kind=="call"&&!builtin(n.value)) {
                    const auto &d=definition(i,n.value,n.token);
                    if(d.kind=="global") fail(i,n.token,"module variable is not callable: "+n.value,"E302");
                    if(d.kind=="union") fail(i,n.token,"union construction requires a variant: "+n.value,"E302");
                    n.value=d.name;
                } else if(kind=="union_ctor") {
                    if(m.aliases.contains(n.value)) {
                        const auto &d=definition(i,n.value+"."+n.second,n.token);
                        if(d.kind=="global") fail(i,n.token,"module variable is not callable: "+n.value+"."+n.second,"E302");
                        if(d.kind=="union") fail(i,n.token,"union construction requires a variant: "+n.value+"."+n.second,"E302");
                        n.kind="call";n.value_kind="string";n.value=d.name;n.second.clear();
                    } else n.value=type(i,n.value,n.token);
                } else if(aesop&&kind=="field"&&n.children.size()==1) {
                    const auto &base=m.unit->arena.at(n.children[0]);
                    if(base.kind=="name"&&m.aliases.contains(base.value)) {
                        const auto &d=definition(i,base.value+"."+n.value,n.token);
                        if(d.kind!="global") fail(i,n.token,"module member is not a variable: "+base.value+"."+n.value,"E302");
                        n.kind="global_ref";n.value=d.name;n.children.clear();
                    }
                } else if(aesop&&kind=="store"&&m.unit->arena.at(n.children[0]).kind=="global_ref") {
                    n.value=m.unit->arena.at(n.children[0]).value;n.kind="global_assign";n.value_kind="string";n.children.erase(n.children.begin());
                } else if(kind=="case") n.value=type(i,n.value,n.token);
                if(roots.contains(id)) n.value=m.definitions.at(n.value).name;
            }
        }
    }
    void tag_failure(Unit &u,const Path &path) {
        u.files={project_path_text(path)};u.file_lengths={static_cast<uint32_t>(u.bytes.size()-1)};
        for(const auto &t:u.tokens) u.origins.push_back({0,t.start,t.end});
    }
    std::unique_ptr<Unit> merge() {
        auto result=std::make_unique<Unit>();result->project_syntax=true;result->aesop_syntax=true;
        result->module_order=module_order;result->module_dependencies.assign(modules.size(),{});std::vector<Id> node_bases;
        for(size_t i=0;i<modules.size();++i) {
            const auto &m=modules[i];const auto &u=*m.unit;
            const auto byte_base=result->source.size();const auto cp_base=static_cast<uint32_t>(result->bytes.size());
            const auto token_base=static_cast<uint32_t>(result->tokens.size());const auto node_base=static_cast<Id>(result->arena.size());
            node_bases.push_back(node_base);
            for(const auto &[alias,dependency]:m.aliases) { (void)alias;result->module_dependencies[i].push_back(static_cast<uint32_t>(dependency)); }
            for(const auto &[original,d]:m.definitions) if(d.kind=="global") result->global_names[static_cast<uint32_t>(i)][original]=d.name;
            result->files.push_back(project_path_text(m.path));result->file_lengths.push_back(static_cast<uint32_t>(u.bytes.size()-1));
            for(const auto &name:u.public_functions) result->public_functions.insert(m.definitions.at(name).name);
            for(const auto &[child,parent]:u.nested_parents) result->nested_parents[m.definitions.at(child).name]=m.definitions.at(parent).name;
            for(const auto &[original,d]:m.definitions) result->display_names[d.name]=i==0?original:project_path_text(m.path.lexically_relative(root))+":"+original;
            result->source+=u.source;result->source+='\n';
            for(auto offset:u.bytes) result->bytes.push_back(byte_base+offset);
            for(auto t:u.tokens) {
                result->origins.push_back({static_cast<uint32_t>(i),t.start,t.end});
                t.start+=cp_base;t.end+=cp_base;result->tokens.push_back(t);
            }
            for(auto node:u.arena) {
                node.token+=token_base;
                for(auto &child:node.children) child+=node_base;
                result->arena.push_back(std::move(node));
            }
            for(auto id:u.roots) if(u.arena[id].kind!="import") result->roots.push_back(id+node_base);
            for(auto id:u.mutable_arguments) result->mutable_arguments.insert(id+node_base);
            for(auto token:u.dotted_tokens) result->dotted_tokens.insert(token+token_base);
        }
        for(const auto i:module_order) for(const auto id:modules[i].unit->global_order) result->global_order.push_back(node_bases[i]+id);
        result->bytes.push_back(result->source.size());
        return result;
    }
public:
    std::unique_ptr<Unit> run(const Path &entry) {
        try {
            load(entry,1);
            if(modules.size()==1&&modules[0].aliases.empty()) {
                auto unit=std::move(modules[0].unit);unit->files={project_path_text(modules[0].path)};
                return unit; // Preserve the single-source language/JSON behavior.
            }
            if(source_bytes+modules.size()>1048576) fail(0,0,"aggregate project source budget including separators exceeded");
            collect();lower();return merge();
        } catch(const ProjectAbort &e) {
            auto &m=modules.at(e.module);auto unit=std::move(m.unit);tag_failure(*unit,m.path);return unit;
        }
    }
};
std::unique_ptr<Unit> parse_project(const char *path) {
    try {Project project;return project.run(std::filesystem::path(std::u8string(reinterpret_cast<const char8_t*>(path))));}
    catch(const std::filesystem::filesystem_error &e) {
        auto unit=parse_source("",0);unit->diagnostics={{"E300",e.what(),0}};return unit;
    } catch(const ProjectReadError &e) {
        auto unit=parse_source("",0);unit->diagnostics={{"E300",e.what(),0}};return unit;
    }
}
