// Contributor-only white-box test; no private arena mutation API is shipped.
#include "kparse.cpp"
#include <chrono>
#include <functional>
#include <iostream>
#include <random>
static void expect(bool value,const std::string &message) {if(!value) throw std::runtime_error(message);}
static std::unique_ptr<Unit> checked(const std::string &source) {
    auto u=parse_source(source.data(),source.size());expect(u->diagnostics.empty(),"Aesop seed parse failure");Checker(*u).run();Verifier(*u).run();return u;
}
static Id find(const Unit &u,const std::string &kind,const std::string &value="") {
    for(Id id=0;id<u.arena.size();++id) if(u.arena[id].kind==kind&&(value.empty()||u.arena[id].value==value)) return id;
    throw std::runtime_error("missing mutation node "+kind+" "+value);
}
static void verify(Unit &u,bool good) {
    serialize(u);const auto before=u.json;const auto exports=u.public_functions;const auto parents=u.nested_parents;bool failed=false;
    try {Verifier(u).run();} catch(const Failure &f) {expect(f.diagnostic.code=="E500","non-verifier failure");failed=true;}
    serialize(u);expect(u.json==before&&u.public_functions==exports&&u.nested_parents==parents,"verifier mutated arena/visibility metadata");expect(failed!=good,"unexpected verifier outcome");
}
int main() {try {
    unsigned tests=0;
    const auto temp=std::filesystem::temp_directory_path()/("aesop-ir-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));std::filesystem::create_directories(temp);
    struct Cleanup {std::filesystem::path path;~Cleanup(){std::error_code ec;std::filesystem::remove_all(path,ec);}} cleanup{temp};
    {std::ofstream(temp/"main.aw")<<"use Lib.aw as lib; func main[i64] { print(lib.answer()); return 0; };";
     std::ofstream(temp/"Lib.aw")<<"func hidden[i64] { return 99; }; exports{@r func answer[i64] { @p func helper[i64] { return hidden(); }; return helper(); };};";}
    auto project=[&](){auto u=Project().run(temp/"main.aw");expect(u->diagnostics.empty(),"project parse failed");Checker(*u).run();Verifier(*u).run();return u;};
    auto run=[&](const std::function<void(Unit &)> &mutation,bool good=false){auto u=project();mutation(*u);verify(*u,good);++tests;};
    run([](Unit &){},true);
    std::filesystem::create_directory(temp/"sub");std::filesystem::copy_file(temp/"Lib.aw",temp/"sub/Thing.aw");
    for(const auto &[path,alias]:std::vector<std::pair<std::string,std::string>>{{"Lib.aw","Lib"},{"\"Lib.aw\"","Lib"},{"sub/Thing.aw","Thing"}}) {
        std::ofstream(temp/"main.aw")<<"use "<<path<<"; func main[i64] { print("<<alias<<".answer()); return 0; };";
        auto u=project();expect(!CEmitter(*u).emit().empty(),"implicit namespace emission failed");++tests;
    }
    std::ofstream(temp/"main.aw")<<"use Lib.aw as lib; func main[i64] { print(lib.answer()); return 0; };";

    run([](Unit &u){const auto name=u.arena.at(find(u,"function","main")).value;expect(name=="main","entry renamed");for(auto &n:u.arena) if(n.kind=="call"&&u.public_functions.contains(n.value)) {n.value="km_1_0";return;}throw std::runtime_error("public call absent");});
    run([](Unit &u){u.public_functions.clear();});
    run([](Unit &u){u.public_functions.insert("not_a_function");});
    run([](Unit &u){for(auto &n:u.arena) if(n.kind=="call"&&u.public_functions.contains(n.value)) {n.value="km_1_0";n.token=u.arena.at(find(u,"function","km_1_0")).token;return;}throw std::runtime_error("public call absent");});
    run([](Unit &u){u.arena.at(find(u,"function","main")).token=u.arena.at(find(u,"function","km_1_0")).token;});
    run([](Unit &u){u.arena.at(find(u,"function","km_1_0")).token=u.arena.at(find(u,"function","main")).token;});
    run([](Unit &u){auto it=u.nested_parents.begin();expect(it!=u.nested_parents.end(),"helper parent absent");it->second=it->first;});
    run([](Unit &u){auto it=u.nested_parents.begin();it->second="not_a_function";});
    const std::string source="func outer[i64] { @p func helper[i64] { return 42; }; return helper(); }; func unrelated[i64] { return 1; }; func main[i64] { print(outer()); return 0; };";
    {auto u=checked(source);auto &call=u->arena.at(find(*u,"call","outer"));call.value=u->nested_parents.begin()->first;verify(*u,false);++tests;}
    {auto u=checked(source);u->nested_parents.begin()->second="unrelated";verify(*u,false);++tests;}
    {auto u=checked(source);u->arena.at(find(*u,"int","42")).type="bool";verify(*u,false);++tests;}
    {auto u=checked("func main[i64] { @p n: 42; print(n); return 0; };");u->arena.at(find(*u,"local")).second="u8";verify(*u,false);++tests;}
    std::filesystem::create_directory(temp/"Sub");std::ofstream(temp/"Sub"/"Upper.aw")<<"exports{@r func f[i64] { return 42; };};";
    for(const auto &[path,valid]:std::vector<std::pair<std::string,bool>>{{"Sub/Upper.aw",true},{"sub/Upper.aw",false},{"Sub/upper.aw",false},{"lib.aw",false}}) {
        std::ofstream(temp/"main.aw")<<"use "<<path<<" as m; func main[i64] { return 0; };";
        auto u=Project().run(temp/"main.aw");
        if(valid) {expect(u->diagnostics.empty(),"exact-case import rejected");Checker(*u).run();Verifier(*u).run();}
        else expect(u->diagnostics.size()==1&&u->diagnostics[0].code=="E300"&&u->diagnostics[0].message.find("wrong-case")!=std::string::npos,"wrong-case import accepted or wrong diagnostic");
        ++tests;
    }
    // Check structural/error recovery under deterministic lexical mutations. A
    // surviving checked unit must also pass the separate verifier and emitter.
    std::mt19937 rng(20261106);unsigned accepted=0,rejected=0;
    for(unsigned i=0;i<500;++i) {
        auto text=source;const auto pos=static_cast<size_t>(rng()%text.size());if(i%3==0) text.erase(pos,1);else if(i%3==1) text.insert(pos,1,";:@(){}=\n"[rng()%9]);else text[pos]=static_cast<char>(rng()%256);
        auto u=parse_source(text.data(),text.size());
        if(!u->diagnostics.empty()) {++rejected;continue;}
        try {Checker(*u).run();} catch(const Failure &) {++rejected;continue;}
        Verifier(*u).run();expect(!CEmitter(*u).emit().empty(),"empty emission");++accepted;
    }
    AwlLexResult raw{};expect(Awl_lex("@",1,&raw)==0,"Aesop scanner lost @");Awl_lex_free(&raw);
    for(unsigned i=0;i<10000;++i) {
        std::string bytes;for(unsigned j=0,count=rng()%256;j<count;++j) bytes.push_back(static_cast<char>(rng()%256));
        const auto status=Awl_lex(bytes.data(),bytes.size(),&raw);expect(status==0||status==1||status==4||status==6,"unexpected Aesop scanner result");expect(raw.count<=100001,"scanner token cap");
        for(uint32_t j=0;j<raw.count;++j) expect(raw.tokens[j].start<raw.tokens[j].end&&raw.tokens[j].end<=bytes.size(),"scanner span bounds");
        Awl_lex_free(&raw);Awl_lex_free(&raw);
    }
    std::cout<<tests<<" Aesop verifier positive/negative cases; 500 seeded production mutations ("<<accepted<<" checked/emitted, "<<rejected<<" rejected); 10000 raw-byte Aesop scanner inputs PASS\n";return 0;
} catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;} catch(const Failure &f) {std::cerr<<f.diagnostic.code<<": "<<f.diagnostic.message<<'\n';return 1;}}
