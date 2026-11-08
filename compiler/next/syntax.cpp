#include <cctype>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
struct T{std::string k,v;int l,c;};
struct Fail:std::runtime_error{using std::runtime_error::runtime_error;};
static bool id0(unsigned char c){return std::isalpha(c)||c=='_';}
static bool idn(unsigned char c){return std::isalnum(c)||c=='_';}
static std::vector<T> lex(const std::string &s){
    static const std::set<std::string> kw={"use","as","exports","func","if","elseif","else","while","end","return","defer","move","and","or","not","true","false","enum","match","case","then","view","vector","struct","for","in","break","continue","map","set"};
    std::vector<T> out;int l=1,col=1;
    for(size_t i=0;i<s.size();){
        unsigned char ch=s[i];
        if(ch=='\r'){++i;continue;}
        if(ch=='\n'){++i;++l;col=1;continue;}
        if(ch==' '||ch=='\t'){++i;++col;continue;}
        if(ch=='-'&&i+1<s.size()&&s[i+1]=='-'){while(i<s.size()&&s[i]!='\n')++i;continue;}
        if(ch=='@'){
            size_t j=i+1;while(j<s.size()&&idn(s[j]))++j;
            std::string v=s.substr(i,j-i);
            if(v!="@p"&&v!="@s"&&v!="@b"&&v!="@o"&&v!="@m"&&v!="@r"&&v!="@w") throw Fail("unknown permission "+v+" at "+std::to_string(l)+":"+std::to_string(col));
            out.push_back({"Perm",v,l,col});col+=int(j-i);i=j;continue;
        }
        if(id0(ch)){
            size_t j=i+1;while(j<s.size()&&idn(s[j]))++j;
            std::string v=s.substr(i,j-i);
            if(v=="local"||v=="function"||v=="var"||v=="let"||v=="const"||v=="pub"||v=="public"||v=="private"||v=="export"||v=="mut"||v=="readonly"||v=="scoped"||v=="borrow"||v=="own"||v=="do")
                throw Fail("legacy keyword '"+v+"' is invalid in next syntax at "+std::to_string(l)+":"+std::to_string(col));
            out.push_back({kw.count(v)?"Kw":"Id",v,l,col});col+=int(j-i);i=j;continue;
        }
        if(std::isdigit(ch)){
            size_t j=i+1;while(j<s.size()&&(std::isalnum(unsigned(s[j]))||s[j]=='_'||(s[j]=='.'&&j+1<s.size()&&std::isdigit(unsigned(s[j+1])))))++j;
            out.push_back({"Num",s.substr(i,j-i),l,col});col+=int(j-i);i=j;continue;
        }
        if(ch=='"'){
            size_t j=i+1;while(j<s.size()&&s[j]!='"'&&s[j]!='\n'){if(s[j]=='\\'&&j+1<s.size())++j;++j;}
            if(j>=s.size()||s[j]!='"') throw Fail("unterminated string at "+std::to_string(l)+":"+std::to_string(col));
            out.push_back({"Str",s.substr(i+1,j-i-1),l,col});col+=int(j-i+1);i=j+1;continue;
        }
        if(ch==':'&&i+1<s.size()&&s[i+1]==':'){out.push_back({"Sym","::",l,col});i+=2;col+=2;continue;}
        if(ch==':'&& col>1&&(s[i-1]==' '||s[i-1]=='\t'||s[i-1]=='\n'))
            throw Fail("`:` must immediately follow the target with no leading space at "+std::to_string(l)+":"+std::to_string(col));
        if(ch=='-'&&i+1<s.size()&&s[i+1]=='>')
            throw Fail("`->` is not part of next syntax at "+std::to_string(l)+":"+std::to_string(col)+"; use `: Type`");
        if(ch=='.'&&i+1<s.size()&&s[i+1]=='.'){out.push_back({"Sym","..",l,col});i+=2;col+=2;continue;}
        if((ch=='='||ch=='!'||ch=='<'||ch=='>')&&i+1<s.size()&&s[i+1]=='='){
            out.push_back({"Sym",s.substr(i,2),l,col});i+=2;col+=2;continue;
        }
        if(ch=='=') throw Fail("`=` is not part of next syntax at "+std::to_string(l)+":"+std::to_string(col)+"; use `:`");
        std::string one(1,char(ch));
        if(std::string(":;,.()[]{}+-*/%<>").find(ch)==std::string::npos)
            throw Fail("unexpected character '"+one+"' at "+std::to_string(l)+":"+std::to_string(col));
        out.push_back({"Sym",one,l,col});++i;++col;
    }
    out.push_back({"Eof","",l,col});for(size_t q=0;q+1<out.size();++q) if(out[q].k=="Kw"&&(out[q].v=="view"||out[q].v=="vector"||out[q].v=="map"||out[q].v=="set"||out[q].v=="string"||out[q].v=="spool")&&out[q+1].v==".") out[q].k="Id";
    for(size_t q=0;q+2<out.size();++q) if(out[q].v=="."&&out[q+1].k=="Kw"&&(out[q+2].v=="("||out[q+2].v=="<")&&q>0&&out[q-1].k=="Id") out[q+1].k="Id";
    return out;
}
struct ExportInfo{std::string perm,kind;};
struct ModInfo{std::map<std::string,ExportInfo> exports;std::set<std::string> priv;};
static std::set<fs::path> loading;
static void parse_file(const fs::path &p,std::map<fs::path,ModInfo> &mods);
struct Parser{
    std::vector<T> t;size_t i=0;fs::path file;std::map<fs::path,ModInfo> &mods;ModInfo self;
    std::map<std::string,fs::path> aliases;std::vector<std::set<std::string>> locals;bool loop=false;
    const T& cur()const{return t[i];}
    bool at(const std::string &v)const{return t[i].k!="Str"&&t[i].k!="Num"&&t[i].v==v;}
    T eat(const std::string &v=""){
        if(!v.empty()&&t[i].v!=v) throw Fail(file.filename().string()+":"+std::to_string(t[i].l)+":"+std::to_string(t[i].c)+" expected '"+v+"', got '"+(t[i].v.empty()?t[i].k:t[i].v)+"'");
        return t[i++];
    }
    T id(){if(cur().k!="Id") throw Fail(file.filename().string()+":"+std::to_string(cur().l)+":"+std::to_string(cur().c)+" expected identifier");return t[i++];}
    void type(){
        if(at("[")){eat("[");type();eat(";");if(cur().k!="Num")throw Fail("expected array size");++i;eat("]");return;}
        if(at("vector")||at("view")){++i;eat("<");type();eat(">");return;}
        if(at("map")){++i;eat("<");type();eat(",");type();eat(">");return;}
        if(at("set")){++i;eat("<");type();eat(">");return;}
        id();
        while(at(".")){eat(".");id();}
    }
    bool known(const std::string &n)const{
        for(auto it=locals.rbegin();it!=locals.rend();++it) if(it->count(n)) return true;
        return self.priv.count(n)||self.exports.count(n);
    }
    bool generic_call()const{
        size_t j=i;int depth=0;
        while(t[j].v!="<"&&j<t.size()) return false;
        for(;j<t.size();++j){
            const std::string &v=t[j].v;
            if(v=="<") ++depth;
            else if(v==">"&&--depth==0) return t[j+1].v=="(";
            else if(!(t[j].k=="Id"||t[j].k=="Kw"||t[j].k=="Num"||v=="["||v=="]"||v==";")) return false;
        }
        return false;
    }
    void expr(){
        if(at("-")||at("not")) ++i;
        if(at("move")) ++i;
        if(at("(")){eat("(");expr();eat(")");}
        else if(at("[")){
            eat("[");expr();
            if(at(";")){eat(";");expr();}
            else while(at(",")){eat(",");expr();}
            eat("]");
        }
        else if(cur().k=="Num"||cur().k=="Str"||at("true")||at("false")) ++i;
        else if(at("vector")||at("view")||cur().k=="Id"){
            std::string a=cur().v;++i;
            if(at(".")&&(a=="spool"||a=="map"||a=="set"||a=="vector"||a=="view"||a=="string"||a=="int_vector")&&i+2<t.size()&&t[i+1].k=="Id"&&(t[i+2].v=="<"||t[i+2].v=="(")&&!aliases.count(a)&&!known(a)){a+="_"+t[i+1].v;i+=2;}
            if(a=="map_new"&&at("<")){eat("<");type();eat(",");type();eat(">");eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");}
            else if(a=="set_new"&&at("<")){eat("<");type();eat(">");eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");}
            else if(generic_call()){eat("<");type();eat(">");eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");}
            else if(at(".")){
                while(at(".")){
                    eat(".");std::string b=id().v;
                    if(aliases.count(a)){
                        const auto &m=mods.at(aliases[a]);
                        if(!m.exports.count(b)) throw Fail(file.filename().string()+": '"+b+"' is not exported by "+a);
                        if(at("(")&&m.exports.at(b).kind!="func")
                            throw Fail(file.filename().string()+": '"+a+"."+b+"' is not a function");
                    }
                    if(at("(")){eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");}
                    a.clear();
                }
            }else if(at("(")){
                eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");
            }else if(at("[")){
                eat("[");expr();eat("]");
            }
        }else throw Fail(file.filename().string()+":"+std::to_string(cur().l)+":"+std::to_string(cur().c)+" expected expression");
        while(at(".")){eat(".");id();if(at("(")){eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");}}
        while(at("+")||at("-")||at("*")||at("/")||at("%")||at("..")||at("==")||at("!=")||at("<")||at("<=")||at(">")||at(">=")||at("and")||at("or")||at("[")){
            if(at("[")){eat("[");expr();eat("]");}
            else{++i;expr();}
        }
    }
    void binding(bool top,const std::string &perm){
        std::string name=id().v;
        if(cur().k=="Id"||at("[")||at("vector")||at("view")||at("map")||at("set")) type();
        eat(":");expr();eat(";");
        if(top){if(perm=="@p"||perm=="@s") self.priv.insert(name); else self.exports[name]={perm,"var"};}
        else locals.back().insert(name);
    }
    void parseIf(){
        expr();eat("{");locals.push_back({});while(!at("}")) stmt();locals.pop_back();eat("}");
        if(at("elseif")){eat("elseif");parseIf();}
        else if(at("else")){eat("else");eat("{");locals.push_back({});while(!at("}")) stmt();locals.pop_back();eat("}");}
    }
    void stmt(){
        if(at("@p")||at("@s")){
            std::string p=eat().v;
            if(p=="@p"&&at("func")){func(false,"@p");return;}
            binding(false,p);return;
        }
        if(at("func")) throw Fail("nested function inside block must be marked `@p func`");
        if(at("@r")||at("@w")) throw Fail("export permissions are only valid inside top-level `exports{...};`");
        if(at("if")){eat("if");parseIf();eat(";");return;}
        if(at("while")){eat("while");expr();eat("{");locals.push_back({});const bool outer=loop;loop=true;while(!at("}")) stmt();loop=outer;locals.pop_back();eat("}");eat(";");return;}
        if(at("match")){
            eat("match");expr();eat("then");
            while(at("case")){
                eat("case");id();while(at(".")){eat(".");id();}eat("(");
                locals.push_back({});if(!at(")")){locals.back().insert(id().v);while(at(",")){eat(",");locals.back().insert(id().v);}}eat(")");eat("then");
                while(!at("case")&&!at("end")) stmt();
                locals.pop_back();
            }
            eat("end");eat(";");return;
        }
        if(at("return")){eat("return");if(!at(";")) expr();eat(";");return;}
        if(at("break")||at("continue")){if(!loop) throw Fail("break/continue outside a loop");++i;eat(";");return;}
        if(at("for")){
            eat("for");const auto name=id().v;eat("in");
            if(at("..")) throw Fail("range loops need a start value");
            expr();
            if(at("..")){eat("..");expr();}
            locals.back().insert(name);
            eat("{");const bool outer=loop;loop=true;while(!at("}")) stmt();loop=outer;eat("}");eat(";");return;
        }
        if(at("defer")){eat("defer");expr();eat(";");return;}
        if(cur().k=="Id"){
            std::string a=id().v;
            if(at(".")){
                const std::string root=a;
                while(at(".")){
                    eat(".");std::string b=id().v;
                    if(at(":")){
                        if(aliases.count(root)){
                            const auto &m=mods.at(aliases[root]);
                            if(!m.exports.count(b)) throw Fail("'"+b+"' is not exported by "+root);
                            if(m.exports.at(b).perm!="@w") throw Fail("'"+root+"."+b+"' is read-only (@r) from importing file");
                        } else if(!known(root)) throw Fail("assignment to undeclared variable '"+root+"' (declarations require @p/@s)");
                        eat(":");expr();eat(";");return;
                    }
                    if(at("(")){eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");}
                }
                eat(";");return;
            }
            if(at("[")){eat("[");expr();eat("]");}
            if(at(":")){
                if(!known(a)) throw Fail("assignment to undeclared variable '"+a+"' (declarations require @p/@s)");
                eat(":");expr();eat(";");return;
            }
            eat("(");if(!at(")")){expr();while(at(",")){eat(",");expr();}}eat(")");eat(";");return;
        }
        throw Fail(file.filename().string()+":"+std::to_string(cur().l)+":"+std::to_string(cur().c)+" unexpected token '"+cur().v+"' in statement");
    }
    void func(bool top,const std::string &perm){
        eat("func");std::string name=id().v;
        if(top){if(perm=="@p") self.priv.insert(name); else self.exports[name]={perm,"func"};}
        else locals.back().insert(name);
        locals.push_back({});
        if(at("::")){
            eat("::");
            for(;;){
                if(at("@b")||at("@o")||at("@m")) ++i;
                locals.back().insert(id().v);
                if(at("[")){eat("[");type();eat("]");}
                else{eat(":");type();}
                if(!at(",")) break;
                eat(",");
            }
        }
        if(at(":")){eat(":");if(at("@o")) ++i;type();}
        eat("{");while(!at("}")) stmt();eat("}");eat(";");locals.pop_back();
    }
    void parseStruct(const std::string &perm){
        eat("struct");std::string name=id().v;
        if(!perm.empty()){if(perm=="@p") self.priv.insert(name); else self.exports[name]={perm,"struct"};}
        eat("{");std::set<std::string> fields;
        while(!at("}")){const auto f=id().v;eat(":");type();eat(";");if(!fields.insert(f).second) throw Fail("duplicate struct field "+f);}
        eat("}");eat(";");
    }
    void parseEnum(bool top,const std::string &perm){
        eat("enum");std::string name=id().v;
        if(top){if(perm=="@p") self.priv.insert(name); else self.exports[name]={perm,"enum"};}
        while(!at("end")){
            id();eat("(");if(!at(")")){id();eat(":");type();while(at(",")){eat(",");id();eat(":");type();}}eat(")");eat(";");
        }
        eat("end");eat(";");
    }
    void unit(){
        while(!at("")&&cur().k!="Eof"){
            if(at("use")){
                eat("use");
                std::string rel;
                while(!at("as")&&!at(";")){if(cur().k=="Eof") throw Fail("unterminated use");rel+=cur().v;++i;}
                const bool package=rel.size()<4||rel.substr(rel.size()-3)!=".aw";
                std::string alias=at("as")?(eat("as"),id().v):(package?rel:fs::path(rel).stem().string());
                eat(";");
                fs::path target=fs::weakly_canonical(file.parent_path()/rel);
                if(package){
                    // bare name: packages/NAME/NAME.aw under the nearest enclosing project root, no fallback to local files
                    fs::path dir=file.parent_path();target.clear();
                    for(int up=0;up<32;++up){
                        const fs::path candidate=dir/"packages"/rel/(rel+".awpkg");
                        if(fs::is_regular_file(candidate)){target=fs::weakly_canonical(dir/"packages"/rel/(rel+".aw"));break;}
                        if(!dir.has_parent_path()||dir.parent_path()==dir) break;
                        dir=dir.parent_path();
                    }
                    if(target.empty()) throw Fail("package '"+rel+"' is not installed (expected packages/"+rel+"/"+rel+".awpkg)");
                }
                if(!mods.count(target)){
                    if(!fs::is_regular_file(target)) throw Fail("imported file not loaded before user: "+target.string());
                    if(loading.count(target)||loading.size()>=64) throw Fail("import cycle or import depth limit at "+target.string());
                    parse_file(target,mods);
                }
                aliases[alias]=target;
            }else if(at("exports")){
                eat("exports");eat("{");
                while(!at("}")){
                    if(!at("@r")&&!at("@w")) throw Fail("exports block only accepts @r or @w declarations, got '"+cur().v+"'");
                    std::string p=eat().v;
                    if(at("func")){if(p!="@r") throw Fail("exported functions use @r");func(true,p);}
                    else if(at("enum")){if(p!="@r") throw Fail("exported enums use @r");parseEnum(true,p);}
                    else if(at("struct")){if(p!="@r") throw Fail("exported structs use @r");parseStruct(p);}
                    else binding(true,p);
                }
                eat("}");eat(";");
            }else if(at("@p")||at("@s")){
                std::string p=eat().v;
                if(p=="@p"&&at("func")) func(true,"@p");
                else if(p=="@p"&&at("enum")) parseEnum(true,"@p");
                else if(p=="@p"&&at("struct")) parseStruct("@p");
                else binding(true,p);
            }else if(at("func")) func(true,"@p");
            else if(at("enum")) parseEnum(true,"@p");
            else if(at("struct")) parseStruct("@p");
            else if(at("@r")||at("@w")) throw Fail("@r/@w must appear inside `exports{...};`");
            else throw Fail(file.filename().string()+":"+std::to_string(cur().l)+":"+std::to_string(cur().c)+" top-level declarations require @p/@s, func, enum, struct, use, or exports{...};");
        }
        mods[fs::weakly_canonical(file)]=self;
    }
};
static void parse_file(const fs::path &p,std::map<fs::path,ModInfo> &mods){
    std::ifstream in(p);if(!in) throw Fail("cannot open "+p.string());
    std::ostringstream ss;ss<<in.rdbuf();
    fs::path canon=fs::weakly_canonical(p);
    loading.insert(canon);
    Parser P{lex(ss.str()),0,p,mods,{},{},{}};P.unit();
    loading.erase(canon);
}
static void expect_fail(const std::string &name,const std::string &src,std::map<fs::path,ModInfo> mods={}){
    bool failed=false;
    try{Parser P{lex(src),0,"/virtual/"+name+".aw",mods,{},{},{}};P.unit();}
    catch(const Fail&){failed=true;}
    if(!failed) throw Fail("expected failure for case: "+name);
}
int main(int argc,char **argv){
    try{
        std::map<fs::path,ModInfo> mods;
        for(int i=1;i<argc;++i) parse_file(argv[i],mods);
        expect_fail("legacy_local","func main: i64 { local x: i64: 1; return x; };");
        expect_fail("legacy_equal","func main: i64 { @p x: 1; x = 2; return x; };");
        expect_fail("spaced_colon","func main: i64 { @p x : 1; return x; };");
        expect_fail("missing_semi","func main: i64 { @p x: 1 return x; };");
        expect_fail("missing_func_end_semi","func main: i64 { return 0; }");
        expect_fail("old_paren_func","func main(): i64 { return 0; };");
        expect_fail("old_arrow_return","func main -> i64 { return 0; };");
        expect_fail("undeclared_assign","func main: i64 { x: 1; return 0; };");
        expect_fail("export_outside_block","@r x: 1; func main: i64 { return 0; };");
        expect_fail("private_inside_exports","exports{ @p x: 1; };");
        expect_fail("nested_func_without_at_p","func main: i64 { func inner: i64 { return 1; }; return inner(); };");
        std::map<fs::path,ModInfo> m;
        {Parser P{lex("@p secret: 7;\nexports{\n @r ro: 1;\n @w rw: 2;\n @r func get: i64 { return secret; };\n};\n"),0,"/virtual/lib.aw",m,{},{},{}};P.unit();}
        expect_fail("write_readonly_export","use lib.aw as lib;\nfunc main: i64 { lib.ro: 9; return 0; };",m);
        expect_fail("access_private_from_importer","use lib.aw as lib;\nfunc main: i64 { return lib.secret; };",m);
        std::cout<<"next syntax prototype: "<<(argc-1)<<" files + 13 negative checks passed\n";
        return 0;
    }catch(const std::exception &e){std::cerr<<"ERROR: "<<e.what()<<"\n";return 1;}
}
