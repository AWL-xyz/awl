#include "kparse.h"
#include <algorithm>
#include <chrono>
#include <charconv>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <functional>
#include <memory>
#include <optional>
#include <queue>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace {
using Id=uint32_t;
using List=std::vector<Id>;
constexpr uint32_t max_depth=64,max_tokens=100000,max_nodes=200002;
struct Node {
    std::string kind;
    uint32_t token;
    std::string value_kind="null",value,second,literal;
    List children;
    std::string type{},symbol{},result_mode{};
};
struct Diagnostic { std::string code,message; uint32_t token; };
struct Failure { Diagnostic diagnostic; };
struct Stop {};
#include "ktext.inc"
#include "karrays.inc"
struct Origin { uint32_t file,start,end; };
struct Unit {
    bool project_syntax=true,aesop_syntax=true;
    std::unordered_set<std::string> public_functions;
    std::unordered_set<Id> mutable_arguments;
    std::unordered_set<uint32_t> dotted_tokens;
    std::unordered_map<std::string,std::string> nested_parents;
    std::unordered_map<uint32_t,std::unordered_map<std::string,std::string>> global_names;
    List global_order;
    std::vector<uint32_t> module_order{0};
    std::vector<std::vector<uint32_t>> module_dependencies{{}};
    std::vector<std::string> files;
    std::vector<uint32_t> file_lengths;
    std::vector<Origin> origins;
    std::unordered_map<std::string,std::string> display_names;
    std::string source;
    std::vector<size_t> bytes;
    std::vector<AwlLexToken> tokens;
    std::vector<Node> arena;
    List roots;
    std::vector<Diagnostic> diagnostics;
    std::string json,report,c_output;
    bool checked=false;
    std::string text(uint32_t i) const {
        if(i+1==tokens.size()) return "<eof>";
        const auto &t=tokens.at(i);
        return source.substr(bytes.at(t.start),bytes.at(t.end)-bytes.at(t.start));
    }
};
#include "kgeneric-types.inc"
#include "kmap-types.inc"
#include "kplatform-signatures.inc"
#include "kmath.inc"
const std::unordered_set<std::string> integers={"i8","i16","i32","i64","u8","u16","u32","u64"};
const std::unordered_set<std::string> reserved={"import","as","function","local","if","then","else","end","while","do","return","true","false","and","or","not","bool","unit","string","spool","struct","union","match","case","i8","i16","i32","i64","u8","u16","u32","u64"};
bool identifier(const std::string &s) {
    auto first=[](char c){ return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||c=='_'; };
    if(s.empty()||!first(s[0])||reserved.contains(s)) return false;
    return std::all_of(s.begin()+1,s.end(),[&](char c){return first(c)||(c>='0'&&c<='9');});
}
std::pair<std::string,std::string> number(const std::string &s) {
    size_t n=0;
    while(n<s.size()&&s[n]>='0'&&s[n]<='9') ++n;
    if(!n) return {};
    auto type=n==s.size()?std::string("i64"):s.substr(n);
    if(!integers.contains(type)) return {};
    auto value=s.substr(0,n); auto first=value.find_first_not_of('0');
    value=first==std::string::npos?"0":value.substr(first);
    return {value,type};
}
std::string minimum_magnitude(const std::string &type) {
    if(type=="i8") return "128";
    if(type=="i16") return "32768";
    if(type=="i32") return "2147483648";
    if(type=="i64") return "9223372036854775808";
    return {};
}
class Parser {
    Unit &u;
    uint32_t position=0,depth=0,nested_serial=0;
    struct FunctionScope {std::string function_name;std::unordered_map<std::string,std::string> helpers;std::unordered_set<std::string> locals;};
    std::vector<FunctionScope> function_scopes;
    bool direct_function_body=false;
    std::vector<std::vector<std::pair<size_t,std::string>>> local_logs;
    void local_name(const std::string &name) {
        const auto index=function_scopes.size()-1;
        if(function_scopes.back().locals.insert(name).second&&!local_logs.empty()) local_logs.back().emplace_back(index,name);
    }
    std::string function_keyword() const {return "func";}
    std::string peek() const { return u.text(position); }
    uint32_t pop() { const auto t=position; if(position+1<u.tokens.size()) ++position; return t; }
    [[noreturn]] void error(uint32_t token,std::string message,std::string code="E100") const { throw Failure{{std::move(code),std::move(message),token}}; }
    [[noreturn]] void fail(const std::string &message) const { error(position,message+"; got '"+peek()+"'"); }
    uint32_t take(const std::string &s) { if(peek()!=s) fail("expected '"+s+"'"); return pop(); }
    uint32_t ident() { if((u.aesop_syntax&&(peek()=="elseif"||peek()=="enum"||peek()=="struct"||peek()=="for"||peek()=="in"||peek()=="break"||peek()=="continue"||peek()=="map"||peek()=="set"||peek()=="view"||peek()=="vector"||peek()=="f64"||peek()=="pi"||peek()=="tau"||peek()=="func"||peek()=="text"||peek()=="use"||peek()=="exports"||peek().starts_with("kn_nested_")))||!identifier(peek())||(u.project_syntax&&(peek()=="defer"||peek()=="scoped"||peek()=="borrow"||peek()=="int_vector"))) fail("expected identifier"); return pop(); }
    void nonlocal_value(const std::string &name,uint32_t token) {
        if(!u.aesop_syntax) return;
        for(size_t i=function_scopes.size();i>0;--i) {
            const auto &scope=function_scopes[i-1];
            if(scope.locals.contains(name)) {if(i==function_scopes.size()) return;error(token,"parent-local capture is not implemented; pass "+name+" explicitly","E232");}
            if(scope.helpers.contains(name)) error(token,"nested func names are not variable values","E232");
        }
    }
    void colon() {
        if(peek()!=":") error(position,"Aesop syntax requires ':' instead of '='","E110");
        if(position==0||u.tokens[position-1].end!=u.tokens[position].start) error(position,"no whitespace allowed before ':'","E110");
        pop();
    }
    std::string called(const std::string &name,uint32_t token) {
        if(u.aesop_syntax) for(auto it=function_scopes.rbegin();it!=function_scopes.rend();++it) {
            if(it->helpers.contains(name)) return it->helpers.at(name);
            if(it->locals.contains(name)) error(token,"local value is not a callable function: "+name,"E110");
        }
        return name;
    }
    uint32_t array_count(uint32_t token) {
        const auto text=u.text(pop());
        if(text.empty()||text.size()>4||text.find_first_not_of("0123456789")!=std::string::npos) error(token,"array length must be a decimal constant from 1 to 1024");
        const auto count=std::stoul(text);
        if(!count||count>1024) error(token,"array length must be from 1 to 1024");
        return static_cast<uint32_t>(count);
    }
    std::string type() {
        if(u.aesop_syntax&&peek()=="view") {Guard guard(*this);const auto t=pop();take("<");const auto element=type();take(">");if(!generic_element(element)) error(t,"view elements must be scalar integer, bool, f64 or text");return "view<"+element+">";}
        if(u.aesop_syntax&&peek()=="vector") {Guard guard(*this);const auto t=pop();take("<");const auto element=type();take(">");if(!generic_element(element)) error(t,"vector elements must be scalar integer, bool, f64 or text");return "vector<"+element+">";}
        if(u.aesop_syntax&&(peek()=="map"||peek()=="set")) {
            Guard guard(*this);const auto t=pop();take("<");const auto first=type();
            if(u.text(t)=="set") {take(">");if(!set_type(set_name(first))) error(t,"set elements must be an integer, bool or text");return set_name(first);}
            take(",");const auto second=type();take(">");
            if(!map_type(map_name(first,second))) error(t,"map keys are an integer, bool or text and values are a scalar or text");
            return map_name(first,second);
        }
        if(u.aesop_syntax&&peek()=="f64") return u.text(pop());
        if(u.aesop_syntax&&peek()=="text") {pop();return "string";}
        if(u.project_syntax&&peek()=="[") {
            Guard guard(*this);const auto t=pop();const auto element=type();take(";");const auto count=array_count(t);take("]");
            auto name=array_name(element,count);if(name.size()>128) error(t,"array type exceeds 128 characters","E007");return name;
        }
        if(integers.contains(peek())||peek()=="bool"||peek()=="unit"||peek()=="string"||peek()=="spool"||(u.project_syntax&&peek()=="int_vector")) return u.text(pop());
        auto name=u.text(ident()); if(u.project_syntax&&peek()==".") {pop();name+="."+u.text(ident());} return name; }
    Id add(std::string kind,uint32_t token,List children={},std::string value_kind="null",std::string value={},std::string second={},std::string literal={}) {
        if(u.arena.size()>=max_nodes) error(token,"IR node budget exceeded","E007");
        const auto id=static_cast<Id>(u.arena.size());
        u.arena.push_back({std::move(kind),token,std::move(value_kind),std::move(value),std::move(second),std::move(literal),std::move(children)});
        return id;
    }
    Id list(List values) { return add("#list",0,std::move(values)); }
    struct Guard {
        Parser &p;
        explicit Guard(Parser &parser):p(parser) {
            if(++p.depth>max_depth) { --p.depth; p.error(p.position,"syntax nesting exceeds 64","E002"); }
        }
        ~Guard() { --p.depth; }
    };
    void record(const Diagnostic &d) {
        if(d.code.starts_with("E00")) { u.diagnostics={d}; throw Stop{}; }
        u.diagnostics.push_back(d);
        if(u.diagnostics.size()>=20) throw Stop{};
    }
    List fields(bool comma) {
        List result;
        if(comma&&peek()==")") return result;
        while(true) {
            const auto f=ident(); if(u.aesop_syntax) colon(); else take(":"); const auto ty=type();
            result.push_back(add("field_decl",f,{},"pair",u.text(f),ty));
            if(!comma||peek()!=",") break;
            pop();
        }
        return result;
    }
    Id structure() {
        const auto t=take("struct"); const auto name=u.text(ident()); List members;
        take("{");
        while(peek()!="}") {if(peek()==";") error(position,"empty struct field statement","E110");const auto f=fields(false);members.insert(members.end(),f.begin(),f.end());take(";");}
        take("}");take(";");return add("struct",t,std::move(members),"string",name);
    }
    Id tagged_union() {
        const auto t=take("enum"); const auto name=u.text(ident()); List variants;
        while(peek()!="end") {
            if(peek()==";") {if(u.aesop_syntax) error(position,"empty enum variants are not allowed","E110");pop();continue;}
            const auto v=ident(); take("("); auto payload=fields(true); take(")"); if(u.aesop_syntax) take(";");
            variants.push_back(add("variant_decl",v,std::move(payload),"string",u.text(v)));
        }
        take("end"); if(u.aesop_syntax) take(";"); return add("union",t,std::move(variants),"string",name);
    }
    Id function(bool nested=false) {
        const auto t=take(function_keyword()); const auto name_token=ident();auto name=u.text(name_token);
        if(nested) {
            if(function_scopes.empty()||!direct_function_body) error(t,"nested helpers must be declared directly in their enclosing function body","E110");
            auto &scope=function_scopes.back();
            if(scope.helpers.contains(name)||scope.locals.contains(name)) error(name_token,"duplicate nested helper/binding "+name,"E210");
            const auto linked="kn_nested_"+std::to_string(nested_serial++);u.nested_parents[linked]=scope.function_name;scope.helpers[name]=linked;name=linked;
        }
        function_scopes.emplace_back();function_scopes.back().function_name=name;
        bool result_owned=false;std::string ret;
        if(peek()=="[") {
            pop();
            if(peek()=="@") {pop();take("o");result_owned=true;}
            ret=type();take("]");
        }
        List parameters;
        if(peek()=="::") {
            pop();
            while(true) {
                bool borrowed=false,owned=false,mutable_param=false;
                if(peek()=="@") {pop();const auto mode=pop();borrowed=u.text(mode)=="b";owned=u.text(mode)=="o";mutable_param=u.text(mode)=="m";if(!borrowed&&!owned&&!mutable_param) error(mode,"argument modifiers are @b, @o or @m","E110");}
                const auto p=ident();std::string ty;
                if(peek()=="[") {pop();const auto element=type();take("]");if(!generic_element(element))error(p,"vector argument elements must be scalar or text");ty="vector<"+element+">";}
                else {colon();ty=type();if(generic_type(ty))error(p,"vector arguments use name[element]","E110");}
                function_scopes.back().locals.insert(u.text(p));
                parameters.push_back(add(owned?"own_param":borrowed?"borrow_param":mutable_param?"mut_param":"param",p,{},"pair",u.text(p),ty));
                if(peek()!=",") break;
                pop();
            }
        }
        if(peek()==":"||peek()=="->") error(position,"Aesop function results follow the name: func name[type] :: arguments { ... };","E110");
        take("{");auto body=block({"}"},true);take("}");take(";");function_scopes.pop_back();
        const auto params_id=list(std::move(parameters)); const auto body_id=list(std::move(body));
        const auto id=add("function",t,{params_id,body_id},"pair",name,ret);u.arena[id].result_mode=result_owned?"own":"";return id;
    }
    List block(const std::unordered_set<std::string> &stops,bool direct=false) {
        struct Restore {bool &value;bool old;~Restore(){value=old;}} restore{direct_function_body,direct_function_body};direct_function_body=direct;
        local_logs.emplace_back();
        struct LocalRestore {Parser &p;~LocalRestore(){for(const auto &[index,name]:p.local_logs.back()) p.function_scopes[index].locals.erase(name);p.local_logs.pop_back();}} locals_restore{*this};
        Guard guard(*this); List body;
        while(!stops.contains(peek())) {
            if(peek()=="<eof>"||peek()==function_keyword()||peek()=="struct"||peek()=="union"||(u.aesop_syntax&&peek()=="enum")) fail("unterminated block");
            if(peek()==";") {if(u.aesop_syntax) error(position,"empty commands/double semicolons are not allowed","E110"); pop(); continue; }
            const auto start=position;
            try { const auto id=statement();if(id!=UINT32_MAX) {if(u.aesop_syntax) take(";");body.push_back(id);} }
            catch(const Failure &e) {
                if(u.aesop_syntax) {u.diagnostics={e.diagnostic};throw Stop{};}
                record(e.diagnostic);
                if(position==start) pop();
                while(!stops.contains(peek())&&peek()!="<eof>"&&peek()!=function_keyword()&&peek()!="struct"&&peek()!="union"&&peek()!=";") {
                    const auto s=peek();
                    if(u.tokens[position].line>u.tokens[start].line&&(s=="local"||s=="return"||s=="if"||s=="while"||s=="match"||(u.project_syntax&&(s=="defer"||s=="scoped")))) break;
                    pop();
                }
                if(peek()==";") pop();
            }
        }
        return body;
    }
    Id match(uint32_t t) {
        const auto value=expression(); take("then"); List arms;
        while(peek()=="case") {
            const auto c=pop(); auto owner=u.text(ident()); take("."); auto variant=u.text(ident());
            if(u.project_syntax&&peek()==".") {pop();owner+="."+variant;variant=u.text(ident());}
            take("("); List binders;
            if(peek()!=")") {
                while(true) {
                    const auto b=ident(); binders.push_back(add("pattern_bind",b,{},"string",u.text(b)));
                    if(peek()!=",") break;
                    pop();
                }
            }
            take(")"); take("then");
            std::vector<std::string> introduced;
            if(u.aesop_syntax) for(auto id:binders) {
                const auto &name=u.arena[id].value;
                if(function_scopes.back().helpers.contains(name)) error(u.arena[id].token,"pattern shadows nested helper "+name,"E210");
                if(name!="_"&&function_scopes.back().locals.insert(name).second) introduced.push_back(name);
            }
            auto body=block({"case","end"});
            if(u.aesop_syntax) for(const auto &name:introduced) function_scopes.back().locals.erase(name);
            const auto bind_id=list(std::move(binders)); const auto body_id=list(std::move(body));
            arms.push_back(add("case",c,{bind_id,body_id},"pair",owner,variant));
        }
        take("end"); const auto arms_id=list(std::move(arms)); return add("match",t,{value,arms_id});
    }
    Id conditional(uint32_t t) {
        Guard guard(*this);const auto cond=expression();take("{");auto yes=block({"}"});take("}");List no;
        if(peek()=="elseif") {const auto next=pop();no.push_back(conditional(next));}
        else if(peek()=="else") {pop();take("{");no=block({"}"});take("}");}
        return add("if",t,{cond,list(std::move(yes)),list(std::move(no))});
    }
    Id string_value(const std::string &raw,uint32_t t) {
        if(!u.aesop_syntax)return add("string",t,{},"string",text_literal(raw,t));
        std::string part="\"";Id result=UINT32_MAX;
        auto append=[&](Id value){result=result==UINT32_MAX?value:add("concat",t,{result,value});};
        for(size_t i=1;i+1<raw.size();) {
            if(raw[i]=='\\') {
                if(i+2<raw.size()&&raw[i+1]=='$'&&raw[i+2]=='{') {part+="\\u{24}";i+=2;continue;}
                part+=raw[i++];if(i+1<raw.size())part+=raw[i++];continue;
            }
            if(raw[i]=='$'&&i+2<raw.size()&&raw[i+1]=='{') {
                part+='"';append(add("string",t,{},"string",text_literal(part,t)));part="\"";
                const auto end=raw.find('}',i+2);if(end==std::string::npos)error(t,"unterminated string interpolation","E102");
                const auto name=raw.substr(i+2,end-i-2);
                // identifier or dotted field path, each segment must be a plain identifier
                std::vector<std::string> segments;{size_t from=0;for(;;) {const auto dot=name.find('.',from);segments.push_back(name.substr(from,dot==std::string::npos?std::string::npos:dot-from));if(dot==std::string::npos) break;from=dot+1;}}
                for(const auto &segment:segments) if(!identifier(segment)) error(t,"interpolation requires an identifier or dotted field path","E102");
                nonlocal_value(segments[0],t);Id value=add("name",t,{},"string",segments[0]);
                for(size_t k=1;k<segments.size();++k) value=add("field",t,{value},"string",segments[k]);
                append(add("format",t,{value}));i=end+1;
            } else part+=raw[i++];
        }
        part+='"';append(add("string",t,{},"string",text_literal(part,t)));return result;
    }
    Id statement() {
        const auto t=pop(); const auto s=u.text(t);
        if(u.aesop_syntax&&s=="@") {
            const auto modifier=pop();const auto mode=u.text(modifier);if(mode!="p"&&mode!="s")error(modifier,"local modifiers are @p or @s","E110");
            if(peek()==function_keyword()) {if(mode!="p")error(modifier,"nested helpers use @p","E110");const auto fn=function(true);u.roots.push_back(fn);return UINT32_MAX;}
            const bool owned=mode=="s";
            const auto name_token=ident();const auto name=u.text(name_token);
            if(function_scopes.back().helpers.contains(name)) error(name_token,"local shadows nested helper "+name,"E210");
            std::string ty;if(peek()!=":"&&peek()!="=") ty=type();colon();const auto value=expression();
            local_name(name);
            return add(owned?"scoped_local":"local",t,{value},"pair",name,ty);
        }
        if(u.aesop_syntax&&(s=="local"||s=="scoped")) error(t,"use @p name [type]: initializer; (@s for a scoped local)","E110");
        if(u.project_syntax&&s=="defer") {const auto call=expression();return add("defer",t,{call});}
        if(s=="return") {if(u.aesop_syntax&&peek()==";") return add("return",t,{add("unit",t,{})}); const auto value=expression(); return add("return",t,{value}); }
        if(s=="match") return match(t);
        if(u.aesop_syntax&&s=="if") return conditional(t);
        if(u.aesop_syntax&&s=="while") {const auto cond=expression();take("{");auto body=block({"}"});take("}");return add("while",t,{cond,list(std::move(body))});}
        if(u.aesop_syntax&&(s=="break"||s=="continue")) return add(s,t,{});
        if(u.aesop_syntax&&s=="for") {
            const auto name_token=ident();const auto name=u.text(name_token);
            take("in");
            auto first=expression(6);
            if(peek()=="..") {
                pop();const auto last=expression(6);take("{");auto body=block({"}"});take("}");
                local_name(name);
                return add("for_range",t,{first,last,list(std::move(body))},"pair",name);
            }
            take("{");auto body=block({"}"});take("}");
            local_name(name);
            return add("for_each",t,{first,list(std::move(body))},"pair",name);
        }
        if(identifier(s)&&(peek()==":")) { nonlocal_value(s,t);colon(); const auto value=expression(); return add("assign",t,{value},"string",s); }
        --position;
        const auto target=expression();
        if(peek()==":") { colon(); const auto value=expression(); return add("store",t,{target,value}); }
        return add("expr",t,{target});
    }
    List arguments() {
        take("("); List args;
        if(peek()!=")") {
            while(true) { args.push_back(expression()); if(peek()!=",") break; pop(); }
        }
        take(")"); return args;
    }
    static int precedence(const std::string &s) {
        static const std::unordered_map<std::string,int> prec={{"..",5},{"or",1},{"and",2},{"==",3},{"!=",3},{"<",4},{">",4},{"<=",4},{">=",4},{"+",5},{"-",5},{"*",6},{"/",6},{"%",6}};
        const auto found=prec.find(s); return found==prec.end()?-1:found->second;
    }
    Id expression(int minimum=0) {
        Guard guard(*this); const auto t=pop(); std::string s=u.text(t); Id left=0; bool dotted=false;
        // category.function(...) calls, e.g. spool.new(16), map.get(m,k), spell the builtin spool_new, map_get
        if(u.aesop_syntax&&position+2<u.tokens.size()&&u.text(position)=="."&&(identifier(u.text(position+1))||integers.contains(u.text(position+1))||u.text(position+1)=="f64")&&(u.text(position+2)=="("||u.text(position+2)=="<")) {
            static const std::unordered_set<std::string> categories={"spool","map","set","vector","view","string","int_vector"};
            bool local=false;for(const auto &scope:function_scopes) if(scope.locals.contains(s)) local=true;
            if(categories.contains(s)&&!local) {pop();s+="_"+u.text(position);pop();dotted=true;}
        }
        if(u.aesop_syntax&&s.starts_with("kn_nested_")) error(t,"reserved internal nested-function identifier","E110");
        const auto next=s=="-"?number(peek()):std::pair<std::string,std::string>{};
        const auto current=number(s);
        if(s=="-"&&!next.first.empty()&&next.first==minimum_magnitude(next.second)&&!(u.aesop_syntax&&position+1<u.tokens.size()&&u.text(position+1)==".")) {
            pop(); left=add("int",t,{},"integer","-"+next.first,{},next.second);
        } else if(s=="-"||s=="not") { const auto rhs=expression(7); left=add("unary",t,{rhs},"string",s); }
        else if(s=="(") { left=expression(); take(")"); }
        else if(u.aesop_syntax&&!current.first.empty()&&peek()=="."&&position+1<u.tokens.size()&&u.tokens[position+1].flags==1) {
            const auto dot=pop(),fraction=pop();const auto tail=u.text(fraction);const auto decimal=s+"."+tail;
            if(u.tokens[t].end!=u.tokens[dot].start||u.tokens[dot].end!=u.tokens[fraction].start||!finite_decimal(decimal)) error(t,"invalid, nonfinite or out-of-range f64 decimal literal","E102");
            left=add("float",t,{},"string",decimal);
        }
        else if(u.aesop_syntax&&(s=="pi"||s=="tau")) left=add("float",t,{},"string",s=="pi"?"3.141592653589793238462643383279502884":"6.283185307179586476925286766559005768");
        else if(!current.first.empty()) left=add(current.second[0]=='i'?"int":"uint",t,{},"integer",current.first,{},current.second);
        else if(integers.contains(s)||(u.aesop_syntax&&s=="f64")) { auto args=arguments(); left=add("convert",t,std::move(args),"string",s); }
        else if(u.project_syntax&&!s.empty()&&s[0]=='"') left=string_value(s,t);
        else if(u.project_syntax&&s=="move"&&identifier(peek())) {
            const auto name=ident();left=add("move",t,{add("name",name,{},"string",u.text(name))});
        }
        else if(u.project_syntax&&s=="[") {
            List values;if(peek()=="]") error(t,"empty array literals are not supported");
            values.push_back(expression());
            if(peek()==";") {
                pop();const auto count=array_count(t);take("]");
                left=add("array_repeat",t,std::move(values),"string",std::to_string(count));
            } else {
                while(peek()==",") {pop();values.push_back(expression());if(values.size()>1024) error(t,"array literal exceeds 1024 elements","E007");}
                take("]");left=add("array",t,std::move(values));
            }
        }
        else if(s=="true"||s=="false") left=add("bool",t,{},"bool",s);
        else if(u.aesop_syntax&&(s=="map_new"||s=="set_new")&&peek()=="<") {
            called(s,t);pop();const auto first=type();
            if(s=="set_new") {take(">");if(!set_type(set_name(first))) error(t,"set elements must be an integer, bool or text");auto args=arguments();left=add("call",t,std::move(args),"string","set_new_"+first);}
            else {take(",");const auto second=type();take(">");if(!map_type(map_name(first,second))) error(t,"map keys are an integer, bool or text and values are a scalar or text");auto args=arguments();left=add("call",t,std::move(args),"string","map_new_"+first+"_"+second);}
        }
        else if(u.aesop_syntax&&s=="vector_new"&&peek()=="<") {
            called(s,t);pop();const auto element=type();take(">");if(!generic_element(element)) error(t,"vector elements must be scalar integer, bool, f64 or text");auto args=arguments();left=add("call",t,std::move(args),"string","vector_new_"+element);
        }
        else if(identifier(s)) {
            if(!u.project_syntax&&peek()=="."&&position+2<u.tokens.size()&&u.text(position+2)=="(") {
                pop();const auto variant=u.text(ident());auto args=arguments();left=add("union_ctor",t,std::move(args),"pair",s,variant);
            } else {
            auto look=position; std::vector<std::string> parts;
            while(u.project_syntax&&look+1<u.tokens.size()&&u.text(look)=="."&&identifier(u.text(look+1))&&parts.size()<2) {parts.push_back(u.text(look+1));look+=2;}
            if(!parts.empty()&&look<u.tokens.size()&&u.text(look)=="(") {
                position=look; auto args=arguments();
                left=add("union_ctor",t,std::move(args),"pair",parts.size()==1?s:s+"."+parts[0],parts.back());
            } else if(peek()=="(") { auto args=arguments(); left=add("call",t,std::move(args),"string",called(s,t)); }
            else {nonlocal_value(s,t);left=add("name",t,{},"string",s);}
            }
        } else error(t,"expected expression; got '"+s+"'");
        if(dotted) u.dotted_tokens.insert(t);
        while(peek()=="."||(u.project_syntax&&peek()=="[")) {
            if(peek()==".") {pop();const auto f=ident();left=add("field",f,{left},"string",u.text(f));}
            else {const auto t=pop();const auto index=expression();take("]");left=add("index",t,{left,index});}
        }
        while(precedence(peek())>=minimum) {
            const auto op=pop(); const auto rhs=expression(precedence(u.text(op))+1); if(u.text(op)=="..") {if(!u.aesop_syntax)error(op,"concatenation requires Aesop syntax");left=add("concat",op,{add("format",op,{left}),add("format",op,{rhs})});}else left=add("binary",op,{left,rhs},"string",u.text(op));
        }
        return left;
    }
    Id global(const std::string &mode,uint32_t token) {
        const auto name=u.text(ident());std::string ty;if(peek()!=":"&&peek()!="=") ty=type();
        colon();const auto value=expression();take(";");const auto id=add("global",token,{value},"pair",name,ty);
        u.arena[id].result_mode=mode;u.global_names[0][name]=name;u.global_order.push_back(id);return id;
    }
    Id use() {
        const auto t=take("use");std::string path;unsigned parts=1;
        auto component=[&]() {if(u.tokens[position].flags!=1&&u.tokens[position].flags!=2) error(position,"expected use path component","E300");return u.text(pop());};
        if(!peek().empty()&&peek()[0]=='"') {const auto literal=pop();path=text_literal(u.text(literal),literal);}
        else {
            path=component();
            while(peek()=="/"||peek()=="."||peek()=="-") {
                const auto sep=pop();if(u.tokens[sep-1].end!=u.tokens[sep].start||u.tokens[sep].end!=u.tokens[position].start) error(sep,"use paths must be contiguous","E300");
                path+=u.text(sep)+component();if(++parts>32) error(t,"use path component budget exceeded","E300");
            }
        }
        if(path.size()>4095||path.find('\0')!=std::string::npos||path.find('\\')!=std::string::npos) error(t,"use path must be bounded UTF8 without NUL and use '/' separators","E300");
        if(!path.ends_with(".aw")) {
            // bare name: installed package under <project>/packages/NAME, resolved by the project loader with no fallback to local files
            if(path.find('/')!=std::string::npos||path.find('.')!=std::string::npos||path.size()>64||path.empty()) error(t,"package names are 1..64 letters/digits/_/-; project files require a .aw path","E300");
            std::string name=path;if(peek()=="as") {pop();name=u.text(ident());} else if(!identifier(path)) error(t,"package name requires an explicit identifier alias with as","E300");
            take(";");return add("import",t,{},"pair","pkg:"+path,name);
        }
        auto alias=path.substr(path.find_last_of('/')==std::string::npos?0:path.find_last_of('/')+1);alias.resize(alias.find_last_of('.'));
        if(peek()=="as") {pop();alias=u.text(ident());}
        if(!identifier(alias)) error(t,"file basename requires an explicit identifier alias with as","E300");
        take(";");return add("import",t,{},"pair",path,alias);
    }
    void tree_limits() {
        std::vector<std::pair<Id,uint32_t>> stack;
        for(auto root:u.roots) stack.emplace_back(root,1);
        uint32_t count=0;
        while(!stack.empty()) {
            const auto [id,d]=stack.back(); stack.pop_back(); const auto &node=u.arena.at(id);
            if(node.kind!="#list") {
                if(d>max_depth) error(node.token,"IR nesting exceeds 64","E006");
                if(++count>max_tokens) error(node.token,"IR node budget exceeded","E007");
            }
            for(auto child:node.children) stack.emplace_back(child,d+(node.kind!="#list"));
        }
    }
public:
    explicit Parser(Unit &unit):u(unit) {}
    void run() {
        try {
            bool declarations=false;
            while(peek()!="<eof>") {
                if(u.project_syntax&&peek()==";") {if(u.aesop_syntax) error(position,"unexpected semicolon","E110");pop();continue;}
                const auto start=position;
                try {
                    if(u.aesop_syntax&&peek()=="use") {
                        if(declarations) error(position,"use declarations must precede other declarations","E300");
                        u.roots.push_back(use());
                    } else if(u.aesop_syntax&&peek()=="exports") {
                        declarations=true;pop();take("{");
                        while(peek()!="}") {
                            const auto token=take("@");const auto mode=peek();
                            if(mode!="r"&&mode!="w") error(position,"exports members require @r or @w","E110");
                            pop();
                            if(peek()==function_keyword()) {
                                if(mode!="r") error(position,"exported funcs require @r, not @w","E110");
                                const auto fn=function();const auto &name=u.arena[fn].value;
                                if(!u.public_functions.insert(name).second) error(u.arena[fn].token,"duplicate export "+name,"E210");
                                u.roots.push_back(fn);
                            } else if(peek()=="enum") {
                                if(mode!="r") error(position,"exported enums require @r, not @w","E110");
                                const auto declaration=tagged_union();u.arena[declaration].result_mode="r";
                                u.roots.push_back(declaration);
                            } else if(peek()=="struct") {
                                if(mode!="r") error(position,"exported structs require @r, not @w","E110");
                                const auto declaration=structure();u.arena[declaration].result_mode="r";
                                u.roots.push_back(declaration);
                            } else u.roots.push_back(global(mode=="w"?"rw":mode,token));
                        }
                        take("}");take(";");
                    } else if(u.aesop_syntax&&peek()=="@") {
                        declarations=true;const auto token=pop();
                        if(peek()!="p") error(position,"@r/@rw are only valid inside exports{...}; use @p for private declarations","E110");
                        pop();
                        if(peek()==function_keyword()) u.roots.push_back(function());
                        else if(peek()=="struct") u.roots.push_back(structure());
                        else u.roots.push_back(global("p",token));
                    } else if(u.aesop_syntax&&peek()=="import") {error(position,"Aesop syntax uses use file.aw; rather than import","E110");
                    } else {declarations=true;
                        if(u.aesop_syntax&&peek()=="union") error(position,"Aesop syntax uses enum for tagged values, not union","E110");
                        u.roots.push_back(peek()=="struct"?structure():(peek()=="union"||(u.aesop_syntax&&peek()=="enum"))?tagged_union():function());}
                }
                catch(const Failure &e) {
                    if(u.aesop_syntax) {u.diagnostics={e.diagnostic};throw Stop{};}
                    record(e.diagnostic);
                    if(position==start) pop();
                    while(peek()!=function_keyword()&&peek()!="struct"&&peek()!="union"&&peek()!="<eof>") pop();
                }
            }
            if(u.diagnostics.empty()) tree_limits();
        } catch(const Failure &e) { u.diagnostics={e.diagnostic}; }
          catch(const Stop &) {}
    }
};
#include "kcheck.inc"
#include "kverify.inc"
#include "kemit.inc"

