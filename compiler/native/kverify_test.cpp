#include <cctype>
// Test-only translation unit: include implementation to corrupt private arenas.
// No mutation API or test backdoor is exported by production library/executable.
#include "kparse.cpp"
#include <functional>
#include <iostream>
#include <random>
void assert_test(bool condition,const std::string &message) {if(!condition) throw std::runtime_error(message);}
std::unique_ptr<Unit> checked_source(const std::string &source,bool project=false,bool next=false) {
    auto u=parse_source(source.data(),source.size(),project,next);
    assert_test(u->diagnostics.empty(),"seed parse failed: "+source+(u->diagnostics.empty()?"":" :: "+u->diagnostics.front().message)); Checker c(*u);c.run();return u;
}
Id find_kind(const Unit &u,const std::string &kind,const std::string &value="") {
    for(Id id=0;id<u.arena.size();++id) if(u.arena[id].kind==kind&&(value.empty()||u.arena[id].value==value)) return id;
    throw std::runtime_error("missing mutation target: "+kind+" "+value);
}
void verify_expected(Unit &u,bool good) {
    serialize(u); const auto before=u.json; bool rejected=false;
    try {Verifier v(u);v.run();}
    catch(const Failure &f) {assert_test(f.diagnostic.code=="E500","wrong verifier error");rejected=true;}
    serialize(u); assert_test(u.json==before,"verifier modified arena/diagnostics");
    assert_test(rejected!=good,good?"valid arena rejected":"corruption accepted");
}
int main() {
    try {
        const std::string source=R"(
struct Pair a:i64 b:bool end
union Result Ok(value:Pair) Err(code:i64) None() end
function id(x:i64)->i64 return x end
function noop()->unit print(1) end
function unwrap(r:Result)->i64
match r then
case Result.Ok(_) then return 1
case Result.Err(code) then return code
case Result.None() then return 0
end
end
function main()->i64
local p:Pair=Pair(1,true)
local a:i64=id(p.a)
a=a+1
p.a=a
if p.b then print(not false) else print(i8(1)) end
while false do a=-a end
local r:Result=Result.Ok(p)
match r then
case Result.Ok(q) then print(q.a)
case Result.Err(code) then print(code)
case Result.None() then print(0)
end
print(-128i8)
print(18446744073709551615u64)
return a
end
)";
        auto seed=checked_source(source);verify_expected(*seed,true);
        seed->checked=false;verify_expected(*seed,true); // Flag is not proof.
        using Mutation=std::function<void(Unit&)>; std::vector<Mutation> tests;
        auto change=[&](std::string kind,auto mutator,std::string value="") {
            tests.emplace_back([=](Unit &u){mutator(u.arena[find_kind(u,kind,value)]);});
        };
        change("int",[](Node &n){n.type="u64";});
        change("int",[](Node &n){n.value="9223372036854775808";},"1");
        change("int",[](Node &n){n.value="-129";},"-128");
        change("uint",[](Node &n){n.value="18446744073709551616";});
        change("int",[](Node &n){n.value="01";});
        change("int",[](Node &n){n.value="-0";});
        change("int",[](Node &n){n.value="1;abort()";});
        change("int",[](Node &n){n.literal="u64";});
        change("bool",[](Node &n){n.value="maybe";});
        change("name",[](Node &n){n.symbol="k_v99999";});
        change("name",[](Node &n){n.value="injected";});
        change("name",[](Node &n){n.value="p);abort();//";});
        change("local",[](Node &n){n.symbol="bad";});
        change("local",[](Node &n){n.second="unit";});
        change("local",[](Node &n){n.value="return";});
        change("assign",[](Node &n){n.symbol="k_v99999";});
        change("assign",[](Node &n){n.value="absent";});
        change("field",[](Node &n){n.value="absent";});
        change("field",[](Node &n){n.type="bool";},"a");
        change("convert",[](Node &n){n.value="bool";});
        change("unary",[](Node &n){n.value="~";});
        change("binary",[](Node &n){n.value="<<";});
        change("call",[](Node &n){n.value="absent";});
        change("call",[](Node &n){n.children.clear();},"Pair");
        change("call",[](Node &n){n.type="i64";},"print");
        change("union_ctor",[](Node &n){n.second="Absent";});
        change("union_ctor",[](Node &n){n.children.clear();});
        change("case",[](Node &n){n.value="Pair";});
        change("case",[](Node &n){n.second="Absent";});
        change("pattern_bind",[](Node &n){n.type="bool";});
        change("pattern_bind",[](Node &n){n.symbol="k_v90000";},"_");
        change("field_decl",[](Node &n){n.second="unit";});
        change("struct",[](Node &n){n.children.clear();});
        change("union",[](Node &n){n.children.clear();});
        change("function",[](Node &n){n.value="print";});
        change("function",[](Node &n){n.second="bool";},"main");
        change("return",[](Node &n){n.children.clear();});
        tests.emplace_back([](Unit &u){u.roots.push_back(u.roots.back());});
        tests.emplace_back([](Unit &u){u.roots[0]=UINT32_MAX;});
        tests.emplace_back([](Unit &u){u.roots.pop_back();});
        tests.emplace_back([](Unit &u){auto &m=u.arena[find_kind(u,"function","main")];u.arena[m.children[1]].children.pop_back();});
        tests.emplace_back([](Unit &u){auto &m=u.arena[find_kind(u,"match")];auto &arms=u.arena[m.children[1]];arms.children.pop_back();});
        tests.emplace_back([](Unit &u){auto &s=u.arena[find_kind(u,"struct")];u.arena[s.children[0]].second=s.value;});
        tests.emplace_back([](Unit &u){auto &n=u.arena[find_kind(u,"local","a")];n.symbol=u.arena[find_kind(u,"local","p")].symbol;});
        tests.emplace_back([](Unit &u){auto &n=u.arena[find_kind(u,"store")];auto &p=u.arena[n.children[0]];p.kind="call";p.value="Pair";});
        size_t targeted=0;
        for(const auto &mutate:tests) {Unit copy=*seed;mutate(copy);verify_expected(copy,false);++targeted;}
        // Every experimental intrinsic must be independently recognized with
        // exact result metadata; no Checker call is used by Verifier.
        for(const auto &[name,sig]:platform_signatures) {
            const bool next=generic_specialization(name)||view_specialization(name)||name=="process_capture";
            std::string shown=name;
            if(next) for(const std::string c:{"int_vector","spool","vector","string","view","map","set"}) if(name.starts_with(c+"_")) {shown=c+"."+name.substr(c.size()+1);break;}
            std::string call=shown+"(";
            for(size_t i=0;i<sig.parameters.size();++i) {if(i) call+=",";call+=view_type(sig.parameters[i])?"vector_view(vector_new<"+*view_type(sig.parameters[i])+">(0),0,0)":generic_type(sig.parameters[i])?"vector_new<"+*generic_type(sig.parameters[i])+">(0)":sig.parameters[i]=="f64"?"0.0":sig.parameters[i]=="bool"?"false":sig.parameters[i]=="int_vector"?"int_vector_new(0)":sig.parameters[i]=="spool"?"spool_new(0)":sig.parameters[i]=="string"?"string_from_codepoint(0u32)":sig.parameters[i]=="i64"?"0":"0"+sig.parameters[i];}
            call+=")";
            if(next) for(const std::string prefix:{"int_vector_","spool_","vector_","string_","view_","map_","set_"}) {
                size_t pos=0;while((pos=call.find(prefix,pos))!=std::string::npos) {
                    if(pos==0||(!std::isalnum(static_cast<unsigned char>(call[pos-1]))&&call[pos-1]!='_'&&call[pos-1]!='.')) call[pos+prefix.size()-1]='.';
                    pos+=prefix.size();
                }
            }
            auto platform=checked_source(next?"func main: i64 { "+call+"; return 0; };":"function main()->i64 "+call+" return 0 end",next||name.starts_with("int_vector_"),next);
            verify_expected(*platform,true);
            const auto id=find_kind(*platform,"call",name);
            Unit wrong_type=*platform;wrong_type.arena[id].type=sig.result=="unit"?"i64":"unit";
            verify_expected(wrong_type,false);++targeted;
            Unit unknown=*platform;unknown.arena[id].value="not_a_platform_intrinsic";
            verify_expected(unknown,false);++targeted;
        }
        auto text=checked_source(R"(function main()->i64 local s:string="a\0é🚀" print(s+"b") print(string_slice(s,0,1)) return 0 end)",true);
        verify_expected(*text,true);
        const auto string_id=find_kind(*text,"string");
        std::vector<std::function<void(Node &)>> string_corruptions={
            [](Node &n){n.type="i64";},[](Node &n){n.value_kind="integer";},
            [](Node &n){n.literal="i64";},[](Node &n){n.value=std::string(65537,'x');},
            [](Node &n){n.value=std::string("\xc0\x80",2);},
            [](Node &n){n.value=std::string("\xed\xa0\x80",3);},
            [](Node &n){n.value=std::string("\xf4\x90\x80\x80",4);},
            [](Node &n){n.value=std::string("\xf0\x9f\x9a",3);},
            [](Node &n){n.value=std::string("\x80",1);},
            [](Node &n){n.children.push_back(0);},[](Node &n){n.second="x";},
            [](Node &n){n.symbol="k_v999";}
        };
        for(const auto &mutate:string_corruptions) {Unit copy=*text;mutate(copy.arena[string_id]);verify_expected(copy,false);++targeted;}
        std::string aggregate_source="function main()->i64 ";
        for(int i=0;i<17;++i) aggregate_source+="print(\"x\") ";
        aggregate_source+="return 0 end";
        auto aggregate=checked_source(aggregate_source,true);
        for(auto &node:aggregate->arena) if(node.kind=="string") node.value=std::string(65536,'x');
        verify_expected(*aggregate,false);++targeted;
        auto deferred=checked_source("function main()->i64 local b:spool=spool_new(4) defer spool_free(b) return 0 end",true);
        verify_expected(*deferred,true);const auto deferred_id=find_kind(*deferred,"defer");
        std::vector<std::function<void(Unit &)>> deferred_corruptions={
            [=](Unit &u){u.arena[deferred_id].children.clear();},
            [=](Unit &u){u.arena[deferred_id].children={u.roots[0]};},
            [=](Unit &u){u.arena[deferred_id].type="unit";},
            [=](Unit &u){u.arena[deferred_id].value_kind="string";},
            [=](Unit &u){u.arena[deferred_id].value="x";},
            [=](Unit &u){u.arena[deferred_id].second="x";},
            [=](Unit &u){u.arena[deferred_id].symbol="k_v999";},
            [=](Unit &u){u.arena[deferred_id].literal="i64";},
            [=](Unit &u){u.arena[u.arena[deferred_id].children[0]].children.clear();},
            [=](Unit &u){u.arena[u.arena[deferred_id].children[0]].type="i64";},
            [=](Unit &u){u.arena[u.arena[deferred_id].children[0]].value="buffer_free";},
            [=](Unit &u){u.arena[u.arena[deferred_id].children[0]].value="print";},
            [](Unit &u){u.project_syntax=false;}
        };
        for(const auto &mutate:deferred_corruptions) {Unit copy=*deferred;mutate(copy);verify_expected(copy,false);++targeted;}
        auto array_seed=checked_source("function main()->i64 local a:[i64;2]=[1,2] a[0]=3 return array_length(a) end",true);
        verify_expected(*array_seed,true);const auto aid=find_kind(*array_seed,"array"),iid=find_kind(*array_seed,"index"),lid=find_kind(*array_seed,"call","array_length");
        std::vector<std::function<void(Unit &)>> array_corruptions={
            [=](Unit &u){u.arena[aid].type="[bool;2]";},
            [=](Unit &u){u.arena[aid].type="[i64;0]";},
            [=](Unit &u){u.arena[aid].type="[i64;1025]";},
            [=](Unit &u){u.arena[aid].children.clear();},
            [=](Unit &u){u.arena[aid].children.pop_back();},
            [=](Unit &u){u.arena[aid].value="x";},
            [=](Unit &u){u.arena[aid].value_kind="string";},
            [=](Unit &u){u.arena[aid].second="x";},
            [=](Unit &u){u.arena[aid].symbol="k_v99";},
            [=](Unit &u){u.arena[aid].literal="i64";},
            [=](Unit &u){u.arena[iid].children.clear();},
            [=](Unit &u){u.arena[iid].type="bool";},
            [=](Unit &u){u.arena[u.arena[iid].children[1]].type="u64";},
            [=](Unit &u){u.arena[lid].type="u64";},
            [=](Unit &u){u.arena[lid].children.clear();},
            [=](Unit &u){u.arena[lid].value="not_array_length";},
            [](Unit &u){u.project_syntax=false;}
        };
        for(const auto &mutate:array_corruptions) {Unit copy=*array_seed;mutate(copy);verify_expected(copy,false);++targeted;}
        auto repeated=checked_source("function main()->i64 local a:[i64;3]=[7;3] return a[2] end",true);
        verify_expected(*repeated,true);const auto rid=find_kind(*repeated,"array_repeat");
        for(const std::string bad:{"0","1025","-1","01","1u8","1;abort()","","9999999999999999999999999999"}) {
            Unit copy=*repeated;copy.arena[rid].value=bad;verify_expected(copy,false);++targeted;
        }
        std::vector<std::function<void(Unit &)>> repeat_corruptions={
            [=](Unit &v){v.arena[rid].children.clear();},
            [=](Unit &v){v.arena[rid].children.push_back(v.arena[rid].children[0]);},
            [=](Unit &v){v.arena[rid].type="[i64;2]";},
            [=](Unit &v){v.arena[rid].value_kind="integer";},
            [=](Unit &v){v.arena[rid].second="injected";},
            [](Unit &v){v.project_syntax=false;}
        };
        for(const auto &mutate:repeat_corruptions) {Unit copy=*repeated;mutate(copy);verify_expected(copy,false);++targeted;}
        auto owner_seed=checked_source("function fresh(x:i64)->spool return spool_new(x) end function main()->i64 scoped owner:spool=spool_new(8) local manual:spool=spool_new(8) local alias:spool=manual spool_print(owner) manual=alias return 0 end",true);
        verify_expected(*owner_seed,true);const auto oid=find_kind(*owner_seed,"scoped_local"),mid=find_kind(*owner_seed,"name","manual");const auto osym=owner_seed->arena[oid].symbol;
        for(const std::string bad:{"i64","string","[spool;1]"}) {Unit c=*owner_seed;c.arena[oid].second=bad;verify_expected(c,false);++targeted;}
        std::vector<std::function<void(Unit &)>> owner_corruptions={
            [=](Unit &v){v.arena[oid].children.clear();},
            [=](Unit &v){v.arena[v.arena[oid].children[0]].value="fresh";},
            [=](Unit &v){v.arena[mid].value="owner";v.arena[mid].symbol=osym;},
            [=](Unit &v){auto &a=v.arena[find_kind(v,"assign","manual")];a.value="owner";a.symbol=osym;},
            [=](Unit &v){auto &a=v.arena[find_kind(v,"call","spool_print")];a.value="spool_free";a.type="unit";},
            [](Unit &v){v.project_syntax=false;},
            [=](Unit &v){v.arena[oid].symbol.clear();},
            [=](Unit &v){v.arena[oid].value_kind="string";}
        };
        for(const auto &mutate:owner_corruptions) {Unit copy=*owner_seed;mutate(copy);verify_expected(copy,false);++targeted;}
        auto escaped=checked_source("function f()->spool scoped owner:spool=spool_new(8) return spool_new(1) end function main()->i64 return 0 end",true);
        const auto eo=find_kind(*escaped,"scoped_local"),er=find_kind(*escaped,"return");
        auto &en=escaped->arena[escaped->arena[er].children[0]];en.kind="name";en.value="owner";en.value_kind="string";en.children.clear();en.symbol=escaped->arena[eo].symbol;
        verify_expected(*escaped,false);++targeted;
        auto borrow_seed=checked_source("function read(borrow b:spool)->i64 return spool_bytes(b) end function main()->i64 scoped owner:spool=spool_new(8) local manual:spool=spool_new(8) read(owner) return read(manual) end",true);
        verify_expected(*borrow_seed,true);const auto bp=find_kind(*borrow_seed,"borrow_param");
        for(const std::string bad:{"i64","string","[spool;1]"}) {Unit c=*borrow_seed;c.arena[bp].second=bad;verify_expected(c,false);++targeted;}
        std::vector<std::function<void(Unit &)>> borrow_corruptions={
            [=](Unit &v){v.arena[bp].kind="field_decl";},
            [=](Unit &v){v.arena[bp].kind="param";},
            [=](Unit &v){v.arena[bp].value_kind="string";},
            [=](Unit &v){v.arena[bp].symbol.clear();},
            [=](Unit &v){v.arena[bp].literal="i64";},
            [=](Unit &v){v.arena[bp].children.push_back(0);},
            [](Unit &v){v.project_syntax=false;},
            [](Unit &v){auto &c=v.arena[find_kind(v,"call","spool_bytes")];c.value="spool_free";c.type="unit";}
        };
        for(const auto &mutate:borrow_corruptions) {Unit copy=*borrow_seed;mutate(copy);verify_expected(copy,false);++targeted;}
        auto borrow_escape=checked_source("function f(borrow b:spool)->spool return spool_new(1) end function main()->i64 return 0 end",true);
        const auto be=find_kind(*borrow_escape,"borrow_param"),br=find_kind(*borrow_escape,"return");
        auto &bn=borrow_escape->arena[borrow_escape->arena[br].children[0]];bn.kind="name";bn.value="b";bn.value_kind="string";bn.children.clear();bn.symbol=borrow_escape->arena[be].symbol;
        verify_expected(*borrow_escape,false);++targeted;
        auto borrowed_assignment=checked_source("function f(borrow b:spool)->i64 local m:spool=spool_new(1) m=m return 0 end function main()->i64 return 0 end",true);
        auto &ba=borrowed_assignment->arena[find_kind(*borrowed_assignment,"assign","m")];ba.value="b";ba.symbol=borrowed_assignment->arena[find_kind(*borrowed_assignment,"borrow_param")].symbol;
        verify_expected(*borrowed_assignment,false);++targeted;
        auto legacy_borrow=checked_source("function borrow()->i64 return 1 end function main()->i64 return borrow() end",false);verify_expected(*legacy_borrow,true);
        auto move_seed=checked_source("function main()->i64 scoped a:spool=spool_new(8) scoped b:spool=move a print(spool_valid(b)) return 0 end",true);
        verify_expected(*move_seed,true);const auto move_id=find_kind(*move_seed,"move"),source_id=move_seed->arena[move_id].children[0],after_id=move_seed->arena[find_kind(*move_seed,"call","spool_valid")].children[0];
        std::vector<std::function<void(Unit &)>> move_corruptions={
            [=](Unit &v){v.arena[move_id].children.clear();},
            [=](Unit &v){v.arena[move_id].type="i64";},
            [=](Unit &v){v.arena[move_id].value="injected";},
            [=](Unit &v){v.arena[move_id].value_kind="string";},
            [=](Unit &v){v.arena[source_id].type="i64";},
            [=](Unit &v){v.arena[source_id].value="b";},
            [=](Unit &v){v.arena[source_id].symbol="k_v999";},
            [=](Unit &v){v.arena[after_id].value="a";v.arena[after_id].symbol=v.arena[source_id].symbol;},
            [=](Unit &v){v.arena[move_id].kind="array";v.arena[move_id].type="[spool;1]";},
            [](Unit &v){v.project_syntax=false;}
        };
        for(const auto &mutate:move_corruptions) {Unit copy=*move_seed;mutate(copy);verify_expected(copy,false);++targeted;}
        auto nested_move=checked_source("function main()->i64 scoped a:spool=spool_new(8) while false do scoped inner:spool=spool_new(8) print(spool_valid(inner)) end return 0 end",true);
        const auto nm=find_kind(*nested_move,"scoped_local","inner");const auto outer_symbol=nested_move->arena[find_kind(*nested_move,"scoped_local","a")].symbol;
        const auto init_id=nested_move->arena[nm].children[0],old_capacity=nested_move->arena[init_id].children[0];
        auto &nc=nested_move->arena[old_capacity];nc.kind="name";nc.value_kind="string";nc.value="a";nc.literal="";nc.type="spool";nc.symbol=outer_symbol;
        auto &ni=nested_move->arena[init_id];ni.kind="move";ni.value_kind="null";ni.value="";ni.type="spool";
        verify_expected(*nested_move,false);++targeted;
        nested_move->arena[nm].value="a";auto &nu=nested_move->arena[nested_move->arena[find_kind(*nested_move,"call","spool_valid")].children[0]];nu.value="a";
        verify_expected(*nested_move,false);++targeted;
        auto legacy_move=checked_source("function move()->i64 return 1 end function main()->i64 return move() end",false);verify_expected(*legacy_move,true);
        auto take_seed=checked_source("function finish(own b:spool)->i64 return spool_bytes(b) end function main()->i64 scoped a:spool=spool_new(8) local count:i64=finish(move a) return count end",true);
        verify_expected(*take_seed,true);const auto tp=find_kind(*take_seed,"own_param"),tm=find_kind(*take_seed,"move");
        for(const std::string bad:{"i64","string","[spool;1]"}) {Unit c=*take_seed;c.arena[tp].second=bad;verify_expected(c,false);++targeted;}
        std::vector<std::function<void(Unit &)>> take_corruptions={
            [=](Unit &v){v.arena[tp].kind="param";},
            [=](Unit &v){v.arena[tp].kind="borrow_param";},
            [=](Unit &v){v.arena[tp].value_kind="string";},
            [=](Unit &v){v.arena[tp].symbol.clear();},
            [=](Unit &v){v.arena[tm].type="bool";},
            [=](Unit &v){v.arena[tm].children.clear();},
            [](Unit &v){auto &c=v.arena[find_kind(v,"call","spool_bytes")];c.value="spool_free";c.type="unit";},
            [](Unit &v){v.project_syntax=false;}
        };
        for(const auto &mutate:take_corruptions) {Unit copy=*take_seed;mutate(copy);verify_expected(copy,false);++targeted;}
        auto take_alias=checked_source("function f(borrow a:spool,own b:spool)->unit end function main()->i64 scoped x:spool=spool_new(8) scoped y:spool=spool_new(8) f(x,move y) return 0 end",true);
        const auto tx=find_kind(*take_alias,"name","x"),ty=find_kind(*take_alias,"name","y");take_alias->arena[tx].value="y";take_alias->arena[tx].symbol=take_alias->arena[ty].symbol;
        verify_expected(*take_alias,false);++targeted;
        auto take_duplicate=checked_source("function f(own a:spool,own b:spool)->unit end function main()->i64 scoped x:spool=spool_new(8) scoped y:spool=spool_new(8) f(move x,move y) return 0 end",true);
        const auto dx=find_kind(*take_duplicate,"name","x"),dy=find_kind(*take_duplicate,"name","y");take_duplicate->arena[dy].value="x";take_duplicate->arena[dy].symbol=take_duplicate->arena[dx].symbol;
        verify_expected(*take_duplicate,false);++targeted;
        auto take_escape=checked_source("function f(own b:spool)->spool return spool_new(1) end function main()->i64 return 0 end",true);
        const auto te=find_kind(*take_escape,"own_param"),tr=find_kind(*take_escape,"return");auto &ten=take_escape->arena[take_escape->arena[tr].children[0]];
        ten.kind="name";ten.value_kind="string";ten.value="b";ten.children.clear();ten.symbol=take_escape->arena[te].symbol;
        verify_expected(*take_escape,false);++targeted;
        auto legacy_own=checked_source("function own(own:i64)->i64 return own+1 end function main()->i64 return own(1) end",false);verify_expected(*legacy_own,true);
        auto result_seed=checked_source("function make()->own spool scoped b:spool=spool_new(8) return move b end function main()->i64 scoped a:spool=make() return 0 end",true);
        verify_expected(*result_seed,true);
        const auto rf=find_kind(*result_seed,"function","make"),rm=find_kind(*result_seed,"move"),rs=find_kind(*result_seed,"scoped_local","a");
        std::vector<std::function<void(Unit &)>> result_corruptions={
            [=](Unit &v){v.arena[rf].result_mode="borrow";},
            [=](Unit &v){v.arena[rf].result_mode="";},
            [=](Unit &v){v.arena[rf].second="i64";},
            [=](Unit &v){v.arena[rm].result_mode="own";},
            [=](Unit &v){v.arena[rm].type="bool";},
            [=](Unit &v){v.arena[rm].children.clear();},
            [=](Unit &v){v.arena[rs].kind="local";},
            [](Unit &v){v.project_syntax=false;},
            [](Unit &v){v.arena[find_kind(v,"scoped_local","b")].kind="local";}
        };
        for(const auto &mutate:result_corruptions) {Unit copy=*result_seed;mutate(copy);verify_expected(copy,false);++targeted;}
        for(const std::string path:{"if true then scoped b:spool=move a end", "if false then else scoped b:spool=move a end", "if true then scoped b:spool=move a local a:i64=1 end", "if true then scoped a:spool=move a end", "if true then if true then scoped b:spool=move a end end", "if true then scoped b:spool=move a else scoped c:spool=move a end", "if true then if false then else scoped b:spool=move a end local a:i64=1 end", "if true then scoped b:spool=move a scoped a:spool=spool_new(8) end", "if true then scoped b:spool=move a else return 1 end"}) {
            auto joined=checked_source("function main()->i64 scoped a:spool=spool_new(8) scoped spare:spool=spool_new(8) "+path+" print(spool_valid(spare)) return 0 end",true);
            verify_expected(*joined,true);
            const auto source=find_kind(*joined,"scoped_local","a"),use=find_kind(*joined,"name","spare");
            joined->arena[use].value="a";joined->arena[use].symbol=joined->arena[source].symbol;
            verify_expected(*joined,false);++targeted;
        }
        for(const auto &path:std::vector<std::string>{
            "match r then case Route.One(n) then scoped b:spool=move a case Route.Two() then end",
            "match r then case Route.One(n) then case Route.Two() then scoped b:spool=move a end",
            "match r then case Route.One(n) then scoped b:spool=move a local a:i64=1 case Route.Two() then end",
            "match r then case Route.One(n) then scoped a:spool=move a case Route.Two() then end",
            "match r then case Route.One(n) then if true then scoped b:spool=move a end case Route.Two() then end",
            "if true then match r then case Route.One(n) then scoped b:spool=move a case Route.Two() then end end",
            "match r then case Route.One(n) then scoped b:spool=move a case Route.Two() then return 1 end",
            "match r then case Route.One(n) then scoped b:spool=move a case Route.Two() then scoped b:spool=move a end",
            "match r then case Route.One(n) then scoped b:spool=move a scoped a:spool=spool_new(8) case Route.Two() then end"}) {
            auto joined=checked_source("union Route One(n:i64) Two() end function main()->i64 scoped a:spool=spool_new(8) scoped spare:spool=spool_new(8) local r:Route=Route.One(1) "+path+" print(spool_valid(spare)) return 0 end",true);
            verify_expected(*joined,true);
            const auto owner=find_kind(*joined,"scoped_local","a"),use=find_kind(*joined,"name","spare");
            joined->arena[use].value="a";joined->arena[use].symbol=joined->arena[owner].symbol;
            verify_expected(*joined,false);++targeted;
        }
        for(const auto &path:std::vector<std::string>{
            "take(move a)",
            "if true then take(move a) else take(move a) end",
            "if true then if true then take(move a) else take(move a) end else take(move a) end",
            "match R.A() then case R.A() then take(move a) case R.B() then take(move a) end",
            "if true then take(move a) local a:i64=1 else take(move a) end",
            "match R.A() then case R.A() then take(move a) local a:i64=1 case R.B() then take(move a) end",
            "if true then take(move a) else return 1 end",
            "match R.A() then case R.A() then take(move a) case R.B() then return 1 end",
            "if true then match R.B() then case R.A() then take(move a) case R.B() then take(move a) end else take(move a) end"}) {
            auto restored=checked_source("union R A() B() end function take(own b:spool)->unit end function main()->i64 scoped a:spool=spool_new(8) "+path+" a=spool_new(16) print(spool_capacity(a)) return 0 end",true);
            verify_expected(*restored,true);
            const auto statement=find_kind(*restored,"expr");bool removed=false;
            for(auto &node:restored->arena) if(node.kind=="#list") {
                const auto it=std::find(node.children.begin(),node.children.end(),statement);
                if(it!=node.children.end()) {node.children.erase(it);removed=true;break;}
            }
            assert_test(removed,"missing reinit consuming statement");verify_expected(*restored,false);++targeted;
        }
        for(const auto &body:std::vector<std::string>{
            "take(move a) a=make()",
            "if true then take(move a) a=make() else take(move a) a=make() end",
            "match R.A() then case R.A() then take(move a) a=make() case R.B() then take(move a) a=make() end",
            "while false do take(move a) a=make() end",
            "take(move a) a=make() local a:i64=1",
            "if true then take(move a) a=make() else return 1 end",
            "match R.A() then case R.A() then take(move a) a=make() case R.B() then return 1 end",
            "if true then while false do take(move a) a=make() end end",
            "match R.A() then case R.A() then if true then take(move a) a=make() end case R.B() then end"}) {
            auto loop=checked_source("union R A() B() end function take(own b:spool)->unit end function make()->own spool scoped b:spool=spool_new(8) return move b end function main()->i64 scoped a:spool=spool_new(8) while false do "+body+" end print(spool_capacity(a)) return 0 end",true);
            verify_expected(*loop,true);const auto refill=find_kind(*loop,"assign","a");bool removed=false;
            for(auto &node:loop->arena) if(node.kind=="#list") {const auto it=std::find(node.children.begin(),node.children.end(),refill);if(it!=node.children.end()) {node.children.erase(it);removed=true;break;}}
            assert_test(removed,"missing loop refill assignment");verify_expected(*loop,false);++targeted;
        }
        auto vector_seed=checked_source("function make()->own int_vector scoped v:int_vector=int_vector_new(8) int_vector_push(v,42) return move v end function take(own v:int_vector)->own int_vector return move v end function size(borrow v:int_vector)->i64 return int_vector_length(v) end function main()->i64 scoped v:int_vector=make() scoped b:int_vector=take(move v) print(size(b)) return 0 end",true);
        verify_expected(*vector_seed,true);
        const auto vf=find_kind(*vector_seed,"function","make"),vs=find_kind(*vector_seed,"scoped_local","v"),vm=find_kind(*vector_seed,"move"),vp=find_kind(*vector_seed,"own_param"),vb=find_kind(*vector_seed,"borrow_param");
        std::vector<std::function<void(Unit &)>> vector_corruptions={
            [=](Unit &v){v.arena[vf].second="spool";},
            [=](Unit &v){v.arena[vf].result_mode="";},
            [=](Unit &v){v.arena[vs].second="spool";},
            [=](Unit &v){v.arena[vs].kind="local";},
            [=](Unit &v){v.arena[vm].type="spool";},
            [=](Unit &v){v.arena[vp].second="spool";},
            [=](Unit &v){v.arena[vp].kind="borrow_param";},
            [=](Unit &v){v.arena[vb].kind="param";},
            [=](Unit &v){v.arena[vb].second="i64";},
            [](Unit &v){v.arena[find_kind(v,"call","int_vector_push")].value="int_vector_free";},
            [](Unit &v){v.arena[find_kind(v,"call","int_vector_length")].value="spool_bytes";},
            [](Unit &v){v.project_syntax=false;}
        };
        for(const auto &mutate:vector_corruptions) {Unit copy=*vector_seed;mutate(copy);verify_expected(copy,false);++targeted;}
        auto vector_alias=checked_source("function f(borrow a:int_vector,own b:int_vector)->unit end function main()->i64 scoped a:int_vector=int_vector_new(0) scoped b:int_vector=int_vector_new(0) f(a,move b) return 0 end",true);
        const auto va=find_kind(*vector_alias,"name","a"),vbname=find_kind(*vector_alias,"name","b");vector_alias->arena[vbname].value="a";vector_alias->arena[vbname].symbol=vector_alias->arena[va].symbol;verify_expected(*vector_alias,false);++targeted;
        auto argument_seed=checked_source("function main()->i64 if arg_i64_valid(0) then print(arg_i64(0)) end print(arg_count()) return 0 end",true);verify_expected(*argument_seed,true);
        Unit argument_bad=*argument_seed;argument_bad.arena[find_kind(argument_bad,"call","arg_i64")].type="u64";verify_expected(argument_bad,false);++targeted;
        Unit argument_arity=*argument_seed;argument_arity.arena[find_kind(argument_arity,"call","arg_count")].children.push_back(find_kind(argument_arity,"int"));verify_expected(argument_arity,false);++targeted;
        auto file_seed=checked_source("function main()->i64 local f:i64=file_open(\"input\",0) defer file_close(f) print(file_valid(f)) print(file_size(f)) return 0 end",true);verify_expected(*file_seed,true);
        for(const auto &change:std::vector<std::function<void(Unit&)>>{
            [](Unit &v){v.arena[find_kind(v,"call","file_close")].type="unit";},
            [](Unit &v){v.arena[find_kind(v,"call","file_close")].value="file_size";},
            [](Unit &v){v.arena[find_kind(v,"call","file_size")].type="bool";},
            [](Unit &v){v.arena[find_kind(v,"call","file_open")].children.pop_back();}
        }) {Unit changed_file=*file_seed;change(changed_file);verify_expected(changed_file,false);++targeted;}
        auto vector_legacy=checked_source("struct int_vector x:i64 end function main()->i64 local v:int_vector=int_vector(42) return v.x end",false);verify_expected(*vector_legacy,true);
        Unit orphan=*array_seed;
        Node junk{"local",0,"pair","junk","[forged_element;2]","",{}};junk.type="[forged_element;2]";
        orphan.arena.push_back(junk);verify_expected(orphan,true);
        Node ignored_vector{"scoped_local",0,"pair","orphan_vector","int_vector","",{}};ignored_vector.type="int_vector";orphan.arena.push_back(ignored_vector);
        CEmitter orphan_emitter(orphan);assert_test(orphan_emitter.emit().find("forged_element")==std::string::npos,"emitted orphan type metadata");
        assert_test(orphan_emitter.emit().find("KIntVector")==std::string::npos,"emitted orphan vector metadata");
        // Reachable-node mutation sweep: each edit violates one representation
        // invariant irrespective of the selected node's semantic role.
        std::vector<Id> reachable,stack=seed->roots;
        while(!stack.empty()) {auto id=stack.back();stack.pop_back();reachable.push_back(id);const auto &n=seed->arena[id];stack.insert(stack.end(),n.children.begin(),n.children.end());}
        std::mt19937 rng(710);
        for(size_t i=0;i<10000;++i) {
            Unit copy=*seed;const auto id=reachable[rng()%reachable.size()];auto &n=copy.arena[id];
            switch(rng()%6) {
                case 0:n.token=UINT32_MAX;break;
                case 1:n.children.push_back(id);break;
                case 2:n.children.push_back(UINT32_MAX);break;
                case 3:n.value_kind="forged";break;
                case 4:n.kind="forged";break;
                default:n.kind=std::string(33,'x');break;
            }
            verify_expected(copy,false);
        }
        // An emitter object must not trust an earlier successful verification.
        Unit changed=*seed; CEmitter emitter(changed);const auto first=emitter.emit();
        assert_test(first==emitter.emit(),"non-deterministic repeated emission");
        changed.arena[find_kind(changed,"int")].type="bool";
        bool blocked=false;try {emitter.emit();} catch(const Failure &e) {blocked=e.diagnostic.code=="E500";}
        assert_test(blocked,"backend trusted stale verified state");
        // API failure writes diagnostics, not a repaired or silently accepted IR.
        Unit bad=*seed;bad.arena[find_kind(bad,"int")].type="bool";bad.checked=true;
        assert_test(Awl_verify_unit(&bad)==1&&bad.diagnostics[0].code=="E500","API did not reject forged annotation");
        assert_test(bad.arena[find_kind(bad,"int")].type=="bool","API repaired annotation");
        assert_test(Awl_verify_unit(nullptr)==2,"null verification accepted");
        std::cout<<"native verifier: read-only valid arena, "<<targeted<<" targeted corruptions, 10000 seeded structural corruptions passed\n";
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
