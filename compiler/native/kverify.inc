// Independent, read-only verifier of the current structured native arena.
// Does not call Checker, trust Unit::checked, or repair inferred metadata.
class Verifier {
    const Unit &u;
    struct Local { std::string type,symbol; bool scoped=false,movable=false,moved=false,empty=false; };
    struct Function { std::vector<std::string> arguments; std::string result; std::vector<bool> borrows,takes,mutables; bool owns_result=false; };
    using Scope=std::unordered_map<std::string,Local>;
    std::unordered_map<std::string,Id> records,sums;
    std::unordered_map<std::string,Function> functions;
    std::unordered_map<std::string,uint32_t> function_files;
    std::string current_function;
    uint32_t current_file=0,loop_depth=0;
    std::unordered_map<std::string,Id> globals;
    std::unordered_set<std::string> initialized_globals;
    bool initializing_global=false;
    const Node &global_access(const std::string &name,bool write=false) const {
        need(u.next_syntax&&globals.contains(name),"unknown global reference");const auto &g=at(globals.at(name));
        need(file_of(g)==current_file||(g.result_mode!="p"&&(!write||g.result_mode=="rw")),"private/readonly module variable access");
        need(!initializing_global||initialized_globals.contains(name),"initializer reads uninitialized module variable");return g;
    }
    void function_access(const std::string &name) const {
        need(current_file==function_files.at(name)||u.public_functions.contains(name),"cross-module call to private function");
        if(u.nested_parents.contains(name)) {
            auto caller=current_function;const auto &parent=u.nested_parents.at(name);uint32_t depth=0;
            while(caller!=parent) {need(++depth<=64&&u.nested_parents.contains(caller),"nested helper called outside enclosing lexical scope");caller=u.nested_parents.at(caller);}
        }
    }
    uint32_t file_of(const Node &node) const {return u.origins.empty()?0:u.origins.at(node.token).file;}
    std::unordered_set<std::string> symbols,active;
    struct Layout { uint64_t size,align; uint32_t height; };
    std::unordered_map<std::string,Layout> layouts;
    [[noreturn]] static void fail(const std::string &message) {
        throw Failure{{"E500","IR verification failed: "+message,UINT32_MAX}};
    }
    static void need(bool yes,const std::string &message) { if(!yes) fail(message); }
    const Node &at(Id id) const { need(id<u.arena.size(),"invalid arena reference"); return u.arena[id]; }
    const Node &shape(Id id,const std::string &kind,size_t arity) const {
        const auto &n=at(id); need(n.kind==kind,"invalid node kind");
        need(n.children.size()==arity,"invalid child count for "+kind); return n;
    }
    const List &list(Id id) const { const auto &n=at(id); need(n.kind=="#list","expected list node"); return n.children; }
    bool ident(const std::string &name) const { return name.size()<=128&&identifier(name)&&!(u.project_syntax&&name=="int_vector")&&!(u.next_syntax&&(name=="elseif"||name=="vector"||name=="view")); }
    bool flat_struct(const std::string &ty,uint32_t depth=0) const {
        const auto it=records.find(ty);
        if(it==records.end()||depth>64) return false;
        for(auto f:at(it->second).children) {const auto &t=at(f).second;if(!scalar(t)&&!flat_struct(t,depth+1)) return false;}
        return true;
    }
    bool scalar(const std::string &ty) const { return ty=="bool"||ty=="string"||(u.next_syntax&&ty=="f64")||integers.contains(ty); }
    bool resource_struct(const std::string &ty,uint32_t depth=0) const {
        const auto it=records.find(ty);
        if(!u.next_syntax||depth>64||it==records.end()) return false;
        for(auto f:at(it->second).children) {const auto &t=at(f).second;if(generic_type(t)||map_type(t)||set_type(t)||t=="spool"||resource_struct(t,depth+1)) return true;}
        return false;
    }
    bool resource(const std::string &ty) const {return resource_struct(ty)|| (u.next_syntax&&(generic_type(ty)||map_type(ty)||set_type(ty)))||ty=="spool"||(u.project_syntax&&ty=="int_vector");}
    bool value(const std::string &ty,uint32_t depth=0) const {if(depth>64) return false;if(auto a=array_type(ty)) return u.project_syntax&&value(a->element,depth+1);return scalar(ty)||resource(ty)||(u.next_syntax&&view_type(ty))||records.contains(ty)||sums.contains(ty); }
    void graph() const {
        need(u.source.size()<=1048576&&u.arena.size()<=max_nodes,"arena/source budget exceeded");
        need(!u.bytes.empty()&&u.bytes.front()==0&&u.bytes.back()==u.source.size(),"invalid source map");
        for(size_t i=1;i<u.bytes.size();++i) need(u.bytes[i]>u.bytes[i-1],"invalid source map order");
        need(!u.tokens.empty()&&u.tokens.size()<=100001,"invalid token budget");
        if(!u.origins.empty()) {
            need(u.files.size()<=64&&u.file_lengths.size()==u.files.size()&&u.origins.size()==u.tokens.size(),"invalid project provenance");
            for(size_t i=0;i<u.origins.size();++i) {
                const auto &o=u.origins[i];const auto &t=u.tokens[i];
                need(o.file<u.files.size()&&o.start<=o.end&&o.end<=u.file_lengths[o.file],"invalid project source span");
                need(t.start<=t.end&&o.end-o.start==t.end-t.start,"inconsistent project source span");
            }
        }
        need(u.roots.size()<=u.arena.size(),"root budget exceeded");
        size_t edges=u.roots.size(),literal_bytes=0,deferred_count=0;
        std::vector<unsigned char> seen(u.arena.size(),0);
        std::vector<std::pair<Id,uint32_t>> stack; uint32_t count=0;
        for(auto id:u.roots) stack.emplace_back(id,1);
        while(!stack.empty()) {
            const auto [id,depth]=stack.back(); stack.pop_back(); const auto &n=at(id);
            need(!seen[id],"shared or duplicate reachable node"); seen[id]=1;
            need(n.token<u.tokens.size(),"invalid source token reference"); const auto &token=u.tokens[n.token];
            need(token.line&&token.column&&token.start<=token.end&&token.end<u.bytes.size(),"invalid source token");
            if(n.kind!="#list") { need(depth<=64,"IR nesting limit exceeded"); need(++count<=100000,"IR node budget exceeded"); }
            // Canonical representation: no payload in null nodes, no unexpected
            // secondary string, and annotations only on their permitted kinds.
            need(n.kind.size()<=32&&n.value.size()<=(n.kind=="string"?65536u:257u)&&n.second.size()<=128&&n.type.size()<=128&&n.symbol.size()<=128&&n.literal.size()<=3,"node string budget exceeded");
            need(n.children.size()<=u.arena.size()-edges,"edge budget exceeded"); edges+=n.children.size();
            const auto &k=n.kind;
            need(n.result_mode.empty()||(k=="function"&&n.result_mode=="own")||(u.next_syntax&&k=="global"&&(n.result_mode=="p"||n.result_mode=="r"||n.result_mode=="rw"))||(u.next_syntax&&(k=="union"||k=="struct")&&n.result_mode=="r"),"invalid result mode annotation");
            if(k=="defer"||k=="scoped_local"||k=="own_param") need(u.project_syntax&&++deferred_count<=256,"deferred release project budget/syntax");
            if(k=="string") {literal_bytes+=n.value.size();need(literal_bytes<=1048576,"aggregate string literal budget exceeded");}
            const bool expression=k=="unit"||k=="format"||k=="concat"||k=="global_ref"||k=="float"||k=="move"||k=="array_repeat"||k=="array"||k=="index"||k=="string"||k=="int"||k=="uint"||k=="bool"||k=="name"||k=="field"||k=="convert"||k=="unary"||k=="binary"||k=="call"||k=="union_ctor";
            const bool pair=k=="global"||k=="function"||k=="field_decl"||(k=="param"||(k=="borrow_param"||k=="own_param"))||k=="mut_param"||(k=="local"||k=="scoped_local")||k=="for_range"||k=="for_each"||k=="case"||k=="union_ctor";
            const bool string=k=="global_ref"||k=="global_assign"||k=="float"||k=="array_repeat"||k=="string"||k=="struct"||k=="union"||k=="variant_decl"||k=="pattern_bind"||k=="name"||k=="field"||k=="convert"||k=="unary"||k=="binary"||k=="call"||k=="assign";
            const std::string expected=pair?"pair":string?"string":k=="bool"?"bool":(k=="int"||k=="uint")?"integer":"null";
            need(n.value_kind==expected,"invalid value representation");
            if(expected=="null") need(n.value.empty(),"unexpected node payload");
            if(!pair) need(n.second.empty(),"unexpected secondary payload");
            if(!expression&&k!="pattern_bind") need(n.type.empty(),"unexpected type annotation");
            if(k!="global"&&k!="global_ref"&&k!="global_assign"&&k!="name"&&k!="param"&&k!="borrow_param"&&k!="own_param"&&k!="mut_param"&&k!="local"&&k!="scoped_local"&&k!="assign"&&k!="pattern_bind"&&k!="for_range"&&k!="for_each") need(n.symbol.empty(),"unexpected symbol annotation");
            if(k!="int"&&k!="uint") need(n.literal.empty(),"unexpected literal annotation");
            for(auto child:n.children) {
                need(child<id,"non-backward arena reference");
                stack.emplace_back(child,depth+(k!="#list"));
            }
        }
    }
    std::vector<std::string> field_types(const List &fields) const {
        std::vector<std::string> out; for(auto id:fields) out.push_back(at(id).second); return out;
    }
    void fields(const List &items) const {
        need(items.size()<=128,"field budget exceeded"); std::unordered_set<std::string> names;
        for(auto id:items) {
            const auto &f=shape(id,"field_decl",0);
            need(ident(f.value)&&names.insert(f.value).second,"invalid/duplicate field name");
            need(value(f.second),"invalid field type");
            if(u.next_syntax) need(scalar(f.second)||sums.contains(f.second)||records.contains(f.second)||resource(f.second),"invalid aggregate field type");
        }
    }
    Layout payload(const List &items,uint32_t depth) {
        uint64_t bytes=0,align=1; uint32_t height=0;
        for(auto id:items) {
            const auto item=layout(at(id).second,depth+1);
            bytes=((bytes+item.align-1)/item.align)*item.align+item.size;
            align=std::max(align,item.align); height=std::max(height,item.height+1);
            need(bytes<=1048576&&height<=64,"aggregate layout budget exceeded");
        }
        return {((bytes+align-1)/align)*align,align,height};
    }
    Layout layout(const std::string &ty,uint32_t depth) {
        if(layouts.contains(ty)) return layouts.at(ty);
        if(u.next_syntax&&(generic_type(ty)||map_type(ty)||set_type(ty)||ty=="spool")) return layouts[ty]=Layout{16,8,0};
        need(depth<=64,"aggregate nesting limit exceeded");
        need(active.insert(ty).second,"recursive value layout"); Layout out{};
        if(auto a=array_type(ty)) {const auto e=layout(a->element,depth+1);need(e.size<=1048576/a->count,"array size budget");out={e.size*a->count,e.align,e.height+1};}
        else if(records.contains(ty)) out=payload(at(records.at(ty)).children,depth);
        else {
            need(sums.contains(ty),"invalid layout type"); uint64_t bytes=1,align=1; uint32_t height=1;
            for(auto id:at(sums.at(ty)).children) {
                const auto p=payload(at(id).children,depth); bytes=std::max(bytes,p.size); align=std::max(align,p.align); height=std::max(height,p.height);
            }
            bytes=((4+align-1)/align)*align+bytes; align=std::max<uint64_t>(4,align);
            out={((bytes+align-1)/align)*align,align,height};
        }
        need(out.size<=1048576&&out.height<=64,"aggregate layout budget exceeded");
        active.erase(ty); layouts[ty]=out; return out;
    }
    void binding(const Node &n,const std::string &ty) {
        const auto &s=n.symbol;
        need(s.size()>=4&&s.size()<=128&&s.starts_with("k_v")&&s[3]>='1'&&s[3]<='9'&&
             std::all_of(s.begin()+4,s.end(),[](char c){return c>='0'&&c<='9';}),"invalid binding symbol");
        need(symbols.insert(s).second,"duplicate binding symbol"); need(value(ty),"invalid binding type");if(array_type(ty)) layout(ty,1);
    }
    Id variant(const std::string &owner,const std::string &name) const {
        need(sums.contains(owner),"unknown union constructor");
        if(u.next_syntax) need(file_of(at(sums.at(owner)))==current_file||at(sums.at(owner)).result_mode=="r","cross-module access to private enum variant");
        for(auto id:at(sums.at(owner)).children) if(at(id).value==name) return id;
        fail("unknown variant");
    }
    std::string projection(const std::string &base,const std::string &name) const {
        need(records.contains(base),"projection on non-struct");
        for(auto id:at(records.at(base)).children) if(at(id).value==name) return at(id).second;
        fail("unknown field projection");
    }
    void literal(const Node &n) const {
        const auto &ty=n.literal; need(integers.contains(ty),"invalid literal type");
        need((n.kind=="int")== (ty[0]=='i'),"literal signedness mismatch");
        const auto &text=n.value; need(!text.empty()&&text.size()<=257,"invalid integer spelling");
        const bool negative=text[0]=='-'; const size_t start=negative?1:0;
        need(text.size()>start&&(!negative||ty[0]=='i'),"invalid integer sign");
        need(text[start]!='0'||text.size()==start+1,"non-canonical integer spelling");
        need(!negative||text.substr(start)!="0","negative zero spelling");
        const auto bits=static_cast<uint32_t>(std::stoul(ty.substr(1)));
        const uint64_t limit=ty[0]=='i'?(negative?(uint64_t(1)<<(bits-1)):(uint64_t(1)<<(bits-1))-1):bits==64?UINT64_MAX:(uint64_t(1)<<bits)-1;
        uint64_t magnitude=0;
        for(size_t i=start;i<text.size();++i) {
            need(text[i]>='0'&&text[i]<='9',"invalid integer digit"); const auto digit=static_cast<uint64_t>(text[i]-'0');
            need(magnitude<limit/10||(magnitude==limit/10&&digit<=limit%10),"integer literal outside range");
            magnitude=magnitude*10+digit;
        }
    }
    std::string expression(Id id,Scope &env,bool borrow=false,const std::unordered_set<std::string> *transfer_scope=nullptr,bool adopt=false) {
        const auto &n=at(id); const auto &k=n.kind;
        if(initializing_global) need(k=="global_ref"||k=="float"||k=="int"||k=="uint"||k=="bool"||k=="string"||k=="unary"||k=="binary"||k=="convert"||k=="format"||k=="concat"||(k=="call"&&math_signatures.contains(n.value)),"impure/non-scalar module initializer");
        std::string ty;
        if(k=="array_repeat") {
            shape(id,k,1);need(u.project_syntax,"repeated array requires project syntax");
            const auto count=array_type("[i64;"+n.value+"]");need(bool(count),"invalid repeated array count");
            const auto element=expression(n.children[0],env);need(value(element),"invalid repeated array element");
            ty=array_name(element,count->count);need(value(ty),"invalid repeated array type");layout(ty,1);
        } else if(k=="array") {
            need(u.project_syntax&&!n.children.empty()&&n.children.size()<=1024,"invalid array literal");
            const auto element=expression(n.children[0],env);need(value(element),"invalid array element");
            for(size_t i=1;i<n.children.size();++i) need(expression(n.children[i],env)==element,"mismatched array element");
            ty=array_name(element,n.children.size());need(value(ty),"invalid array type");layout(ty,1);
        } else if(k=="index") {
            shape(id,k,2);need(u.project_syntax,"index requires project syntax");const auto a=array_type(expression(n.children[0],env));need(bool(a),"index on non-array");
            need(expression(n.children[1],env)=="i64","index type");ty=a->element;
        } else if(k=="float") {shape(id,k,0);need(u.next_syntax&&finite_decimal(n.value),"invalid f64 literal");ty="f64";
        } else if(k=="int"||k=="uint") { shape(id,k,0); literal(n); ty=n.literal; }
        else if(k=="string") {shape(id,k,0);size_t count=0;need(text_scalars(n.value,count),"invalid UTF-8 string literal");ty="string";}
        else if(k=="bool") { shape(id,k,0); need(n.value=="true"||n.value=="false","invalid boolean literal"); ty="bool"; }
        else if(k=="unit") { shape(id,k,0); need(u.next_syntax,"unit literal outside next syntax"); ty="unit"; }
        else if(k=="global_ref") {shape(id,k,0);const auto &g=global_access(n.value);need(n.symbol==g.symbol,"global read symbol mismatch");ty=g.second;}
        else if(k=="name") {
            shape(id,k,0); need(ident(n.value)&&env.contains(n.value),"free local name");
            const auto &local=env.at(n.value);need(!local.moved,"use of moved builder"); need(!local.scoped||borrow,"scoped builder copied/released/escaped"); need(n.symbol==local.symbol,"incorrect resolved local symbol"); ty=local.type;
        } else if(k=="field") { shape(id,k,1); need(ident(n.value),"invalid field name"); ty=projection(expression(n.children[0],env,true),n.value); }
        else if(k=="format") {shape(id,k,1);need(u.next_syntax&&scalar(expression(n.children[0],env)),"invalid string injection");ty="string";}
        else if(k=="concat") {shape(id,k,2);need(u.next_syntax&&expression(n.children[0],env)=="string"&&expression(n.children[1],env)=="string","invalid concatenation");ty="string";}
        else if(k=="convert") { shape(id,k,1); const auto source=expression(n.children[0],env);need((integers.contains(n.value)&&integers.contains(source))||(u.next_syntax&&n.value=="f64"&&(integers.contains(source)||source=="f64")),"invalid numeric conversion"); ty=n.value; }
        else if(k=="unary") {
            shape(id,k,1); ty=expression(n.children[0],env);
            need(n.value=="not"?ty=="bool":n.value=="-"&&((integers.contains(ty)&&ty[0]=='i')||(u.next_syntax&&ty=="f64")),"invalid unary operation");
        } else if(k=="binary") {
            shape(id,k,2); const auto a=expression(n.children[0],env),b=expression(n.children[1],env); const auto &op=n.value;
            if(op=="and"||op=="or") { need(a=="bool"&&b==a,"invalid logical operands"); ty="bool"; }
            else if(op=="=="||op=="!=") {need(a==b&&(scalar(a)||(u.next_syntax&&flat_struct(a))),"invalid equality operands"); ty="bool";}
            else if(op=="+"&&a=="string"&&b=="string") ty="string";
            else {
                need(op=="+"||op=="-"||op=="*"||op=="/"||op=="%"||op=="<"||op==">"||op=="<="||op==">=","invalid binary operator");
                need((integers.contains(a)||(u.next_syntax&&a=="f64"&&op!="%"))&&a==b,"invalid arithmetic/comparison operands");
                ty=(op=="<"||op==">"||op=="<="||op==">=")?"bool":a;
            }
        } else if(k=="call"||k=="union_ctor") {
            if(k=="call"&&(generic_specialization(n.value)||view_specialization(n.value))) need(u.next_syntax,"generic vector outside next syntax");
            if(k=="call"&&n.value.starts_with("int_vector_")) need(u.project_syntax,"vector call outside project syntax");
            need(ident(n.value),"invalid callee name");
            const auto resolved=container_signature(n.value);
            need(!(map_call(n.value)||set_call(n.value)),"unresolved map/set operation");
            if(k=="call"&&functions.contains(n.value)&&functions.at(n.value).owns_result) need(adopt,"unadopted owned call result");
            std::vector<std::string> args;
            static const std::unordered_set<std::string> allowed={"spool_valid","spool_reserve","spool_truncate","spool_clear","spool_capacity","spool_bytes","spool_length","spool_append","spool_codepoint","spool_i64","spool_u64","spool_print","spool_snapshot","int_vector_valid","int_vector_length","int_vector_capacity","int_vector_reserve","int_vector_push","int_vector_pop","int_vector_get","int_vector_set","int_vector_clear","int_vector_insert","int_vector_remove"};
            std::unordered_set<std::string> lent,taken;
            for(size_t i=0;i<n.children.size();++i) {
                const bool user_borrow=functions.contains(n.value)&&i<functions.at(n.value).borrows.size()&&functions.at(n.value).borrows[i];
                const bool taking=(k=="call"&&functions.contains(n.value)&&i<functions.at(n.value).takes.size()&&functions.at(n.value).takes[i])||(k=="call"&&u.next_syntax&&!functions.contains(n.value)&&records.contains(n.value)&&resource_struct(n.value)&&i<at(records.at(n.value)).children.size()&&resource(at(at(records.at(n.value)).children[i]).second));
                const auto &arg=at(n.children[i]);
                if(k=="call"&&functions.contains(n.value)&&i<functions.at(n.value).mutables.size()&&functions.at(n.value).mutables[i]) {
                    need(u.mutable_arguments.contains(n.children[i]),"mutable argument must be an in-place borrow");
                    const auto &argument=at(n.children[i]);
                    need(argument.kind=="name"||argument.kind=="field"||argument.kind=="index","mutable argument must be a place");
                    need(place(n.children[i],env)==functions.at(n.value).arguments[i],"mutable argument type");
                    args.push_back(functions.at(n.value).arguments[i]);continue;
                }
                if(taking) {
                    need(transfer_scope!=nullptr,"consuming call outside direct statement context");shape(n.children[i],"move",1);const auto &from=shape(arg.children[0],"name",0);
                    need(env.contains(from.value)&&env.at(from.value).movable&&transfer_scope->contains(from.value),"own argument source must be same-block owner");
                    args.push_back(expression(arg.children[0],env,true));need(arg.type==args.back(),"own move annotation");taken.insert(env.at(from.value).symbol);env.at(from.value).moved=true;env.at(from.value).empty=true;
                } else {
                    const bool lending=k=="call"&&((i==0&&(allowed.contains(n.value)||generic_borrow(n.value)||container_borrow(n.value)))||user_borrow||(n.value=="process_capture"&&(i==2||i==3)));
                    args.push_back(expression(n.children[i],env,lending));if(lending&&arg.kind=="name"&&env.contains(arg.value)) lent.insert(env.at(arg.value).symbol);
                }
            }
            for(const auto &symbol:taken) need(!lent.contains(symbol),"borrow/consume alias in one call");
            if(k=="union_ctor") {need(ident(n.second),"invalid variant name"); need(args==field_types(at(variant(n.value,n.second)).children),"invalid union arguments"); ty=n.value;}
            else if(n.value=="print") {need(args.size()==1&&scalar(args[0]),"invalid print call"); ty="unit";}
            else if(n.value=="array_length") {need(args.size()==1&&array_type(args[0]),"invalid array_length call");ty="i64";}
            else if(u.next_syntax&&math_signatures.contains(n.value)) {const auto &sig=math_signatures.at(n.value);need(args==sig.parameters,"invalid math arguments");ty=sig.result;}
            else if(auto container=new_container_type(n.value)) {need(args.size()==1&&args[0]=="i64","invalid container allocation");ty=*container;}
            else if(resolved) {
                const auto &expected=resolved->first;
                need(args.size()==expected.size(),"invalid container argument count");
                need(args[0]==*map_container_type(n.value),"container argument type mismatch");
                for(size_t i=1;i<expected.size();++i) need(args[i]==expected[i],"invalid container argument type");
                ty=resolved->second;
            }
            else if(platform_signatures.contains(n.value)) {const auto &sig=platform_signatures.at(n.value); need(args==sig.parameters,"invalid platform arguments"); ty=sig.result;}
            else if(records.contains(n.value)) {need(args==field_types(at(records.at(n.value)).children),"invalid constructor arguments"); ty=n.value;}
            else {need(functions.contains(n.value),"unknown callee"); const auto &f=functions.at(n.value); if(u.next_syntax) function_access(n.value); need(args==f.arguments,"invalid call arguments"); ty=f.result;}
        } else fail("invalid expression kind");
        need(n.type==ty,"incorrect expression type annotation"); return ty;
    }
    std::string place(Id id,Scope &env) {
        const auto &n=at(id); if(n.kind=="name") return expression(id,env,true);
        if(n.kind=="index") {
            shape(id,"index",2);need(u.project_syntax,"indexed place requires project syntax");const auto a=array_type(place(n.children[0],env));need(bool(a),"index place on non-array");
            need(expression(n.children[1],env)=="i64"&&n.type==a->element,"indexed place annotation/type");return a->element;
        }
        shape(id,"field",1); need(ident(n.value),"invalid place field");
        const auto ty=projection(place(n.children[0],env),n.value); need(n.type==ty,"incorrect place annotation"); return ty;
    }
    bool matched(Id id,Scope &env,const std::string &ret,bool own_result,const std::unordered_set<std::string> &eligible) {
        const auto &n=shape(id,"match",2); const auto ty=expression(n.children[0],env); need(sums.contains(ty),"match on non-union");
        std::unordered_set<std::string> seen,joined,definite; bool total=true,first=true;
        for(auto arm_id:list(n.children[1])) {
            const auto &arm=shape(arm_id,"case",2); need(arm.value==ty&&ident(arm.second),"invalid case identity");
            const auto &fields=at(variant(ty,arm.second)).children; need(seen.insert(arm.second).second,"duplicate case");
            const auto &binders=list(arm.children[0]); need(fields.size()==binders.size(),"pattern arity mismatch");
            Scope branch=env; std::unordered_set<std::string> names,shadow_moved,shadow_empty;
            for(size_t i=0;i<binders.size();++i) {
                const auto &b=shape(binders[i],"pattern_bind",0); const auto &ft=at(fields[i]).second;
                need(ident(b.value)&&b.type==ft,"invalid pattern annotation");
                if(b.value=="_") {need(b.symbol.empty(),"discard has a symbol");continue;}
                need(names.insert(b.value).second,"duplicate pattern binding"); binding(b,ft);if(branch.contains(b.value)) {const auto &old=branch.at(b.value);if(old.moved) shadow_moved.insert(old.symbol);if(old.empty) shadow_empty.insert(old.symbol);}
                branch[b.value]={ft,b.symbol};
            }
            std::unordered_set<std::string> outcome,empties;
            const auto arm_total=block(list(arm.children[1]),branch,ret,false,own_result,&eligible,&outcome,&empties);
            if(!arm_total) {
                outcome.insert(shadow_moved.begin(),shadow_moved.end());empties.insert(shadow_empty.begin(),shadow_empty.end());
                for(const auto &symbol:outcome) joined.insert(symbol);
                if(first) {definite=empties;first=false;} else for(auto it=definite.begin();it!=definite.end();) {if(empties.contains(*it)) ++it;else it=definite.erase(it);}
            }
            total=total&&arm_total;
        }
        need(seen.size()==at(sums.at(ty)).children.size(),"non-exhaustive match");
        for(auto &item:env) if(!total) {item.second.moved=joined.contains(item.second.symbol);item.second.empty=definite.contains(item.second.symbol);}
        return total;
    }
    bool block(const List &body,const Scope &outer,const std::string &ret,bool entry=false,bool own_result=false,const std::unordered_set<std::string> *inherited=nullptr,std::unordered_set<std::string> *exits=nullptr,std::unordered_set<std::string> *empty_exits=nullptr) {
        Scope env=outer; std::unordered_set<std::string> declared,eligible=inherited?*inherited:std::unordered_set<std::string>{},hidden_moved,hidden_empty; bool total=false;size_t deferred_scope=0;
        if(entry) for(const auto &[name,binding]:env) if(binding.movable) {declared.insert(name);eligible.insert(name);need(++deferred_scope<=64,"own parameter cleanup scope budget");}
        for(auto id:body) {
            const auto &n=at(id); const auto &k=n.kind; need(!total,"unreachable statement");
            if((k=="local"||k=="scoped_local")) {
                shape(id,k,1);const bool owned=k=="scoped_local";
                if(owned) {
                    need(u.project_syntax&&++deferred_scope<=64,"scoped cleanup budget/syntax");
                    const auto &init=at(n.children[0]);
                    need(resource(n.second)&&(init.kind=="move"||(init.kind=="call"&&(init.value==n.second+"_new"||(init.value==n.second&&resource_struct(n.second))||generic_fresh(init.value,n.second)||container_fresh(init.value,n.second)||(functions.contains(init.value)&&functions.at(init.value).owns_result)))),"scoped requires fresh allocation or move");
                } need(ident(n.value)&&!declared.contains(n.value),"invalid/duplicate local name");
                const auto &init=at(n.children[0]);
                if(owned&&init.kind=="move") {
                    shape(n.children[0],"move",1);const auto &from=shape(init.children[0],"name",0);
                    need(env.contains(from.value)&&env.at(from.value).movable&&eligible.contains(from.value),"move source crosses ownership loop barrier");
                    need(expression(init.children[0],env,true)==n.second&&init.type==n.second,"invalid move type");env.at(from.value).moved=true;env.at(from.value).empty=true;
                } else need(expression(n.children[0],env,false,&eligible,owned)==n.second,"local initializer type");
                if(env.contains(n.value)&&env.at(n.value).moved) hidden_moved.insert(env.at(n.value).symbol);
                if(env.contains(n.value)&&env.at(n.value).empty) hidden_empty.insert(env.at(n.value).symbol);
                binding(n,n.second);declared.insert(n.value);eligible.insert(n.value); env[n.value]={n.second,n.symbol,owned,owned};
            } else if(k=="global_assign") {shape(id,k,1);const auto &g=global_access(n.value,true);need(n.symbol==g.symbol&&expression(n.children[0],env)==g.second,"global assignment symbol/type mismatch");
            } else if(k=="assign") {
                shape(id,k,1); need(ident(n.value)&&env.contains(n.value),"assignment to free local");auto &local=env.at(n.value);
                need(n.symbol==local.symbol,"assignment symbol mismatch");
                if(local.scoped) {
                    need(local.movable&&local.moved&&local.empty&&eligible.contains(n.value),"reinitialization without definitely empty eligible owner");
                    const auto &rhs=at(n.children[0]);need(rhs.kind=="call"&&(rhs.value==local.type+"_new"||generic_fresh(rhs.value,local.type)||container_fresh(rhs.value,local.type)||(functions.contains(rhs.value)&&functions.at(rhs.value).owns_result)),"invalid owner reinitialization source");
                    need(expression(n.children[0],env,false,&eligible,true)==local.type,"owner reinitialization type");local.moved=false;local.empty=false;
                } else need(expression(n.children[0],env)==local.type,"assignment type");
            } else if(k=="store") {shape(id,k,2); need(place(n.children[0],env)==expression(n.children[1],env),"field store type");}
            else if(k=="return") {
                shape(id,k,1);const auto &value=at(n.children[0]);
                if(value.kind=="unit") {need(ret=="unit"&&!own_result,"bare return in a value function");total=true;continue;}
                if(own_result) {
                    if(value.kind=="move") {
                        shape(n.children[0],"move",1);const auto &from=shape(value.children[0],"name",0);
                        need(env.contains(from.value)&&env.at(from.value).movable,"owned return source must be an owner");
                        need(expression(value.children[0],env,true)==ret&&value.type==ret,"owned return move type");env.at(from.value).moved=true;env.at(from.value).empty=true;
                    } else {
                        need(value.kind=="call"&&functions.contains(value.value)&&functions.at(value.value).owns_result,"owned return requires move or owned-result call");
                        need(expression(n.children[0],env,false,&eligible,true)==ret,"owned return type");
                    }
                } else need(expression(n.children[0],env,false,&eligible)==ret,"return type");total=true;
            }
            else if(k=="defer") {
                shape(id,k,1);need(++deferred_scope<=64,"deferred release scope budget");
                const auto &call=shape(n.children[0],"call",1);
                need(generic_free(call.value)||(container_call(call.value)&&call.value.find("_free_")!=std::string::npos)||call.value=="int_vector_free"||call.value=="spool_free"||call.value=="buffer_free"||call.value=="window_close"||call.value=="file_close"||call.value=="tcp_close","invalid deferred release");
                need(expression(n.children[0],env)==((call.value=="file_close"||call.value=="tcp_close")?"i64":"unit"),"invalid deferred release type");
            }
            else if(k=="expr") {shape(id,k,1);expression(n.children[0],env,false,&eligible);}
            else if(k=="if") {
                shape(id,k,3);need(expression(n.children[0],env)=="bool","if condition type");
                std::unordered_set<std::string> a_moves,b_moves,a_empty,b_empty;
                const auto a=block(list(n.children[1]),env,ret,false,own_result,&eligible,&a_moves,&a_empty);
                const auto b=block(list(n.children[2]),env,ret,false,own_result,&eligible,&b_moves,&b_empty);
                for(auto &item:env) {
                    auto &local=item.second;
                    if(!a||!b) {local.moved=(!a&&a_moves.contains(local.symbol))||(!b&&b_moves.contains(local.symbol));local.empty=(a||a_empty.contains(local.symbol))&&(b||b_empty.contains(local.symbol));}
                }
                total=a&&b;
            } else if(k=="while") {
                shape(id,k,2);need(expression(n.children[0],env)=="bool","while condition type");
                std::unordered_set<std::string> moved_back,empty_back;++loop_depth;
                const auto terminal=block(list(n.children[1]),env,ret,false,own_result,&eligible,&moved_back,&empty_back);
                --loop_depth;
                if(!terminal) for(const auto &item:env) if(item.second.movable) {
                    const auto &before=item.second;
                    need(before.moved==moved_back.contains(before.symbol)&&before.empty==empty_back.contains(before.symbol),"loop ownership invariant mismatch");
                }
            }
            else if(k=="break"||k=="continue") {
                shape(id,k,0);need(u.next_syntax&&loop_depth>0,"break/continue outside a loop");
            } else if(k=="for_range") {
                need(u.next_syntax&&list(n.children[2]).size()<=100000,"invalid range loop");
                need(expression(n.children[0],env)=="i64"&&expression(n.children[1],env)=="i64","range loop bounds must be i64");
                need(ident(n.value)&&!declared.contains(n.value)&&n.second=="i64","invalid range loop binding");
                binding(n,"i64");declared.insert(n.value);
                Scope inner=env;inner[n.value]={"i64",n.symbol};
                std::unordered_set<std::string> back_moves,empty_back;++loop_depth;
                block(list(n.children[2]),inner,ret,false,own_result,&eligible,&back_moves,&empty_back);
                --loop_depth;
            } else if(k=="for_each") {
                const auto collection=expression(n.children[0],env,true);
                std::string element;
                if(auto e=generic_type(collection)) element=*e;else if(auto v=view_type(collection)) element=*v;else if(collection=="int_vector") element="i64";else if(auto a=array_type(collection)) element=a->element;else if(auto m=map_type(collection)) element=m->first;else if(auto t=set_type(collection)) element=*t;else if(u.next_syntax&&collection=="string") element="u32";
                need(!element.empty(),"for iteration requires a vector, view, int_vector or fixed array");
                need(ident(n.value)&&!declared.contains(n.value)&&n.second==element,"invalid iteration binding");
                binding(n,element);declared.insert(n.value);
                Scope inner=env;inner[n.value]={element,n.symbol};
                std::unordered_set<std::string> back_moves,empty_back;++loop_depth;
                block(list(n.children[1]),inner,ret,false,own_result,&eligible,&back_moves,&empty_back);
                --loop_depth;
            } else if(k=="match") total=matched(id,env,ret,own_result,eligible);
            else fail("invalid statement kind");
        }
        if(exits) { *exits=hidden_moved;for(const auto &item:env) if(item.second.moved) exits->insert(item.second.symbol); }
        if(empty_exits) { *empty_exits=hidden_empty;for(const auto &item:env) if(item.second.empty) empty_exits->insert(item.second.symbol); }
        return total;
    }
public:
    explicit Verifier(const Unit &unit):u(unit) {}
    void run() {
        need(u.diagnostics.empty(),"unit contains diagnostics"); graph(); std::unordered_set<std::string> names;
        for(const auto &ty:integers) {const uint64_t bytes=std::stoul(ty.substr(1))/8; layouts[ty]={bytes,bytes,0};} layouts["bool"]={1,1,0};layouts["string"]={24,8,0};layouts["spool"]={8,8,0};
        if(u.next_syntax) layouts["f64"]={8,8,0};
        if(u.project_syntax) layouts["int_vector"]={8,8,0};
        if(u.next_syntax) for(const auto &e:generic_elements) {layouts["vector<"+e+">"]={8,8,0};layouts["view<"+e+">"]={32,8,0};}
        for(auto id:u.roots) {
            const auto &d=at(id); need(d.kind=="struct"||d.kind=="union"||d.kind=="function"||(u.next_syntax&&d.kind=="global"),"invalid declaration kind");
            need(!(u.next_syntax&&(generic_call(d.value)||view_call(d.value)||d.value=="pi"||d.value=="tau"||math_signatures.contains(d.value)))&&ident(d.value)&&d.value!="print"&&d.value!="array_length"&&!platform_signatures.contains(d.value)&&names.insert(d.value).second,"invalid/duplicate declaration name");
            if(u.next_syntax) {if((d.kind=="union"||d.kind=="struct")&&!u.origins.empty()) need(d.value.starts_with("km_"+std::to_string(file_of(d))+"_"),"enum or struct/module provenance mismatch");}
            if(d.kind=="struct") records[d.value]=id; else if(d.kind=="union") sums[d.value]=id;
        }
        for(auto id:u.roots) {
            const auto &d=at(id);
            if(d.kind=="struct") {need(!d.children.empty(),"empty struct");fields(d.children);}
            else if(d.kind=="union") {
                need(!d.children.empty()&&d.children.size()<=128,"invalid variant count"); std::unordered_set<std::string> variants;
                for(auto v:d.children) {const auto &n=at(v);need(n.kind=="variant_decl"&&ident(n.value)&&variants.insert(n.value).second,"invalid/duplicate variant");fields(n.children);}
            } else if(d.kind=="global") {
                shape(id,"global",1);need(scalar(d.second)&&!d.result_mode.empty(),"invalid module scalar type/permission");binding(d,d.second);globals[d.value]=id;
                if(!u.origins.empty()) need(d.value.starts_with("km_"+std::to_string(file_of(d))+"_"),"global/module provenance mismatch");
            } else {
                shape(id,"function",2);
                if(u.next_syntax&&!u.origins.empty()) need(d.value=="main"?file_of(d)==0:d.value.starts_with("km_"+std::to_string(file_of(d))+"_"),"function/module provenance mismatch");
                need(d.second=="unit"||value(d.second),"invalid return type"); if(array_type(d.second)) layout(d.second,1);Function f;f.result=d.second;f.owns_result=d.result_mode=="own";need(!f.owns_result||(u.project_syntax&&resource(d.second)),"invalid owned result declaration");std::unordered_set<std::string> params;
                for(auto p:list(d.children[0])) {const auto &n=at(p);need(n.kind=="param"||n.kind=="borrow_param"||n.kind=="own_param"||n.kind=="mut_param","invalid parameter kind");shape(p,n.kind,0);
                    const bool borrowed=n.kind=="borrow_param",owned=n.kind=="own_param",mutable_param=n.kind=="mut_param";need(!(borrowed||owned)||(u.project_syntax&&resource(n.second)),"invalid borrowed parameter type/syntax");
                    need(!mutable_param||(u.next_syntax&&records.contains(n.second)),"invalid mutable parameter type/syntax");
                    need(ident(n.value)&&params.insert(n.value).second,"invalid/duplicate parameter");binding(n,n.second);f.arguments.push_back(n.second);f.borrows.push_back(borrowed);f.takes.push_back(owned);f.mutables.push_back(mutable_param);}
                list(d.children[1]); functions[d.value]=std::move(f);function_files[d.value]=file_of(d);
            }
        }
        if(u.next_syntax) for(const auto &[child,parent]:u.nested_parents) {
            need(functions.contains(child)&&functions.contains(parent)&&child!=parent&&function_files.at(child)==function_files.at(parent),"invalid nested-function parent");
            auto name=child;uint32_t depth=0;while(u.nested_parents.contains(name)) {need(++depth<=64,"nested parent cycle/depth exceeded");name=u.nested_parents.at(name);}
        }
        if(u.next_syntax) for(const auto &name:u.public_functions) need(functions.contains(name),"export refers to missing function");
        for(auto id:u.roots) if(at(id).kind=="struct"||at(id).kind=="union") layout(at(id).value,1);
        if(u.next_syntax) {
            const auto files=u.origins.empty()?size_t(1):u.files.size();
            need(u.module_order.size()==files&&u.module_dependencies.size()==files&&files<=64,"invalid module initialization graph size");
            std::vector<size_t> position(files,files);size_t edges=0;
            for(size_t i=0;i<files;++i) {const auto f=u.module_order[i];need(f<files&&position[f]==files,"invalid module initialization permutation");position[f]=i;}
            for(size_t i=0;i<files;++i) for(const auto dependency:u.module_dependencies[i]) {need(++edges<=256&&dependency<files&&position[dependency]<position[i],"invalid module initialization dependency order");}
            List expected;for(const auto file:u.module_order) for(const auto id:u.roots) if(at(id).kind=="global"&&file_of(at(id))==file) expected.push_back(id);
            need(u.global_order==expected,"invalid global initialization order/coverage");
            initializing_global=true;
            for(const auto id:u.global_order) {const auto &g=at(id);current_file=file_of(g);Scope empty;need(expression(g.children[0],empty)==g.second,"global initializer type mismatch");initialized_globals.insert(g.value);}
            initializing_global=false;
        }
        need(functions.contains("main")&&functions.at("main").arguments.empty()&&functions.at("main").result=="i64","invalid entry point");
        for(auto id:u.roots) {
            const auto &f=at(id);if(f.kind!="function") continue;current_file=file_of(f);current_function=f.value;Scope env;
            for(auto p:list(f.children[0])) {const auto &n=at(p);env[n.value]={n.second,n.symbol,n.kind=="borrow_param"||n.kind=="own_param",n.kind=="own_param"};}
            const auto total=block(list(f.children[1]),env,f.second,true,functions.at(f.value).owns_result);need(f.second=="unit"||total,"missing total return");
        }
    }
};