std::string json_quote(std::string_view s) {
    std::string out="\""; const char hex[]="0123456789abcdef";
    for(unsigned char c:s) {
        if(c=='"'||c=='\\') { out+='\\'; out+=static_cast<char>(c); }
        else if(c<32) { out+="\\u00"; out+=hex[c>>4]; out+=hex[c&15]; }
        else out+=static_cast<char>(c);
    }
    out+='"'; return out;
}
void ids(std::string &out,const List &list) {
    out+='['; bool first=true;
    for(auto id:list) { if(!first) out+=','; first=false; out+=std::to_string(id); }
    out+=']';
}
void serialize(Unit &u) {
    std::string out="{\"format\":\"KAST-arena-v1\",\"roots\":"; ids(out,u.roots); out+=",\"nodes\":[";
    if(!u.origins.empty()) {
        out=out.substr(0,out.size()-std::string(",\"nodes\":[").size());
        out+=",\"sources\":[";
        for(size_t i=0;i<u.files.size();++i) {if(i) out+=',';out+=json_quote(u.files[i]);}
        out+="],\"origins\":[";
        for(size_t i=0;i<u.origins.size();++i) {
            if(i) out+=',';
            const auto &o=u.origins[i];const auto &t=u.tokens.at(i);
            out+="["+std::to_string(o.file)+","+std::to_string(o.start)+","+std::to_string(o.end)+","+std::to_string(t.line)+","+std::to_string(t.column)+"]";
        }
        out+="],\"nodes\":[";
    }
    bool first=true;
    for(const auto &node:u.arena) {
        if(!first) out+=',';
        first=false;
        out+="{\"kind\":"+json_quote(node.kind)+",\"token\":"+std::to_string(node.token)+",\"value_kind\":"+json_quote(node.value_kind)+",\"value\":"+json_quote(node.value)+",\"second\":"+json_quote(node.second)+",\"literal_type\":"+json_quote(node.literal)+",\"children\":";
        ids(out,node.children); out+=",\"type\":"+json_quote(node.type)+",\"symbol\":"+json_quote(node.symbol);
        if(!node.result_mode.empty()) out+=",\"result_mode\":"+json_quote(node.result_mode);
        out+="}";
        if(out.size()>67108864) throw std::runtime_error("AST export budget exceeded");
    }
    out+="],\"diagnostics\":["; first=true;
    for(const auto &d:u.diagnostics) {
        if(!first) out+=',';
        first=false;
        out+="{\"code\":"+json_quote(d.code)+",\"message\":"+json_quote(d.message)+",\"token\":"+std::to_string(d.token)+"}";
    }
    out+="]}"; u.json=std::move(out);
}
bool source_map(Unit &u,const char *source,size_t size) {
    if((!source&&size)||size>1048576) return false;
    u.source.assign(source?source:"",size); u.bytes.reserve(size+1);
    for(size_t i=0;i<size;) {
        u.bytes.push_back(i); const auto c=static_cast<unsigned char>(u.source[i]); size_t n=0;
        if(c<128) n=1; else if(c>=0xc2&&c<=0xdf) n=2; else if(c>=0xe0&&c<=0xef) n=3; else if(c>=0xf0&&c<=0xf4) n=4; else return false;
        if(n>size-i) return false;
        uint32_t cp=n==1?c:c&((1u<<(7-n))-1u);
        for(size_t j=1;j<n;++j) { const auto b=static_cast<unsigned char>(u.source[i+j]); if((b&0xc0)!=0x80) return false; cp=(cp<<6)|(b&63); }
        if((n==3&&cp<0x800)||(n==4&&cp<0x10000)||(cp>=0xd800&&cp<=0xdfff)||cp>0x10ffff) return false;
        i+=n;
    }
    u.bytes.push_back(size); return true;
}
bool initialize(Unit &u,const char *source,size_t size,const AwlLexToken *tokens,uint32_t count) {
    if(!tokens||count==0||count>max_tokens+1||!source_map(u,source,size)) return false;
    uint32_t end=0;
    for(uint32_t i=0;i<count;++i) {
        const auto &t=tokens[i];
        if(t.start<end||t.start>t.end||t.end>=u.bytes.size()||!t.line||!t.column) return false;
        if(i+1<count&&t.start==t.end) return false;
        if(i+1==count&&(t.start!=t.end||t.end+1!=u.bytes.size())) return false;
        end=t.end;
    }
    u.tokens.assign(tokens,tokens+count); return true;
}
#include "unicode_tables.inc"
template<size_t N> bool in_ranges(uint32_t cp,const UnicodeRange (&ranges)[N]) {
    size_t first=0,last=N;
    while(first<last) { const auto mid=(first+last)/2; if(cp<ranges[mid].first) last=mid; else if(cp>ranges[mid].last) first=mid+1; else return true; }
    return false;
}
uint32_t codepoint(const Unit &u,uint32_t position) {
    const auto begin=u.bytes.at(position),end=u.bytes.at(position+1); const auto c=static_cast<unsigned char>(u.source[begin]);
    uint32_t cp=end-begin==1?c:c&((1u<<(7-(end-begin)))-1u);
    for(size_t i=begin+1;i<end;++i) cp=(cp<<6)|(static_cast<unsigned char>(u.source[i])&63);
    return cp;
}
bool alnum(uint32_t cp) {
    if(cp<128) return (cp>='a'&&cp<='z')||(cp>='A'&&cp<='Z')||(cp>='0'&&cp<='9');
    return in_ranges(cp,unicode_alnum);
}
std::string character_repr(const Unit &u,uint32_t position) {
    const auto cp=codepoint(u,position);
    if(cp==39) return "\"'\"";
    if(cp==92) return "'\\\\'";
    if(cp>=32&&cp<127) return "'"+u.source.substr(u.bytes[position],1)+"'";
    if(cp>=128&&in_ranges(cp,unicode_printable)) return "'"+u.source.substr(u.bytes[position],u.bytes[position+1]-u.bytes[position])+"'";
    const size_t width=cp<256?2:cp<65536?4:8; const char hex[]="0123456789abcdef";
    std::string result="'\\"; result+=width==2?'x':width==4?'u':'U';
    for(size_t i=width;i>0;--i) result+=hex[(cp>>(4*(i-1)))&15];
    return result+"'";
}
std::unique_ptr<Unit> parse_source(const char *source,size_t size) {
    auto u=std::make_unique<Unit>();
    AwlLexResult raw{};
    struct Cleanup { AwlLexResult &r; ~Cleanup(){Awl_lex_free(&r);} } cleanup{raw};
    const auto status=Awl_lex(source,size,&raw);
    if(status==5) throw std::runtime_error("native scanner failure");
    if(status==3||status==4) {
        source_map(*u,"",0); u->tokens.push_back({0,0,1,1,0});
        u->diagnostics.push_back({status==3?"E001":"E008",status==3?"source exceeds 1048576 bytes":"source must be UTF-8",0});
        return u;
    }
    if(!source_map(*u,source,size)) throw std::runtime_error("source map failure");
    if(raw.count) u->tokens.assign(raw.tokens,raw.tokens+raw.count);
    auto finish=[&] { const auto end=static_cast<uint32_t>(u->bytes.size()-1); u->tokens.push_back({end,end,raw.line,raw.column,0}); };
    for(uint32_t i=0;i<raw.count;++i) {
        const auto &t=raw.tokens[i]; const auto text=u->source.substr(u->bytes[t.start],u->bytes[t.end]-u->bytes[t.start]);
        std::string code,message;
        if(t.flags==2&&t.end-t.start>128) { code="E003"; message="identifier exceeds 128 characters"; }
        if(t.flags==1) {
            if(t.end+1<u->bytes.size()&&(alnum(codepoint(*u,t.end))||codepoint(*u,t.end)=='_')) {
                code="E101"; message="invalid integer suffix or missing token separator";
            } else {
                const auto digits=text.find_first_not_of("0123456789");
                if((digits==std::string::npos?text.size():digits)>256) {code="E004";message="integer literal exceeds 256 digits";}
            }
        }
        if(code.empty()&&i>=100000) {code="E005";message="token count exceeds 100000";}
        if(!code.empty()) { u->diagnostics.push_back({code,message,i}); finish(); return u; }
    }
    if(status==1||status==6) {
        const auto index=static_cast<uint32_t>(u->tokens.size());
        u->tokens.push_back({raw.position,raw.position+1,raw.line,raw.column,0});
        u->diagnostics.push_back({status==6?"E102":"E101",status==6?"unterminated string literal":"unexpected character "+character_repr(*u,raw.position),index});
        finish(); return u;
    }
    if(status!=0) throw std::runtime_error("invalid scanner completion");
    finish(); Parser parser(*u); parser.run(); return u;
}
#include "kproject.inc"

