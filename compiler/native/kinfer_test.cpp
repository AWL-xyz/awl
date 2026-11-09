#include "kparse.cpp"
#include <iostream>
static void need(bool ok,const char *message) {if(!ok) throw std::runtime_error(message);}
static std::unique_ptr<Unit> checked(const std::string &source) {
    auto u=parse_source(source.data(),source.size());need(u->diagnostics.empty(),"inference seed parse");Checker(*u).run();Verifier(*u).run();return u;
}
int main() {try {
    auto seed=checked("func main { return answer(); }; func answer { return 42; };");
    for(auto id:seed->roots) need(seed->arena[id].second=="i64","unresolved or wrong inferred signature");
    unsigned checks=0;
    for(auto id:seed->roots) {
        for(const std::string type:{"", "bool", "unit"}) {
            Unit u=*seed;u.arena[id].second=type;bool rejected=false;
            try {Verifier(u).run();}catch(const Failure &f){rejected=f.diagnostic.code=="E500";}
            need(rejected,"forged inferred result accepted");++checks;
        }
    }
    for(const auto &source:{
        "func main { return main(); };",
        "func first { return second(); }; func second { return first(); }; func main { return 0; };",
        "func f :: b:bool { if b { return 1; } else { return false; }; }; func main { return 0; };",
        "func f :: b:bool { if b { return; } else { return 1; }; }; func main { return 0; };",
        "func make { @s b spool: spool.new(1); return move b; }; func main { return 0; };"
    }) {
        auto u=parse_source(source,std::char_traits<char>::length(source));need(u->diagnostics.empty(),"negative inference seed parse");bool rejected=false;
        try {Checker(*u).run();}catch(const Failure &f){rejected=f.diagnostic.code=="E233";}
        need(rejected,"ambiguous/circular/owned inference accepted");++checks;
    }
    auto unit=checked("func notify { print(1); }; func main { notify(); return 0; };");
    auto explicit_cycle=checked("func f[i64] { return g(); }; func g { return f(); }; func main { return 0; };");
    auto unit_cycle=checked("func a { b(); }; func b { a(); }; func main { return 0; };");++checks;
    seed->checked=false;Verifier(*seed).run();need(!CEmitter(*seed).emit().empty(),"inferred source emission failed");checks+=3;
    std::cout<<"PASS "<<checks<<" return inference/checker/independent-verifier cases\n";return 0;
} catch(const Failure &f){std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}
catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
