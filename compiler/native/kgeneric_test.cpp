#include "kparse.cpp"
#include <functional>
#include <iostream>
static void expect(bool ok,const std::string &message) {if(!ok) throw std::runtime_error(message);}
static Id find(const Unit &u,const std::string &kind,const std::string &value) {
    for(Id i=0;i<u.arena.size();++i) if(u.arena[i].kind==kind&&u.arena[i].value==value) return i;
    throw std::runtime_error("missing node "+value);
}
static std::unique_ptr<Unit> checked(const std::string &source) {
    auto u=parse_source(source.data(),source.size(),true,true);expect(u->diagnostics.empty(),"seed parse");Checker(*u).run();Verifier(*u).run();return u;
}
static void verify(Unit &u,bool good=false) {
    serialize(u);const auto before=u.json;bool rejected=false;
    try {Verifier(u).run();}catch(const Failure &f) {expect(f.diagnostic.code=="E500","not E500");rejected=true;}
    serialize(u);expect(u.json==before,"verifier mutated arena");expect(good!=rejected,"incorrect verifier result");
}
int main() {try {
    const std::string source="func main: i64 { @p v vector<f64>: vector.new<f64>(0); vector.valid(v); vector.length(v); vector.capacity(v); vector.reserve(v,9); vector.push(v,1); vector.get(v,0); vector.swap(v,0,0); vector.truncate(v,0); vector.set(v,0,2); vector.insert(v,0,3); vector.remove(v,0); vector.pop(v); vector.clear(v); vector.slice(v,0,0); vector.free(v); return 0; };";
    auto seed=checked(source);verify(*seed,true);unsigned cases=1;
    for(const std::string method:{"new","valid","length","capacity","reserve","push","get","set","insert","remove","pop","clear","slice","free","swap","truncate"}) {
        const auto id=find(*seed,"call","vector_"+method+"_f64");
        auto run=[&](const std::function<void(Unit &)> &edit) {Unit u=*seed;edit(u);verify(u);++cases;};
        run([&](Unit &u) {u.arena[id].type=u.arena[id].type=="bool"?"i64":"bool";});
        run([&](Unit &u) {u.arena[id].value="vector_"+method+"_i64";});
        run([&](Unit &u) {u.arena[id].children.pop_back();});
        run([&](Unit &u) {u.next_syntax=false;});
        run([&](Unit &u) {u.arena[id].value="vector_"+method;});
    }
    for(const auto &ty:{"vector<text>","vector<vector<i64>>","vector<spool>","vector<bad>","vector< f64>","vector<f64 >"}) {
        Unit u=*seed;u.arena[find(u,"local","v")].second=ty;verify(u);++cases;
    }
    const std::string ownership="func finish :: @o v[f64] {}; func main: i64 { @s v vector<f64>: vector.new<f64>(0); @s copy vector<f64>: vector.slice(v,0,0); finish(move copy); copy: vector.new<f64>(0); return 0; };";
    auto owned=checked(ownership);verify(*owned,true);++cases;
    for(const std::string name:{"vector_free_f64","vector_get_f64","vector_push_f64"}) {
        Unit u=*owned;const auto id=find(u,"call","vector_slice_f64");u.arena[id].value=name;verify(u);++cases;
    }
    Unit orphan=*seed;Node extra{};extra.kind="call";extra.value="vector_new_string";extra.type="vector<string>";orphan.arena.push_back(extra);
    const auto first=CEmitter(*seed).emit(),second=CEmitter(*seed).emit();expect(first==second,"nondeterministic emission");expect(CEmitter(orphan).emit()==first,"orphan changed runtime dependencies");++cases;
    expect(first.find("k_vector_new_string")==std::string::npos,"unused specialization emitted");
    std::cout<<"PASS "<<cases<<" typed-vector independent verifier/emitter cases\n";return 0;
} catch(const Failure &f) {std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}}
