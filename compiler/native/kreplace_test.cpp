#include "kparse.cpp"
#include <functional>
#include <iostream>
static void expect(bool ok,const std::string &message) {if(!ok) throw std::runtime_error(message);}
static Id find(const Unit &u,const std::string &kind,const std::string &value) {
    for(Id i=0;i<u.arena.size();++i) if(u.arena[i].kind==kind&&u.arena[i].value==value) return i;
    throw std::runtime_error("missing node "+value);
}
static void verify(Unit &u,bool good=false) {
    serialize(u);const auto before=u.json;bool rejected=false;
    try {Verifier(u).run();}catch(const Failure &f) {expect(f.diagnostic.code=="E500","not E500");rejected=true;}
    serialize(u);expect(u.json==before,"verifier mutated arena");expect(good!=rejected,"incorrect verifier result");
}
int main() {try {
    const std::string source="func main[i64] { return file_replace(\".\",\"temp\",\"target\"); };";
    auto seed=parse_source(source.data(),source.size());expect(seed->diagnostics.empty(),"seed parse");Checker(*seed).run();verify(*seed,true);unsigned cases=1;
    for(const std::string name:{"file_replace"}) {
        const auto id=find(*seed,"call",name);
        auto run=[&](const std::function<void(Unit &)> &edit) {Unit u=*seed;edit(u);verify(u);++cases;};
        run([&](Unit &u) {u.arena[id].type=u.arena[id].type=="bool"?"i64":"bool";});
        run([&](Unit &u) {u.arena[id].value="tcp_injected";});
        run([&](Unit &u) {u.arena[id].children.pop_back();});
        run([&](Unit &u) {u.arena[u.arena[id].children[0]].type="bool";});
    }
    auto code=CEmitter(*seed).emit();expect(code==CEmitter(*seed).emit(),"nondeterministic output");expect(code.find("static int64_t k_file_replace(")!=std::string::npos,"missing runtime");++cases;
    std::cout<<"PASS "<<cases<<" replace independent verifier/emitter cases\n";return 0;
} catch(const Failure &f) {std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}}
