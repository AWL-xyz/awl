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
    const std::string source="func main: i64 { @p s: tcp_listen_loopback(0,1); @p b: buffer_new(8); tcp_valid(s); tcp_port(s); tcp_accept(s,0); tcp_read(s,b,0,8,0); tcp_write(s,b,0,8,0); defer tcp_close(s); buffer_free(b); return 0; };";
    auto seed=parse_source(source.data(),source.size(),true,true);expect(seed->diagnostics.empty(),"seed parse");Checker(*seed).run();verify(*seed,true);unsigned cases=1;
    for(const std::string name:{"tcp_listen_loopback","tcp_valid","tcp_port","tcp_accept","tcp_read","tcp_write","tcp_close"}) {
        const auto id=find(*seed,"call",name);
        auto run=[&](const std::function<void(Unit &)> &edit) {Unit u=*seed;edit(u);verify(u);++cases;};
        run([&](Unit &u) {u.arena[id].type=u.arena[id].type=="bool"?"i64":"bool";});
        run([&](Unit &u) {u.arena[id].value="tcp_injected";});
        run([&](Unit &u) {u.arena[id].children.pop_back();});
        run([&](Unit &u) {u.arena[u.arena[id].children[0]].type="bool";});
    }
    Unit bad=*seed;bad.arena[find(bad,"call","tcp_close")].value="tcp_port";verify(bad);++cases;
    auto code=CEmitter(*seed).emit();expect(code==CEmitter(*seed).emit(),"nondeterministic output");expect(code.starts_with("#define _GNU_SOURCE 1"),"missing feature macro");expect(code.find("static int64_t k_tcp_accept")!=std::string::npos,"missing runtime");++cases;
    std::cout<<"PASS "<<cases<<" tcp independent verifier/emitter cases\n";return 0;
} catch(const Failure &f) {std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}}