std::string render(Unit &u,const std::string &filename,bool json) {
    std::string out=json?"{\"file\":"+json_quote(filename)+",\"diagnostics\":[":"";
    for(size_t i=0;i<u.diagnostics.size();++i) {
        const auto &d=u.diagnostics[i];
        AwlLexToken t{0,0,1,1,0}; if(d.token!=UINT32_MAX) t=u.tokens.at(d.token);
        std::string location=filename; uint32_t start=t.start,end=t.end;
        if(d.token<u.origins.size()) {const auto &o=u.origins[d.token];location=u.files.at(o.file);start=o.start;end=o.end;}
        std::string message; const auto &raw=d.message;
        for(size_t p=0;p<raw.size();) {
            if((raw[p]>='a'&&raw[p]<='z')||(raw[p]>='A'&&raw[p]<='Z')||raw[p]=='_') {
                auto q=p+1;while(q<raw.size()&&((raw[q]>='a'&&raw[q]<='z')||(raw[q]>='A'&&raw[q]<='Z')||(raw[q]>='0'&&raw[q]<='9')||raw[q]=='_')) ++q;
                const auto word=raw.substr(p,q-p);message+=u.display_names.contains(word)?u.display_names.at(word):word;p=q;
            } else message+=raw[p++];
        }
        if(json) {
            if(i) out+=',';
            if(!u.origins.empty()) out+="{\"file\":"+json_quote(location)+",";
            else out+="{";
            out+="\"code\":"+json_quote(d.code)+",\"message\":"+json_quote(message)+",\"line\":"+std::to_string(t.line)+",\"column\":"+std::to_string(t.column)+",\"end_column\":"+std::to_string(t.column+std::max(1u,t.end-t.start))+",\"start\":"+std::to_string(start)+",\"end\":"+std::to_string(end)+"}";
        } else out+=location+":"+std::to_string(t.line)+":"+std::to_string(t.column)+": error["+d.code+"]: "+message+"\n";
    }
    if(json) out+="]}\n";
    return out;
}

}
extern "C" {
uint32_t Awl_parse_abi_version(void) { return 2; }
int Awl_parse_tokens(const char *source,size_t size,const AwlLexToken *tokens,uint32_t count,void **out) {
    if(!out) return 1;
    *out=nullptr;
    try {
        auto unit=std::make_unique<Unit>();
        if(!initialize(*unit,source,size,tokens,count)) return 1;
        Parser parser(*unit); parser.run(); *out=unit.release(); return 0;
    } catch(...) { return 2; }
}
int Awl_parse_source(const char *source,size_t size,void **out) {
    if(!out||(!source&&size)) return 1;
    *out=nullptr;
    try { auto unit=parse_source(source,size); *out=unit.release(); return 0; }
    catch(...) {return 2;}
}
int Awl_parse_file(const char *path,void **out) {
    if(!path||!out) return 1;
    *out=nullptr;
    try {auto unit=parse_project(path);*out=unit.release();return 0;} catch(...) {return 2;}
}
uint32_t Awl_source_file_count(void *opaque) {return opaque?static_cast<uint32_t>(static_cast<Unit*>(opaque)->files.size()):0;}
const char *Awl_source_file_path(void *opaque,uint32_t index) {
    if(!opaque) return nullptr;
    const auto &files=static_cast<Unit*>(opaque)->files;
    return index<files.size()?files[index].c_str():nullptr;
}
uint32_t Awl_diagnostic_count(void *opaque) { return opaque?static_cast<uint32_t>(static_cast<Unit*>(opaque)->diagnostics.size()):0; }
const char *Awl_render_diagnostics(void *opaque,const char *filename,int json,size_t *size) {
    if(!opaque||!filename||!size) return nullptr;
    try { auto &u=*static_cast<Unit*>(opaque); u.report=render(u,filename,json!=0); *size=u.report.size(); return u.report.data(); }
    catch(...) { *size=0; return nullptr; }
}
const char *Awl_parse_json(void *opaque,size_t *size) {
    if(!opaque||!size) return nullptr;
    try { auto &u=*static_cast<Unit*>(opaque); if(u.json.empty()) serialize(u); *size=u.json.size(); return u.json.data(); }
    catch(...) { *size=0; return nullptr; }
}
int Awl_check_unit(void *opaque) {
    if(!opaque) return 2;
    auto &u=*static_cast<Unit*>(opaque);
    if(!u.diagnostics.empty()) return 1;
    if(u.checked) return 0;
    try { Checker checker(u); checker.run(); u.checked=true; u.json.clear(); return 0; }
    catch(const Failure &e) { u.diagnostics={e.diagnostic}; u.json.clear(); return 1; }
    catch(...) { return 2; }
}
int Awl_verify_unit(void *opaque) {
    if(!opaque) return 2;
    auto &u=*static_cast<Unit*>(opaque);
    if(!u.diagnostics.empty()) return 1;
    try { Verifier verifier(u); verifier.run(); return 0; }
    catch(const Failure &e) { u.diagnostics={e.diagnostic}; u.json.clear(); return 1; }
    catch(...) { return 2; }
}
int Awl_emit_c(void *opaque,const char **output,size_t *size) {
    if(!opaque||!output||!size) return 2;
    *output=nullptr; *size=0;
    auto &u=*static_cast<Unit*>(opaque); u.c_output.clear();
    if(!u.diagnostics.empty()) return 1;
    try { CEmitter emitter(u); u.c_output=emitter.emit(); *output=u.c_output.data(); *size=u.c_output.size(); return 0; }
    catch(const Failure &e) {u.diagnostics={e.diagnostic}; u.json.clear();return 1;}
    catch(...) {return 2;}
}
uint32_t Awl_parse_node_count(void *opaque) { return opaque?static_cast<uint32_t>(static_cast<Unit*>(opaque)->arena.size()):0; }
void Awl_parse_free(void *opaque) { delete static_cast<Unit*>(opaque); }
int Awl_parse_benchmark(const char *source,size_t size,const AwlLexToken *tokens,uint32_t count,uint32_t repeat,double *seconds,uint64_t *nodes) {
    if(!seconds||!nodes||!repeat||repeat>100000) return 1;
    *seconds=0; *nodes=0; const auto begin=std::chrono::steady_clock::now();
    for(uint32_t i=0;i<repeat;++i) {
        void *unit=nullptr; const auto status=Awl_parse_tokens(source,size,tokens,count,&unit);
        if(status) return status;
        const auto &u=*static_cast<Unit*>(unit);
        if(!u.diagnostics.empty()) { Awl_parse_free(unit); return 1; }
        *nodes+=Awl_parse_node_count(unit); Awl_parse_free(unit);
    }
    *seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count(); return 0;
}
}
