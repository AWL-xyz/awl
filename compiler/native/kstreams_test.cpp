#include "kparse.cpp"
#include <functional>
#include <iostream>
static void expect(bool condition,const std::string &message) {if(!condition) throw std::runtime_error(message);}
static Id find(const Unit &u,const std::string &kind,const std::string &value) {
    for(Id i=0;i<u.arena.size();++i) if(u.arena[i].kind==kind&&u.arena[i].value==value) return i;
    throw std::runtime_error("missing test node "+kind+" "+value);
}
static void verify(Unit &u,bool good) {
    serialize(u);const auto before=u.json;bool failed=false;
    try {Verifier(u).run();} catch(const Failure &f) {expect(f.diagnostic.code=="E500","wrong diagnostic");failed=true;}
    serialize(u);expect(before==u.json,"verifier modified arena");expect(failed!=good,"incorrect verifier outcome");
}
int main() {try {
    const std::string text="@p first: 1; func main[i64] { @p b: buffer_new(8); stdin_read(b,0,8); stdout_write(b,0,8); stderr_write(b,0,8); stdout_flush(); stderr_flush(); env_size(\"key\"); env_read(\"key\",b,0,8); buffer_free(b); return 0; };";
    auto seed=parse_source(text.data(),text.size());expect(seed->diagnostics.empty(),"seed parse");Checker(*seed).run();verify(*seed,true);unsigned cases=1;
    for(const auto &name:{"stdin_read","stdout_write","stderr_write","stdout_flush","stderr_flush","env_size","env_read"}) {
        const auto id=find(*seed,"call",name);
        auto run=[&](const std::function<void(Unit &)> &edit){Unit u=*seed;edit(u);verify(u,false);++cases;};
        run([&](Unit &u){u.arena[id].type="bool";});
        run([&](Unit &u){u.arena[id].value="injected_function";});
        if(seed->arena[id].children.empty()) run([&](Unit &u){u.arena[id].children.push_back(find(u,"int","8"));});
        else {
            run([&](Unit &u){u.arena[id].children.pop_back();});
            run([&](Unit &u){u.arena[u.arena[id].children[0]].type="bool";});
        }
        run([&](Unit &u){u.arena[find(u,"global","first")].children[0]=id;});
    }
    std::cout<<cases<<" stream/environment independent verifier cases pass\n";return 0;
} catch(const Failure &f) {std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}}
