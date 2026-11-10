#include "parse.cpp"
#include <chrono>
#include <functional>
#include <iostream>
#include <random>
static void expect(bool value,const std::string &message) {if(!value) throw std::runtime_error(message);}
static Id find(const Unit &u,const std::string &kind,const std::string &value="") {
    for(Id i=0;i<u.arena.size();++i) if(u.arena[i].kind==kind&&(value.empty()||u.arena[i].value==value)) return i;
    throw std::runtime_error("missing "+kind+value);
}
static void verify(Unit &u,bool good=false) {
    serialize(u);const auto before=u.json;bool failed=false;
    try {Verifier(u).run();}catch(const Failure &f) {expect(f.diagnostic.code=="E500","not verifier failure");failed=true;}
    serialize(u);expect(u.json==before,"verifier mutated arena");expect(good!=failed,"incorrect verifier outcome");
}
static std::unique_ptr<Unit> checked(const std::string &source) {
    auto u=parse_source(source.data(),source.size());expect(u->diagnostics.empty(),"seed parse");Checker(*u).run();Verifier(*u).run();return u;
}
int main() {try {
    const std::string source="enum Outcome Value(value:i64); Empty(); end; func score[i64] :: v:Outcome { match v then case Outcome.Value(x) then return x; case Outcome.Empty() then return 0; end; }; func main[i64] { print(score(Outcome.Value(7))); return 0; };";
    auto seed=checked(source);unsigned tests=0;
    auto run=[&](const std::function<void(Unit &)> &edit,bool good=false) {Unit u=*seed;edit(u);verify(u,good);++tests;};
    run([](Unit &){},true);
    run([](Unit &u){u.arena[u.arena[find(u,"match")].children[1]].children.pop_back();});
    run([](Unit &u){u.arena[find(u,"union_ctor")].value="Missing";});
    run([](Unit &u){u.arena[find(u,"union_ctor")].second="Empty";});
    run([](Unit &u){u.arena[find(u,"union_ctor")].type="bool";});
    run([](Unit &u){u.arena[find(u,"pattern_bind","x")].symbol="bad";});
    run([](Unit &u){u.arena[find(u,"pattern_bind","x")].type="bool";});
    run([](Unit &u){u.arena[find(u,"field_decl")].second="spool";});
    run([](Unit &u){u.arena[find(u,"field_decl")].second="vector<i64>";});
    run([](Unit &u){u.arena[find(u,"field_decl")].second="[i64;2]";});
    run([](Unit &u){u.arena[find(u,"union")].kind="struct";});
    run([](Unit &u){u.arena[find(u,"variant_decl","Empty")].value="Value";});
    auto numeric=checked("enum Number Real(value:f64); end; func main[i64] { match Number.Real(1) then case Number.Real(x) then print(x); return 0; end; };");
    expect(numeric->arena[find(*numeric,"float","1.0")].type=="f64","literal context");++tests;
    const auto dir=std::filesystem::temp_directory_path()/("Awl-enum-ir-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));std::filesystem::create_directories(dir);
    struct Cleanup {std::filesystem::path p;~Cleanup(){std::error_code ec;std::filesystem::remove_all(p,ec);}} cleanup{dir};
    std::ofstream(dir/"main.aw")<<"use Maker.aw as m; func main[i64] { @p x: m.make(); return 0; };";
    std::ofstream(dir/"Maker.aw")<<"enum Secret Empty(); end; exports{@r func make[Secret] { return Secret.Empty(); };};";
    auto project=Project().run(dir/"main.aw");expect(project->diagnostics.empty(),"project parse");Checker(*project).run();verify(*project,true);++tests;
    auto forged=*project;const auto call=find(forged,"call");auto &n=forged.arena[call];n.kind="union_ctor";n.value_kind="pair";n.value=forged.arena[find(forged,"union")].value;n.second="Empty";verify(forged);++tests;
    forged=*project;forged.arena[find(forged,"union")].token=forged.arena[find(forged,"function","main")].token;verify(forged);++tests;
    std::mt19937 random(7319);unsigned emitted=0,rejected=0;
    for(unsigned i=0;i<500;++i) {
        auto text=source;const auto pos=random()%text.size();text.replace(pos,1,std::string(1,";()end_.,"[random()%9]));
        auto u=parse_source(text.data(),text.size());
        if(!u->diagnostics.empty()) {++rejected;continue;}
        try {Checker(*u).run();Verifier(*u).run();expect(!CEmitter(*u).emit().empty(),"empty C");++emitted;}catch(const Failure &) {++rejected;}
    }
    std::cout<<"PASS "<<tests<<" enum verifier/emitter cases,500 mutations ("<<emitted<<" emitted,"<<rejected<<" rejected)\n";return 0;
}catch(const Failure &f){std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
