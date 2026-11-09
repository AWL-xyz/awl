#include "kparse.cpp"
#include <chrono>
#include <fstream>
#include <iostream>
static void need(bool v,const char *s){if(!v)throw std::runtime_error(s);}
int main(){try{
 const auto dir=std::filesystem::temp_directory_path()/("Awl-export-ir-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));std::filesystem::create_directories(dir);
 struct Cleanup{std::filesystem::path p;~Cleanup(){std::error_code e;std::filesystem::remove_all(p,e);}}cleanup{dir};
 std::ofstream(dir/"Lib.aw")<<"enum Secret Hidden(); end; exports{@r enum Visible Value(value:i64); Empty(); end; @r func make[Visible] { return Visible.Value(7); }; @r func hidden[Secret] { return Secret.Hidden(); };};";
 std::ofstream(dir/"main.aw")<<"use Lib.aw as lib; func main[i64] { match lib.make() then case lib.Visible.Value(x) then print(x); case lib.Visible.Empty() then print(0); end; return 0; };";
 auto seed=Project().run(dir/"main.aw");need(seed->diagnostics.empty(),"parse");Checker(*seed).run();Verifier(*seed).run();
 auto find=[&](const Unit &u,const std::string &kind,const std::string &second=""){for(Id i=0;i<u.arena.size();++i)if(u.arena[i].kind==kind&&(second.empty()||u.arena[i].second==second))return i;throw std::runtime_error("missing node");};
 unsigned tests=1;
 auto reject=[&](const auto &edit){auto u=*seed;edit(u);serialize(u);const auto before=u.json;bool bad=false;try{Verifier(u).run();}catch(const Failure &f){need(f.diagnostic.code=="E500","diagnostic");bad=true;}serialize(u);need(before==u.json,"mutation");if(!bad)throw std::runtime_error("accepted forged IR at "+std::to_string(tests));++tests;};
 reject([&](Unit &u){for(auto &n:u.arena)if(n.kind=="union"&&n.result_mode=="r")n.result_mode.clear();});
 reject([&](Unit &u){for(auto &n:u.arena)if(n.kind=="union"&&n.result_mode=="r")n.result_mode="rw";});
 reject([&](Unit &u){u.arena[find(u,"union_ctor")].second="Absent";});
 reject([&](Unit &u){u.arena[find(u,"case")].second="Absent";});
 reject([&](Unit &u){const auto secret=u.arena[find(u,"union_ctor","Hidden")];auto &n=u.arena[find(u,"call")];n.kind="union_ctor";n.value_kind="pair";n.value=secret.value;n.second="Hidden";n.type=secret.type;});
 reject([&](Unit &u){for(auto &n:u.arena)if(n.kind=="union"&&n.result_mode=="r")n.token=u.arena[find(u,"function")].token;});
 std::cout<<"PASS "<<tests<<" exported enum independent verifier checks\n";return 0;
 }catch(const Failure &f){std::cerr<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
