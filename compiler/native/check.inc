// Included in parse.cpp's private implementation namespace. Native semantic
// analysis including restricted project lifetimes, not general ownership/borrowing.
struct Binding { std::string type,symbol; bool scoped=false,movable=false,moved=false,empty=false; };
using Env=std::unordered_map<std::string,Binding>;
struct Signature { std::vector<std::string> parameters; std::string result; std::vector<bool> borrows,takes,mutables; bool owns_result=false; };
class Checker {
    Unit &u;
    std::unordered_map<std::string,Id> aggregates,functions,globals;
    std::unordered_set<std::string> initialized_globals;
    uint32_t current_file=0;bool initializing_global=false;
    uint32_t file_of(const Node &node) const {return u.origins.empty()?0:u.origins.at(node.token).file;}
    std::string global_name(const std::string &source) const {
        if(u.global_names.contains(current_file)&&u.global_names.at(current_file).contains(source)) return u.global_names.at(current_file).at(source);
        return {};
    }
    Id global_access(Id use,const std::string &name,bool write=false) {
        if(!u.aesop_syntax||!globals.contains(name)) {
            std::vector<std::string> names;for(const auto &[candidate,id]:globals) names.push_back(candidate);
            error(use,"unknown module variable "+name+suggest(name,names),"E230");
        }
        const auto id=globals.at(name);const auto &g=n(id);
        if(file_of(g)!=current_file&&(g.result_mode=="p"||(write&&g.result_mode!="rw"))) error(use,write?"module variable is readonly/private to importer":"module variable is private/not exported","E231");
        if(!initialized_globals.contains(name)) error(use,"module initializer reads a not-yet-initialized variable "+name,"E230");
        return id;
    }
    std::unordered_map<std::string,Signature> signatures;
    std::unordered_map<std::string,std::pair<uint64_t,uint64_t>> sizes;
    std::unordered_map<std::string,uint32_t> heights;
    std::unordered_set<std::string> visiting;
    uint32_t serial=0,deferred_count=0,loop_depth=0;
    std::string result;bool owns_result=false,inferring_result=false;
    void infer_return(Id id,const std::string &ty) {
        if(owner_type(ty)) error(id,"resource results require an explicit [type] or [@o type] annotation","E233");
        if(result.empty()) result=ty;
        else if(result!=ty) error(id,"incompatible inferred return types: "+result+" and "+ty,"E233");
    }
    Node &n(Id id) { return u.arena.at(id); }
    const List &group(Id id) { return n(id).children; }
    [[noreturn]] void error(Id id,const std::string &msg,const std::string &code="E200") { throw Failure{{code,msg,n(id).token}}; }
    bool scalar(const std::string &ty) const { return ty=="bool"||ty=="string"||(u.aesop_syntax&&ty=="f64")||integers.contains(ty); }
    void literal_context(Id id,const std::string &expected) {
        auto &v=n(id);if(u.aesop_syntax&&expected=="f64"&&v.kind=="unary"&&v.value=="-") {literal_context(v.children.at(0),expected);if(n(v.children.at(0)).type=="f64") v.type="f64";return;}
        if(!u.aesop_syntax||expected!="f64"||v.kind!="int"||v.literal!="i64") return;
        const auto token=u.text(v.token);bool plain=!token.empty()&&token.find_first_not_of("0123456789")==std::string::npos;
        if(token=="-"&&v.token+1<u.tokens.size()) {const auto next=u.text(v.token+1);plain=!next.empty()&&next.find_first_not_of("0123456789")==std::string::npos;}
        if(!plain) return;
        v.kind="float";v.value_kind="string";v.value+=".0";v.literal.clear();v.type="f64";
    }
    // a struct holding any owner field is itself an owner: @s-only, moved never copied, freed field by field
    bool resource_struct(const std::string &ty,uint32_t depth=0) const {
        if(!u.aesop_syntax||depth>64||!aggregates.contains(ty)||u.arena.at(aggregates.at(ty)).kind!="struct") return false;
        for(auto f:u.arena.at(aggregates.at(ty)).children) {const auto &t=u.arena.at(f).second;if((u.aesop_syntax&&(generic_type(t)||map_type(t)||set_type(t)))||t=="spool"||resource_struct(t,depth+1)) return true;}
        return false;
    }
    bool owner_type(const std::string &ty) const {return resource_struct(ty)||(u.aesop_syntax&&(generic_type(ty)||map_type(ty)||set_type(ty)))||ty=="spool"||(u.project_syntax&&ty=="int_vector");}
    bool value_type(const std::string &ty,uint32_t depth=0) const {if(depth>64) return false;if(auto a=array_type(ty)) return value_type(a->element,depth+1)&&!resource_struct(a->element);return scalar(ty)||owner_type(ty)||(u.aesop_syntax&&view_type(ty))||aggregates.contains(ty); }
    void valid_type(Id id,const std::string &ty,bool unit=false) { if(!value_type(ty)&&!(unit&&ty=="unit")) error(id,"unknown or invalid value type "+ty);if(array_type(ty)) layout(ty,1,id); }
    void require(Id id,const std::string &got,const std::string &want) { if(got!=want) error(id,"expected "+want+", found "+got); }
    std::string fresh() { return "k_v"+std::to_string(++serial); }
    static bool exceeds(const std::string &a,const std::string &b) { return a.size()!=b.size()?a.size()>b.size():a>b; }
    static std::string maximum(const std::string &ty) {
        static const std::unordered_map<std::string,std::string> values={{"i8","127"},{"i16","32767"},{"i32","2147483647"},{"i64","9223372036854775807"},{"u8","255"},{"u16","65535"},{"u32","4294967295"},{"u64","18446744073709551615"}};
        return values.at(ty);
    }
    static size_t distance(const std::string &a,const std::string &b) {
        std::vector<size_t> previous(b.size()+1),current(b.size()+1);
        for(size_t j=0;j<=b.size();++j) previous[j]=j;
        for(size_t i=1;i<=a.size();++i) {
            current[0]=i;
            for(size_t j=1;j<=b.size();++j) {
                const size_t cost=a[i-1]==b[j-1]?0:1;
                current[j]=std::min({previous[j]+1,current[j-1]+1,previous[j-1]+cost});
            }
            previous=current;
        }
        return previous[b.size()];
    }
    static std::string suggest(const std::string &name,std::vector<std::string> candidates) {
        std::sort(candidates.begin(),candidates.end());
        std::string best;size_t best_distance=3;
        for(const auto &candidate:candidates) {
            if(candidate==name) continue;
            const auto score=distance(name,candidate);
            if(score<best_distance||(score==best_distance&&candidate<best)) {best=candidate;best_distance=score;}
        }
        return best.empty()?"":", did you mean '"+best+"'?";
    }
    static std::string types(const std::vector<std::string> &items) {
        std::string out="[";
        for(size_t i=0;i<items.size();++i) { if(i) out+=", "; out+="'"+items[i]+"'"; }
        return out+"]";
    }
    std::pair<uint64_t,uint64_t> fields_layout(const List &fields,uint32_t depth,Id parent,uint32_t &height) {
        if(fields.size()>128) error(parent,"aggregate exceeds 128 fields","E210");
        std::unordered_set<std::string> seen; uint64_t offset=0,align=1;
        for(auto id:fields) {
            const auto &f=n(id);
            if(!seen.insert(f.value).second) error(id,"duplicate field "+f.value,"E210");
            if(!value_type(f.second)) error(id,"invalid field type "+f.second,"E210");
            if(u.aesop_syntax&&n(parent).kind=="union"&&(owner_type(f.second)||resource_struct(f.second))) error(id,"enum payload requires a scalar or enum value, not an owned resource/array","E210");
            if(u.aesop_syntax&&!scalar(f.second)&&!aggregates.contains(f.second)&&!(n(parent).kind=="struct"&&owner_type(f.second))) error(id,"enum payload requires a scalar or enum value, not an owned resource/array","E210");
            const auto [size,alignment]=layout(f.second,depth+1,id);
            height=std::max(height,heights.at(f.second)+1);
            if(height>64) error(parent,"aggregate nesting limit exceeded","E210");
            offset=(offset+alignment-1)/alignment*alignment+size; align=std::max(align,alignment);
            if(offset>1048576) error(parent,"aggregate value exceeds size budget","E210");
        }
        return {(offset+align-1)/align*align,align};
    }
    std::pair<uint64_t,uint64_t> layout(const std::string &ty,uint32_t depth,Id origin=0) {
        if(sizes.contains(ty)) return sizes.at(ty);
        if(u.aesop_syntax&&(generic_type(ty)||map_type(ty)||set_type(ty)||ty=="spool")) {heights[ty]=0;return sizes[ty]={16,8};}
        if(auto a=array_type(ty)) {
            if(depth>64) error(origin,"array nesting exceeds budget","E210");
            const auto element=layout(a->element,depth+1,origin);
            if(element.first>1048576/a->count||heights.at(a->element)>=64) error(origin,"array value exceeds layout budget","E210");
            heights[ty]=heights.at(a->element)+1;return sizes[ty]={element.first*a->count,element.second};
        }
        const auto id=aggregates.at(ty); const auto &d=n(id);
        if(visiting.contains(ty)) error(id,"recursive value layout is not permitted","E210");
        if(depth>64) error(id,"aggregate nesting limit exceeded","E210");
        visiting.insert(ty); uint64_t size=0,align=1; uint32_t height=0;
        if(d.kind=="struct") {
            if(d.children.empty()) error(id,"empty structs are not supported","E210");
            const auto value=fields_layout(d.children,depth,id,height); size=value.first; align=value.second;
        } else {
            if(d.children.empty()) error(id,"empty unions are not supported","E210");
            if(d.children.size()>128) error(id,"union exceeds 128 variants","E210");
            uint64_t payload=1; height=1; std::unordered_set<std::string> variants;
            for(auto variant:d.children) {
                const auto &v=n(variant);
                if(!variants.insert(v.value).second) error(variant,"duplicate variant "+v.value,"E210");
                const auto [vs,va]=fields_layout(v.children,depth,id,height);
                payload=std::max(payload,vs); align=std::max(align,va);
            }
            size=(4+align-1)/align*align+payload; align=std::max<uint64_t>(4,align); size=(size+align-1)/align*align;
        }
        if(size>1048576) error(id,"aggregate value exceeds size budget","E210");
        visiting.erase(ty); sizes[ty]={size,align}; heights[ty]=height; return sizes.at(ty);
    }
    const List *structure_fields(const std::string &ty) {
        if(!aggregates.contains(ty)||n(aggregates.at(ty)).kind!="struct") return nullptr;
        return &n(aggregates.at(ty)).children;
    }
    // structs compare field-wise, only scalar and nested comparable struct fields qualify
    bool comparable_struct(const std::string &ty,uint32_t depth=0) {
        const auto *fields=structure_fields(ty);
        if(!fields||depth>64) return false;
        for(auto f:*fields) {const auto &t=n(f).second;if(!scalar(t)&&!comparable_struct(t,depth+1)) return false;}
        return true;
    }
    Id variant(const std::string &ty,const std::string &name) {
        if(!aggregates.contains(ty)||n(aggregates.at(ty)).kind!="union") return UINT32_MAX;
        for(auto v:n(aggregates.at(ty)).children) if(n(v).value==name) return v;
        return UINT32_MAX;
    }
    bool tagged(const std::string &ty) { return aggregates.contains(ty)&&n(aggregates.at(ty)).kind=="union"; }
    std::string field(Id id,const std::string &base) {
        const auto *fields=structure_fields(base);
        if(fields) for(auto f:*fields) if(n(f).value==n(id).value) return n(f).second;
        std::vector<std::string> names;
        if(const auto *fields=structure_fields(base)) for(auto f:*fields) names.push_back(n(f).value);
        else if(tagged(base)) for(auto v:n(aggregates.at(base)).children) names.push_back(n(v).value);
        error(id,"unknown field "+n(id).value+" on "+base+suggest(n(id).value,names));
    }
    std::string root_name(Id id) {
        if(n(id).kind=="name") return n(id).value;
        for(auto it=n(id).children.rbegin();it!=n(id).children.rend();++it) if(n(*it).kind!="index") return root_name(*it);
        return root_name(n(id).children.at(0));
    }
    std::string place(Id id,Env &env) {
        auto &node=n(id);
        if(node.kind=="name") return expression(id,env,true);
        if(node.kind=="field") { node.type=field(id,place(node.children.at(0),env)); return node.type; }
        if(node.kind=="index") {
            const auto base=place(node.children.at(0),env);const auto a=array_type(base);
            if(!a) error(id,"index requires an array");
            require(id,expression(node.children.at(1),env),"i64");node.type=a->element;return node.type;
        }
        error(id,"field assignment requires a local-rooted place");
    }
    std::vector<std::string> arguments(Id id,Env &env) {
        std::vector<std::string> args;
        for(auto child:n(id).children) args.push_back(expression(child,env));
        return args;
    }
    std::vector<std::string> field_types(const List &fields) {
        std::vector<std::string> result;
        for(auto f:fields) result.push_back(n(f).second);
        return result;
    }
    std::string expression(Id id,Env &env,bool borrow=false,const std::unordered_set<std::string> *transfer_scope=nullptr,bool adopt=false) {
        auto &node=n(id); std::string ty;
        if(node.kind=="unit") {if(node.type!="unit") error(id,"invalid unit expression");return "unit";}
        if(node.kind=="name"&&!env.contains(node.value)) {const auto target=global_name(node.value);if(!target.empty()) {node.kind="global_ref";node.value=target;}}
        const auto kind=node.kind;
        if(initializing_global&&kind!="name"&&kind!="global_ref"&&kind!="float"&&kind!="int"&&kind!="uint"&&kind!="bool"&&kind!="string"&&kind!="unary"&&kind!="binary"&&kind!="convert"&&kind!="format"&&kind!="concat"&&kind!="type_test"&&!(kind=="call"&&math_signatures.contains(node.value))) error(id,"module initializers currently permit scalar literals, earlier module variables and pure arithmetic/math only","E230");
        if(kind=="array_repeat") {
            const auto count=array_type("[i64;"+node.value+"]");
            if(!u.project_syntax||node.children.size()!=1||!count) error(id,"invalid repeated array");
            const auto element=expression(node.children[0],env);if(!value_type(element)) error(id,"invalid array element type");
            ty=array_name(element,count->count);valid_type(id,ty);
        } else if(kind=="array") {
            if(!u.project_syntax||node.children.empty()||node.children.size()>1024) error(id,"invalid array literal");
            const auto element=expression(node.children[0],env);if(!value_type(element)) error(id,"invalid array element type");
            for(size_t i=1;i<node.children.size();++i) require(id,expression(node.children[i],env),element);
            ty=array_name(element,node.children.size());valid_type(id,ty);
        } else if(kind=="index") {
            const auto a=array_type(expression(node.children.at(0),env));if(!a) error(id,"index requires an array");
            require(id,expression(node.children.at(1),env),"i64");ty=a->element;
        } else if(kind=="float") {if(!u.aesop_syntax||!finite_decimal(node.value)) error(id,"invalid f64 literal");ty="f64";
        } else if(kind=="int"||kind=="uint") {
            ty=node.literal;
            if(!integers.contains(ty)||(kind=="int")!=(ty[0]=='i')) error(id,"invalid integer literal type");
            const bool negative=node.value.starts_with("-"); const auto magnitude=negative?node.value.substr(1):node.value;
            if((negative&&ty[0]!='i')||exceeds(magnitude,negative?minimum_magnitude(ty):maximum(ty))) error(id,"integer literal outside "+ty+" range");
        } else if(kind=="format") {if(!u.aesop_syntax||node.children.size()!=1||!scalar(expression(node.children[0],env)))error(id,"string injection requires a scalar value");ty="string";
        } else if(kind=="concat") {if(!u.aesop_syntax||node.children.size()!=2)error(id,"invalid concatenation");require(id,expression(node.children[0],env),"string");require(id,expression(node.children[1],env),"string");ty="string";
        } else if(kind=="convert") {
            const auto numeric=integers.contains(node.value)||(u.aesop_syntax&&node.value=="f64");
            if(!numeric||node.children.size()!=1) error(id,"numeric conversion expects exactly one argument with a numeric target");
            const auto src=expression(node.children[0],env);
            if(!(integers.contains(src)||(u.aesop_syntax&&src=="f64"))) error(id,"numeric conversion requires a numeric value");
            ty=node.value;
        } else if(kind=="type_test") {
            if(node.children.size()!=1||!(node.value=="numeric"||integers.contains(node.value)||node.value=="f64"||node.value=="bool"||node.value=="string"||node.value=="unit")) error(id,"invalid type test");
            expression(node.children[0],env);ty="bool";
        } else if(kind=="string") {size_t count=0;if(node.value.size()>65536||!text_scalars(node.value,count)) error(id,"invalid UTF-8 string literal","E102");ty="string";}
        else if(kind=="bool") ty="bool";
        else if(kind=="field") ty=field(id,expression(node.children.at(0),env,true));
        else if(kind=="global_ref") {const auto &g=n(global_access(id,node.value));ty=g.second;node.symbol=g.symbol;}
        else if(kind=="name") {
            if(!env.contains(node.value)) {std::vector<std::string> names;for(const auto &[candidate,binding]:env) names.push_back(candidate);error(id,"unknown local "+node.value+suggest(node.value,names));}
            if(env.at(node.value).moved) error(id,std::string(generic_type(env.at(node.value).type)?"use of moved vector ":"use of moved builder ")+node.value,"E221");
            if(env.at(node.value).scoped&&!borrow) error(id,generic_type(env.at(node.value).type)?"restricted vector cannot be copied, released or escape; use supported borrows":"restricted builder cannot be copied, released or escape; use supported borrows","E220");
            ty=env.at(node.value).type; node.symbol=env.at(node.value).symbol;
        } else if(kind=="move") error(id,"move is only valid as a scoped initializer","E221");
        else if(kind=="union_ctor") {
            if(!tagged(node.value)) error(id,"unknown union "+node.value);
            const auto v=variant(node.value,node.second);
            if(v==UINT32_MAX) {
                std::vector<std::string> names;for(auto candidate:n(aggregates.at(node.value)).children) names.push_back(n(candidate).value);
                error(id,"unknown variant "+node.value+"."+node.second+suggest(node.second,names));
            }
            const auto expected=field_types(n(v).children);
            if(u.aesop_syntax) for(size_t i=0;i<node.children.size()&&i<expected.size();++i) literal_context(node.children[i],expected[i]);
            const auto args=arguments(id,env);
            if(args!=expected) error(id,"variant argument types "+types(args)+" do not match "+types(expected));
            ty=node.value;
        } else if(kind=="call") {
            if(u.aesop_syntax&&!u.dotted_tokens.contains(node.token)&&!signatures.contains(node.value)&&builtin_internal_name(node.value)) {
                const auto hint=builtin_surface_call(node.value);
                error(id,"call builtins as namespace.method"+(hint.empty()?"":", use "+hint+"(...)"),"E102");
            }
            if((generic_call(node.value)||generic_specialization(node.value)||view_call(node.value)||view_specialization(node.value))&&!u.aesop_syntax) error(id,"generic vectors require Aesop syntax");
            std::optional<std::pair<std::string,std::pair<std::vector<std::string>,std::string>>> resolved;
            if(map_call(node.value)||set_call(node.value)) {
                if(node.children.empty()) error(id,node.value+" requires a container argument","E228");
                const auto &first=n(node.children[0]);std::string container;
                if(first.kind=="name"&&env.contains(first.value)) container=env.at(first.value).type;
                else if(first.kind=="global_ref"&&globals.contains(first.value)) container=n(globals.at(first.value)).second;
                else if(u.aesop_syntax&&first.kind=="field") container=expression(node.children[0],env,true);
                resolved=map_resolve(node.value,container);
                if(!resolved) error(id,node.value+" requires a map<K,V> or set<T> local container as its first argument","E228");
                node.value=resolved->first;
            }
            if(node.value.starts_with("int_vector_")&&!u.project_syntax) error(id,"integer vectors require native project syntax");
            if(u.aesop_syntax&&!signatures.contains(node.value)&&resource_struct(node.value)&&!adopt) error(id,"a struct holding owned resources must initialize a scoped binding or be forwarded as an owned return","E223");
            if(signatures.contains(node.value)&&signatures.at(node.value).owns_result&&!adopt) error(id,"owned result must initialize a scoped binding or be forwarded as an owned return","E223");
            static const std::unordered_set<std::string> borrowing={"spool_valid","spool_reserve","spool_truncate","spool_clear","spool_capacity","spool_bytes","spool_length","spool_append","spool_codepoint","spool_i64","spool_u64","spool_print","spool_snapshot","int_vector_valid","int_vector_length","int_vector_capacity","int_vector_reserve","int_vector_push","int_vector_pop","int_vector_get","int_vector_set","int_vector_clear","int_vector_insert","int_vector_remove"};
            std::vector<std::string> args;std::unordered_set<std::string> lent,taken;
            for(size_t i=0;i<node.children.size();++i) {
                if(u.aesop_syntax&&i==static_cast<size_t>(generic_value_argument(node.value))&&!args.empty()&&generic_type(args[0])) literal_context(node.children[i],*generic_type(args[0]));
                if(u.aesop_syntax&&math_signatures.contains(node.value)&&i<math_signatures.at(node.value).parameters.size()) literal_context(node.children[i],math_signatures.at(node.value).parameters[i]);
                else if(signatures.contains(node.value)&&i<signatures.at(node.value).parameters.size()) literal_context(node.children[i],signatures.at(node.value).parameters[i]);
                const bool user_borrow=signatures.contains(node.value)&&i<signatures.at(node.value).borrows.size()&&signatures.at(node.value).borrows[i];
                const auto *ctor_fields=u.aesop_syntax&&!signatures.contains(node.value)?structure_fields(node.value):nullptr;
                const bool taking=(signatures.contains(node.value)&&i<signatures.at(node.value).takes.size()&&signatures.at(node.value).takes[i])||(ctor_fields&&resource_struct(node.value)&&i<ctor_fields->size()&&owner_type(n((*ctor_fields)[i]).second));
                const bool mutating=signatures.contains(node.value)&&i<signatures.at(node.value).mutables.size()&&signatures.at(node.value).mutables[i];
                auto &arg=n(node.children[i]);
                if(mutating) {
                    const auto kind=n(node.children[i]).kind;
                    if(kind!="name"&&kind!="field"&&kind!="index") error(id,"@m arguments must be an existing local, field or element, found a temporary value","E229");
                    const auto ty=place(node.children[i],env);
                    if(ty!=signatures.at(node.value).parameters[i]) error(id,"@m argument is "+ty+", the parameter expects "+signatures.at(node.value).parameters[i],"E229");
                    const auto symbol=env.at(root_name(node.children[i])).symbol;
                    if(lent.contains(symbol)) error(id,"one local cannot be borrowed twice in a single call","E229");
                    lent.insert(symbol);
                    u.mutable_arguments.insert(node.children[i]);
                    args.push_back(ty);
                } else if(taking) {
                    if(!transfer_scope||arg.kind!="move"||arg.children.size()!=1||n(arg.children[0]).kind!="name") error(id,"own arguments require explicit same-block move in a direct call","E222");
                    const auto &name=n(arg.children[0]).value;
                    if(!env.contains(name)||!env.at(name).movable||!transfer_scope->contains(name)) error(id,"own argument requires a same-block scoped owner","E222");
                    args.push_back(expression(arg.children[0],env,true));arg.type=args.back();taken.insert(env.at(name).symbol);env.at(name).moved=true;env.at(name).empty=true;
                } else {
                    const bool lending=(i==0&&(borrowing.contains(node.value)||generic_borrow(node.value)||container_borrow(node.value)))||user_borrow||(node.value=="process_capture"&&(i==2||i==3));
                    args.push_back(expression(node.children[i],env,lending));
                    if(lending&&arg.kind=="name"&&env.contains(arg.value)) lent.insert(env.at(arg.value).symbol);
                }
            }
            if(generic_call(node.value)) {
                if(node.value=="vector_new") error(id,"vector_new requires an explicit <element> type");
                if(args.empty()||!generic_type(args[0])) error(id,"vector operation requires a typed vector as its first argument");
                node.value+="_"+*generic_type(args[0]);
            }
            if(view_call(node.value)) {
                if(args.empty()||!view_type(args[0])) error(id,"view operation requires a typed view as its first argument");
                node.value+="_"+*view_type(args[0]);
            }
            for(const auto &symbol:taken) if(lent.contains(symbol)) error(id,"one call cannot borrow and consume the same owner","E222");
            if(node.value=="print") {
                if(args.size()!=1||!scalar(args[0])) error(id,u.project_syntax?"print expects one integer, bool or string":"print expects one integer or bool");
                ty="unit";
            } else if(node.value=="array_length") {
                if(args.size()!=1||!array_type(args[0])) error(id,"array_length expects one array");
                ty="i64";
            } else if(u.aesop_syntax&&math_signatures.contains(node.value)) {
                const auto &sig=math_signatures.at(node.value);if(args!=sig.parameters) error(id,"invalid math arguments for "+node.value+": expected "+types(sig.parameters));ty=sig.result;
            } else if(auto container=new_container_type(node.value)) {
                if(args.size()!=1) error(id,node.value+" expects one capacity argument","E228");
                require(id,args[0],"i64");ty=*container;
            } else if(resolved) {
                const auto &expected=resolved->second.first;
                if(args.size()!=expected.size()) error(id,node.value+" expects "+std::to_string(expected.size()-1)+" argument(s) after the container");
                for(size_t i=1;i<expected.size();++i) if(args[i]!=expected[i]) error(id,"argument "+std::to_string(i+1)+" of "+node.value+" is "+args[i]+", expected "+expected[i],"E228");
                ty=resolved->second.second;
            } else if(platform_signatures.contains(node.value)) {
                const auto &sig=platform_signatures.at(node.value);
                if(args!=sig.parameters) error(id,"invalid platform arguments for "+node.value+": expected "+types(sig.parameters));
                ty=sig.result;
            } else if(const auto *fields=structure_fields(node.value)) {
                const auto expected=field_types(*fields);
                if(args!=expected) error(id,"constructor argument types "+types(args)+" do not match "+types(expected));
                ty=node.value;
            } else {
                if(!signatures.contains(node.value)) {
                    std::vector<std::string> names;for(const auto &[name,signature]:signatures) {if(name.empty()||name.starts_with("km_")) continue;names.push_back(name);}
                    error(id,"unknown function "+node.value+suggest(node.value,names));
                }
                const auto &sig=signatures.at(node.value);
                if(args!=sig.parameters) error(id,"argument types "+types(args)+" do not match "+types(sig.parameters));
                ty=sig.result;
            }
        } else if(kind=="unary") {
            ty=expression(node.children.at(0),env);
            if(node.value=="not") require(id,ty,"bool");
            else if(!(u.aesop_syntax&&ty=="f64")&&(!integers.contains(ty)||ty[0]!='i')) error(id,"unary minus requires a signed integer, found "+ty);
        } else if(kind=="binary") {
            auto a=expression(node.children.at(0),env); auto b=expression(node.children.at(1),env); const auto &op=node.value;
            if(a=="f64") {literal_context(node.children[1],"f64");b=n(node.children[1]).type;}
            if(b=="f64") {literal_context(node.children[0],"f64");a=n(node.children[0]).type;}
            if(op=="and"||op=="or") { require(id,a,"bool"); require(id,b,"bool"); ty="bool"; }
            else if(op=="=="||op=="!=") { if(a!=b||!(scalar(a)||(u.aesop_syntax&&comparable_struct(a)))) error(id,"equality requires matching scalar types or structs of scalars"); ty="bool"; }
            else if(op=="+"&&a=="string"&&b=="string") ty="string";
            else {
                if((!integers.contains(a)&&!(u.aesop_syntax&&a=="f64"))||a!=b||(a=="f64"&&op=="%")) {
                    const bool mixed=(integers.contains(a)&&b=="f64")||(a=="f64"&&integers.contains(b));
                    error(id,std::string("arithmetic/comparison requires matching numeric types")+(mixed?", use f64.convert(...) or an integer.convert(...) explicitly":""));
                }
                ty=(op=="<"||op==">"||op=="<="||op==">=")?"bool":a;
            }
        } else error(id,"invalid expression");
        node.type=ty; return ty;
    }
    bool match(Id id,Env &env,const std::unordered_set<std::string> &eligible) {
        const auto &node=n(id); const auto ty=expression(node.children[0],env);
        if(!tagged(ty)) error(id,"match requires a tagged union value");
        std::unordered_set<std::string> seen,continuing_moves,all_empty; bool total=true,first_continuing=true;
        for(auto arm_id:group(node.children[1])) {
            const auto &arm=n(arm_id);
            if(arm.value!=ty) error(arm_id,"case type "+arm.value+" does not match "+ty);
            const auto v=variant(ty,arm.second);
            if(v==UINT32_MAX) {
                std::vector<std::string> names;for(auto candidate:n(aggregates.at(ty)).children) names.push_back(n(candidate).value);
                error(arm_id,"unknown variant "+ty+"."+arm.second+suggest(arm.second,names));
            }
            if(!seen.insert(arm.second).second) error(arm_id,"duplicate case "+ty+"."+arm.second);
            const auto &binders=group(arm.children[0]); const auto &fields=n(v).children;
            if(binders.size()!=fields.size()) error(arm_id,"pattern payload count does not match variant");
            auto branch=env; std::unordered_set<std::string> names,pattern_moved,pattern_empty;
            for(size_t i=0;i<binders.size();++i) {
                auto &b=n(binders[i]); b.type=n(fields[i]).second;
                if(b.value=="_") continue;
                if(!names.insert(b.value).second) error(binders[i],"duplicate pattern binding "+b.value);
                if(branch.contains(b.value)) {if(branch.at(b.value).moved) pattern_moved.insert(branch.at(b.value).symbol);if(branch.at(b.value).empty) pattern_empty.insert(branch.at(b.value).symbol);}
                b.symbol=fresh(); branch[b.value]={b.type,b.symbol};
            }
            std::unordered_set<std::string> arm_moves,arm_empty;
            const auto arm_total=block(group(arm.children[1]),branch,false,&eligible,&arm_moves,&arm_empty);
            if(!arm_total) {
                arm_moves.insert(pattern_moved.begin(),pattern_moved.end());arm_empty.insert(pattern_empty.begin(),pattern_empty.end());
                continuing_moves.insert(arm_moves.begin(),arm_moves.end());
                if(first_continuing) {all_empty=arm_empty;first_continuing=false;}
                else for(auto it=all_empty.begin();it!=all_empty.end();) {if(!arm_empty.contains(*it)) it=all_empty.erase(it);else ++it;}
            }
            total=total&&arm_total;
        }
        std::vector<std::string> missing;
        for(auto v:n(aggregates.at(ty)).children) if(!seen.contains(n(v).value)) missing.push_back(n(v).value);
        if(!missing.empty()) {
            std::sort(missing.begin(),missing.end()); std::string msg="non-exhaustive match; missing: ";
            for(size_t i=0;i<missing.size();++i) { if(i) msg+=", "; msg+=missing[i]; }
            error(id,msg);
        }
        for(auto &[name,binding]:env) if(!total) {binding.moved=continuing_moves.contains(binding.symbol);binding.empty=all_empty.contains(binding.symbol);}
        return total;
    }
    bool block(const List &statements,const Env &outer,bool entry=false,const std::unordered_set<std::string> *incoming=nullptr,std::unordered_set<std::string> *out_moves=nullptr,std::unordered_set<std::string> *out_empty=nullptr) {
        auto env=outer; std::unordered_set<std::string> eligible=incoming?*incoming:std::unordered_set<std::string>{},consumed,hidden_empty,declared; bool returns=false;size_t deferred_scope=0;
        if(entry) for(const auto &[name,binding]:env) if(binding.movable) {
            declared.insert(name);eligible.insert(name);if(++deferred_scope>64||++deferred_count>256) throw Failure{{"E210","own parameter cleanup budget exceeded",UINT32_MAX}};
        }
        for(auto id:statements) {
            auto &node=n(id); const auto &kind=node.kind;
            if(returns) error(id,"unreachable statement");
            if(kind=="local"||kind=="scoped_local") {
                const bool owned=kind=="scoped_local";
                if(owned) {
                    const auto &init=n(node.children.at(0));
                    if(!u.project_syntax||!owner_type(node.second)||(init.kind!="move"&&(init.kind!="call"||(init.value!=node.second+"_new"&&!(init.value==node.second&&resource_struct(node.second))&&!generic_fresh(init.value,node.second)&&!container_fresh(init.value,node.second)&&(!signatures.contains(init.value)||!signatures.at(init.value).owns_result))))) error(id,"scoped requires a supported fresh resource, owned result or move","E220");
                    if(++deferred_scope>64||++deferred_count>256) error(id,"cleanup budget exceeded (64 per scope, 256 per project)","E210");
                }
                if(declared.contains(node.value)) error(id,"duplicate local "+node.value);
                if(node.second=="unit") error(id,"unit locals are not permitted");
                const bool inferred=u.aesop_syntax&&node.second.empty();
                if(!inferred) literal_context(node.children.at(0),node.second);
                if(inferred) {
                    if(owned) error(id,"@p scoped currently requires an explicit resource type","E220");
                    node.second=expression(node.children.at(0),env,false,&eligible);
                    if(owner_type(node.second)) error(id,"inferred resources require explicit @p scoped ownership","E220");
                }
                valid_type(id,node.second);
                auto &init=n(node.children.at(0));
                if(owned&&init.kind=="move") {
                    if(init.children.size()!=1||n(init.children[0]).kind!="name") error(id,"move requires one scoped name","E221");
                    const auto &name=n(init.children[0]).value;
                    if(!env.contains(name)||!env.at(name).movable||!eligible.contains(name)) error(id,"move requires an eligible owner outside loop barriers","E221");
                    require(id,expression(init.children[0],env,true),node.second);init.type=node.second;env.at(name).moved=true;env.at(name).empty=true;
                } else if(!inferred) require(id,expression(node.children.at(0),env,false,&eligible,owned),node.second);
                if(env.contains(node.value)&&env.at(node.value).moved) consumed.insert(env.at(node.value).symbol);
                if(env.contains(node.value)&&env.at(node.value).empty) hidden_empty.insert(env.at(node.value).symbol);
                eligible.insert(node.value);node.symbol=fresh(); env[node.value]={node.second,node.symbol,owned,owned}; declared.insert(node.value);
            } else if(kind=="global_assign"||(kind=="assign"&&!env.contains(node.value)&&!global_name(node.value).empty())) {
                if(node.kind=="assign") {node.kind="global_assign";node.value=global_name(node.value);}
                const auto &g=n(global_access(id,node.value,true));node.symbol=g.symbol;
                literal_context(node.children.at(0),g.second);require(id,expression(node.children.at(0),env),g.second);
            } else if(kind=="assign") {
                if(!env.contains(node.value)) {std::vector<std::string> names;for(const auto &[name,binding]:env) names.push_back(name);error(id,"unknown local "+node.value+suggest(node.value,names));}
                auto &binding=env.at(node.value);node.symbol=binding.symbol;literal_context(node.children.at(0),binding.type);
                if(binding.scoped) {
                    if(!binding.movable) error(id,generic_type(binding.type)?"borrowed vector cannot be reassigned":"borrowed builder cannot be reassigned","E220");
                    if(!binding.moved) error(id,"live owner cannot be overwritten","E220");
                    if(!binding.empty||!eligible.contains(node.value)) error(id,"reinitialization requires a definitely empty eligible owner","E224");
                    const auto &rhs=n(node.children.at(0));
                    if(rhs.kind!="call"||(rhs.value!=binding.type+"_new"&&!generic_fresh(rhs.value,binding.type)&&!container_fresh(rhs.value,binding.type)&&(!signatures.contains(rhs.value)||!signatures.at(rhs.value).owns_result))) error(id,"owner reinitialization requires fresh allocation or an owned result","E224");
                    require(id,expression(node.children.at(0),env,false,&eligible,true),binding.type);
                    binding.moved=false;binding.empty=false;
                } else require(id,expression(node.children.at(0),env),binding.type);
            } else if(kind=="store") {
                const auto ty=place(node.children.at(0),env); require(id,expression(node.children.at(1),env),ty);
            } else if(kind=="return") {
                if(n(node.children.at(0)).kind=="unit") {if(inferring_result) infer_return(id,"unit");if(result!="unit") error(id,"return without a value in a function returning "+result);returns=true;continue;}
                if(inferring_result) {
                    const auto &value=n(node.children.at(0));
                    if(value.kind=="move"||(value.kind=="call"&&signatures.contains(value.value)&&signatures.at(value.value).owns_result)) error(id,"owned results require an explicit [@o type] annotation","E233");
                    infer_return(id,expression(node.children.at(0),env,false,&eligible));returns=true;continue;
                }
                literal_context(node.children.at(0),result);auto &value=n(node.children.at(0));
                if(owns_result) {
                    if(value.kind=="move") {
                        if(value.children.size()!=1||n(value.children[0]).kind!="name") error(id,"owned return requires one owner name","E223");
                        const auto &name=n(value.children[0]).value;
                        if(!env.contains(name)||!env.at(name).movable) error(id,"owned return cannot adopt a manual or borrowed handle","E223");
                        require(id,expression(value.children[0],env,true),result);value.type=result;env.at(name).moved=true;env.at(name).empty=true;
                    } else {
                        if(value.kind!="call"||!signatures.contains(value.value)||!signatures.at(value.value).owns_result) error(id,"owned return requires move of an owner or an owned-result call","E223");
                        require(id,expression(node.children.at(0),env,false,&eligible,true),result);
                    }
                } else require(id,expression(node.children.at(0),env,false,&eligible),result);
                returns=true;
            }
            else if(kind=="defer") {
                if(!u.project_syntax) error(id,"defer requires native project syntax");
                if(++deferred_scope>64||++deferred_count>256) error(id,"deferred release budget exceeded (64 per scope, 256 per project)","E210");
                const auto &call=n(node.children.at(0));
                if(call.kind!="call"||(!generic_free(call.value)&&!map_specialization(call.value)&&!set_specialization(call.value)&&call.value!="int_vector_free"&&call.value!="spool_free"&&call.value!="buffer_free"&&call.value!="window_close"&&call.value!="file_close"&&call.value!="tcp_close")) error(id,"defer requires a supported release intrinsic");
                require(id,expression(node.children.at(0),env),(call.value=="file_close"||call.value=="tcp_close")?"i64":"unit");
            }
            else if(kind=="expr") expression(node.children.at(0),env,false,&eligible);
            else if(kind=="if") {
                require(id,expression(node.children.at(0),env),"bool");
                std::unordered_set<std::string> left,right,left_empty,right_empty;
                const auto a=block(group(node.children.at(1)),env,false,&eligible,&left,&left_empty);
                const auto b=block(group(node.children.at(2)),env,false,&eligible,&right,&right_empty);
                for(auto &[name,binding]:env) if(!a||!b) {
                    binding.moved=(!a&&left.contains(binding.symbol))||(!b&&right.contains(binding.symbol));
                    binding.empty=(a||left_empty.contains(binding.symbol))&&(b||right_empty.contains(binding.symbol));
                }
                returns=a&&b;
            } else if(kind=="match") returns=match(id,env,eligible);
            else if(kind=="break"||kind=="continue") {
                if(!loop_depth) error(id,kind+" outside for/while loop","E226");
            }
            else if(kind=="for_range") {
                require(id,expression(node.children.at(0),env),"i64");
                require(id,expression(node.children.at(1),env),"i64");
                if(declared.contains(node.value)) error(id,"duplicate local "+node.value);
                node.second="i64";node.symbol=fresh();declared.insert(node.value);
                Env inner=env;inner[node.value]={node.second,node.symbol,false,false};
                std::unordered_set<std::string> back_moves,back_empty;
                ++loop_depth;
                block(group(node.children.at(2)),inner,false,&eligible,&back_moves,&back_empty);
                --loop_depth;
                for(const auto &[name,binding]:env) if(binding.movable&&
                    (back_moves.contains(binding.symbol)!=binding.moved||back_empty.contains(binding.symbol)!=binding.empty))
                    error(id,"loop backedge must restore the entry ownership state of "+name,"E225");
            }
            else if(kind=="for_each") {
                const auto collection=expression(node.children.at(0),env,true);
                std::string element;
                if(auto e=generic_type(collection)) element=*e;
                else if(auto v=view_type(collection)) element=*v;
                else if(collection=="int_vector") element="i64";
                else if(auto a=array_type(collection)) element=a->element;
                else if(auto m=map_type(collection)) element=m->first;
                else if(auto s=set_type(collection)) element=*s;
                else if(u.aesop_syntax&&collection=="string") element="u32";
                else error(id,"for iteration requires a vector, view, map, set, int_vector, string or fixed array, not "+collection,"E227");
                if(declared.contains(node.value)) error(id,"duplicate local "+node.value);
                node.second=element;node.symbol=fresh();declared.insert(node.value);
                Env inner=env;inner[node.value]={element,node.symbol,false,false};
                std::unordered_set<std::string> back_moves,back_empty;
                ++loop_depth;
                block(group(node.children.at(1)),inner,false,&eligible,&back_moves,&back_empty);
                --loop_depth;
            }
            else if(kind=="while") {
                require(id,expression(node.children.at(0),env),"bool");
                std::unordered_set<std::string> back_moves,back_empty;
                ++loop_depth;
                const auto exits=block(group(node.children.at(1)),env,false,&eligible,&back_moves,&back_empty);
                --loop_depth;
                if(!exits) for(const auto &[name,binding]:env) if(binding.movable&&
                    (back_moves.contains(binding.symbol)!=binding.moved||back_empty.contains(binding.symbol)!=binding.empty))
                    error(id,"loop backedge must restore the entry ownership state of "+name,"E225");
            }
            else error(id,"invalid statement");
        }
        if(out_moves) { *out_moves=consumed;for(const auto &[name,binding]:env) if(binding.moved) out_moves->insert(binding.symbol); }
        if(out_empty) { *out_empty=hidden_empty;for(const auto &[name,binding]:env) if(binding.empty) out_empty->insert(binding.symbol); }
        return returns;
    }
public:
    explicit Checker(Unit &unit):u(unit) {}
    void run() {
        deferred_count=0;std::unordered_set<std::string> names;
        for(const auto &ty:integers) { const auto bytes=static_cast<uint64_t>(std::stoul(ty.substr(1))/8); sizes[ty]={bytes,bytes}; heights[ty]=0; }
        if(u.aesop_syntax) {sizes["f64"]={8,8};heights["f64"]=0;}
        sizes["bool"]={1,1}; heights["bool"]=0; sizes["string"]={24,8};heights["string"]=0;sizes["spool"]={8,8};heights["spool"]=0;
        if(u.project_syntax) {sizes["int_vector"]={8,8};heights["int_vector"]=0;}
        if(u.aesop_syntax) for(const auto &e:generic_elements) {sizes["vector<"+e+">"]={8,8};heights["vector<"+e+">"]=0;sizes["view<"+e+">"]={32,8};heights["view<"+e+">"]=0;}
        for(auto id:u.roots) {
            const auto &d=n(id);
            if(d.kind=="import") error(id,"imports require native filesystem project loading","E300");
            if((u.aesop_syntax&&(generic_call(d.value)||view_call(d.value)||d.value=="pi"||d.value=="tau"||math_signatures.contains(d.value)))||d.value=="print"||d.value=="array_length"||d.value=="isnum"||platform_signatures.contains(d.value)||!names.insert(d.value).second) error(id,"duplicate/reserved declaration "+d.value,"E210");
            if(d.kind=="function") functions[d.value]=id; else if(u.aesop_syntax&&d.kind=="global") globals[d.value]=id;else aggregates[d.value]=id;
        }
        for(auto id:u.roots) if(n(id).kind=="struct"||n(id).kind=="union") layout(n(id).value,1);
        for(auto id:u.roots) {
            const auto &f=n(id); if(f.kind!="function") continue;
            if(f.second.empty()) {
                bool value_return=false;List stack={f.children[1]};
                while(!stack.empty()) {
                    const auto &node=n(stack.back());stack.pop_back();
                    if(node.kind=="return"&&n(node.children.at(0)).kind!="unit") value_return=true;
                    stack.insert(stack.end(),node.children.begin(),node.children.end());
                }
                if(!value_return) n(id).second="unit";
            }
            Signature sig; sig.result=f.second;sig.owns_result=f.result_mode=="own";
            if(sig.owns_result&&(!u.project_syntax||!owner_type(f.second))) error(id,"owned results require a supported resource in native projects","E223");
            for(auto p:group(f.children[0])) if(n(p).second=="unit") error(id,"unit parameters are not permitted");
            if(!f.second.empty()) valid_type(id,f.second,true);
            for(auto p:group(f.children[0])) { valid_type(p,n(p).second);const bool borrowed=n(p).kind=="borrow_param",owned=n(p).kind=="own_param",mutable_param=n(p).kind=="mut_param";
                if((borrowed||owned)&&(!u.project_syntax||!owner_type(n(p).second))) error(p,"borrow/own parameters require a supported resource in native projects","E220");
                if(mutable_param&&!structure_fields(n(p).second)) error(p,"@m parameters must be a struct type, not "+n(p).second,"E229");
                if(!u.aesop_syntax&&mutable_param) error(p,"mutable borrows require Aesop syntax","E229");
                sig.parameters.push_back(n(p).second);sig.borrows.push_back(borrowed);sig.takes.push_back(owned);sig.mutables.push_back(mutable_param); }
            signatures[f.value]=std::move(sig);
        }
        for(const auto id:u.global_order) {
            auto &g=n(id);if(g.kind!="global") error(id,"invalid module initializer declaration","E230");
            current_file=file_of(g);initializing_global=true;Env empty;
            if(!g.second.empty()) literal_context(g.children.at(0),g.second);
            const auto type=expression(g.children.at(0),empty);
            if(g.second.empty()) g.second=type;
            require(id,type,g.second);if(!scalar(g.second)) error(id,"module variables currently require scalar value types","E230");
            g.symbol=fresh();initialized_globals.insert(g.value);
        }
        initializing_global=false;
        // Only unknown result signatures create ordering edges, explicit annotations break inference cycles
        std::unordered_map<Id,size_t> pending;
        std::unordered_map<Id,List> users;
        std::priority_queue<Id,std::vector<Id>,std::greater<Id>> ready;
        List declarations;
        for(auto id:u.roots) if(n(id).kind=="function") {
            declarations.push_back(id);std::unordered_set<Id> dependencies;List stack={n(id).children[1]};
            while(!stack.empty()) {
                const auto node_id=stack.back();stack.pop_back();const auto &node=n(node_id);
                if(node.kind=="call"&&functions.contains(node.value)) {
                    const auto target=functions.at(node.value);
                    if(n(target).second.empty()) dependencies.insert(target);
                }
                stack.insert(stack.end(),node.children.begin(),node.children.end());
            }
            pending[id]=dependencies.size();
            for(auto target:dependencies) users[target].push_back(id);
            if(dependencies.empty()) ready.push(id);
        }
        List order;
        while(!ready.empty()) {
            const auto id=ready.top();ready.pop();order.push_back(id);
            for(auto user:users[id]) if(--pending[user]==0) ready.push(user);
        }
        if(order.size()!=declarations.size()) for(auto id:declarations) if(pending[id]&&n(id).second.empty()) error(id,"circular return-type inference, add an explicit [type] annotation to break the cycle","E233");
        for(auto id:order) {
            auto &f=n(id);
            current_file=file_of(f);Env env;result=f.second;owns_result=f.result_mode=="own";inferring_result=f.second.empty();
            for(auto p:group(f.children[0])) {
                auto &param=n(p);
                if(env.contains(param.value)) error(p,"duplicate parameter "+param.value);
                param.symbol=fresh();env[param.value]={param.second,param.symbol,param.kind=="borrow_param"||param.kind=="own_param",param.kind=="own_param"};
            }
            const auto total=block(group(f.children[1]),env,true);
            if(inferring_result) {
                if(result.empty()) result="unit";
                valid_type(id,result,true);f.second=result;signatures.at(f.value).result=result;
            }
            if(!total&&result!="unit") error(id,"not every path returns a value");
        }
        if(!signatures.contains("main")||signatures.at("main").result!="i64"||!signatures.at("main").parameters.empty()) throw Failure{{"E201","entry point must be a parameterless func main returning i64 (explicit or inferred)",UINT32_MAX}};
    }
};
