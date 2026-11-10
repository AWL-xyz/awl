// Contributor-only mutation harness. No mutation API is shipped.
#include "parse.cpp"
#include <chrono>
#include <functional>
#include <iostream>
#include <random>
static void expect(bool b,const std::string &s){if(!b) throw std::runtime_error(s);}
static std::unique_ptr<Unit> checked(const std::string &source) {
    auto u=parse_source(source.data(),source.size());expect(u->diagnostics.empty(),"parse seed failed");Checker(*u).run();Verifier(*u).run();return u;
}
static Id find(const Unit &u,const std::string &kind,const std::string &value="") {
    for(Id id=0;id<u.arena.size();++id) if(u.arena[id].kind==kind&&(value.empty()||u.arena[id].value==value)) return id;
    throw std::runtime_error("missing target "+kind+" "+value);
}
static void verify(Unit &u,bool good=false) {
    serialize(u);const auto before=u.json;const auto order=u.global_order;const auto modules=u.module_order;const auto edges=u.module_dependencies;bool rejected=false;
    try{Verifier(u).run();}catch(const Failure &f){expect(f.diagnostic.code=="E500","not verifier failure");rejected=true;}
    serialize(u);expect(before==u.json&&order==u.global_order&&modules==u.module_order&&edges==u.module_dependencies,"verifier mutated arena/order");expect(good!=rejected,"incorrect verifier outcome");
}
int main(){try {
    const std::string source="@p first: 128.59; exports{@r second: first+1; @w counter: 0;}; func main[i64] { counter: counter+1; print(sin(pi/2)); print(second); return 0; };";
    unsigned tests=0;
    auto run=[&](const std::function<void(Unit &)> &edit,bool good=false){auto u=checked(source);edit(*u);verify(*u,good);++tests;};
    run([](Unit &){},true);
    run([](Unit &u){u.arena[find(u,"float","128.59")].value="1.0);system(0)";});
    run([](Unit &u){u.arena[find(u,"float","128.59")].type="i64";});
    run([](Unit &u){u.arena[find(u,"float","128.59")].value="1e999";});
    run([](Unit &u){u.arena[find(u,"global","first")].second="spool";});
    run([](Unit &u){u.arena[find(u,"global","first")].result_mode="wat";});
    run([](Unit &u){u.arena[find(u,"global_ref","first")].symbol="k_v999999";});
    run([](Unit &u){u.arena[find(u,"global_assign")].symbol="k_v999999";});
    run([](Unit &u){u.arena[find(u,"global","first")].symbol=u.arena[find(u,"global","counter")].symbol;});
    run([](Unit &u){u.global_order.clear();});
    run([](Unit &u){std::reverse(u.global_order.begin(),u.global_order.end());});
    run([](Unit &u){u.global_order.push_back(u.global_order[0]);});
    run([](Unit &u){u.module_order[0]=1;});
    run([](Unit &u){u.module_dependencies[0].push_back(0);});
    run([](Unit &u){auto &call=u.arena[find(u,"call","sin")];call.value="atan2";});
    run([](Unit &u){auto &op=u.arena[find(u,"binary","/")];op.value="%";});
    run([](Unit &u){u.arena[find(u,"global_ref","first")].value="counter";u.arena[find(u,"global_ref","counter")].symbol="k_v999999";});
    // Cross-module permissions are verified independently from source lowering.
    const auto folder=std::filesystem::temp_directory_path()/("Awl-module-ir-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));std::filesystem::create_directories(folder);
    struct Cleanup{std::filesystem::path p;~Cleanup(){std::error_code ec;std::filesystem::remove_all(p,ec);}} cleanup{folder};
    std::ofstream(folder/"main.aw")<<"use Lib.aw as m; @p own_value: m.value+1; func main[i64] { m.value: 7; print(m.value); return 0; };";
    std::ofstream(folder/"Lib.aw")<<"exports{@w value: 1;};";
    auto project=[&](){auto u=Project().run(folder/"main.aw");expect(u->diagnostics.empty(),"project parse");Checker(*u).run();Verifier(*u).run();return u;};
    {auto u=project();verify(*u,true);++tests;}
    for(const auto &mode:{"r","p"}){auto u=project();const auto id=find(*u,"global","km_1_0");u->arena[id].result_mode=mode;verify(*u);++tests;}
    {auto u=project();u->module_order={0,1};verify(*u);++tests;}
    {auto u=project();u->arena[find(*u,"global","km_1_0")].token=u->arena[find(*u,"function","main")].token;verify(*u);++tests;}
    std::mt19937 rng(20261106);unsigned accepted=0,rejected=0;
    for(unsigned i=0;i<1000;++i){auto text=source;const auto pos=rng()%text.size();if(i%3==0)text.erase(pos,1);else if(i%3==1)text.insert(pos,1,";:@()=.0123456789"[rng()%16]);else text[pos]=static_cast<char>(rng()%256);auto u=parse_source(text.data(),text.size());if(!u->diagnostics.empty()){++rejected;continue;}try{Checker(*u).run();}catch(const Failure&){++rejected;continue;}Verifier(*u).run();expect(!CEmitter(*u).emit().empty(),"empty C");++accepted;}
    std::cout<<tests<<" module/f64 verifier cases; 1000 production mutations ("<<accepted<<" checked/emitted, "<<rejected<<" rejected) PASS\n";return 0;
}catch(const Failure &f){std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
