#include "kparse.cpp"
#include <iostream>
static void expect(bool value,const char *message){if(!value)throw std::runtime_error(message);}
static Id find(const Unit &u,const std::string &kind,const std::string &value=""){for(Id i=0;i<u.arena.size();++i)if(u.arena[i].kind==kind&&(value.empty()||u.arena[i].value==value))return i;throw std::runtime_error("missing node");}
int main(){try{
 const std::string source="func first :: v:view<i64>: i64 { return view.get(v,0); }; func main: i64 { @s data vector<i64>: vector.new<i64>(1); vector.push(data,42); @p window: vector.view(data,0,1); print(first(window)); return 0; };";
 auto seed=parse_source(source.data(),source.size(),true,true);expect(seed->diagnostics.empty(),"parse");Checker(*seed).run();Verifier(*seed).run();unsigned tests=1;
 auto reject=[&](const auto &edit){Unit u=*seed;edit(u);serialize(u);const auto before=u.json;bool failed=false;try{Verifier(u).run();}catch(const Failure &f){expect(f.diagnostic.code=="E500","wrong diagnostic");failed=true;}serialize(u);expect(before==u.json,"verifier mutated IR");expect(failed,"accepted forged view IR");++tests;};
 reject([](Unit &u){u.arena[find(u,"call","view_get_i64")].value="view_get_string";});
 reject([](Unit &u){u.arena[find(u,"call","view_get_i64")].type="string";});
 reject([](Unit &u){u.arena[find(u,"call","view_get_i64")].children.pop_back();});
 reject([](Unit &u){u.arena[find(u,"call","view_get_i64")].value="view_set_i64";});
 reject([](Unit &u){u.arena[find(u,"call","vector_view_i64")].value="vector_view_u64";});
 reject([](Unit &u){u.arena[find(u,"call","vector_view_i64")].type="vector<i64>";});
 reject([](Unit &u){u.arena[find(u,"param","v")].kind="borrow_param";});
 reject([](Unit &u){u.arena[find(u,"param","v")].kind="own_param";});
 reject([](Unit &u){u.arena[find(u,"local","window")].kind="scoped_local";});
 reject([](Unit &u){u.arena[find(u,"function","first")].second="vector<i64>";});
 reject([](Unit &u){u.next_syntax=false;});
 std::cout<<"PASS "<<tests<<" view independent verifier cases\n";return 0;
}catch(const Failure &f){std::cerr<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
