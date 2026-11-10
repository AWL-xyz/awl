// Test-only: corrupt private project metadata without exporting mutation APIs.
#include "parse.cpp"
#include <functional>
#include <iostream>
static void require_project(bool value,const char *message) {if(!value) throw std::runtime_error(message);}
int main() {
    namespace fs=std::filesystem;
    const auto folder=fs::temp_directory_path()/("Awl-project-native-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    struct Cleanup {fs::path p;~Cleanup(){std::error_code ec;fs::remove_all(p,ec);}} cleanup{folder};
    try {
        fs::create_directories(folder);
        {std::ofstream f(folder/"main.aw");f<<"use lib.aw as lib; func main[i64] { return lib.answer(); };";}
        {std::ofstream f(folder/"lib.aw");f<<"-- Unicode: \xce\xbb\nexports{@r func answer[i64] { return 42; };};";}
        auto seed=parse_project((folder/"main.aw").string().c_str());
        require_project(seed->diagnostics.empty(),"project parse failed");
        Checker checker(*seed);checker.run();Verifier v(*seed);v.run();
        serialize(*seed);const auto before=seed->json;
        v.run();serialize(*seed);require_project(before==seed->json,"verifier changed project");
        std::vector<std::function<void(Unit&)>> changes={
            [](Unit &u){u.origins[0].file=64;},
            [](Unit &u){u.origins[0].end=UINT32_MAX;},
            [](Unit &u){u.origins[0].start=u.origins[0].end+1;},
            [](Unit &u){u.origins.pop_back();},
            [](Unit &u){u.file_lengths.pop_back();},
            [](Unit &u){u.file_lengths[0]=0;},
            [](Unit &u){u.tokens[0].end+=1;},
            [](Unit &u){u.files.clear();}
        };
        for(const auto &change:changes) {
            Unit copy=*seed;change(copy);bool rejected=false;
            try {Verifier candidate(copy);candidate.run();} catch(const Failure &e) {rejected=e.diagnostic.code=="E500";}
            require_project(rejected,"forged project metadata accepted");
        }
        void *opaque=nullptr;
        require_project(Awl_parse_file((folder/"main.aw").string().c_str(),&opaque)==0&&opaque,"filesystem API failed");
        struct UnitCleanup {void *p;~UnitCleanup(){Awl_parse_free(p);}} owner{opaque};
        require_project(Awl_source_file_count(opaque)==2,"wrong project file count");
        require_project(Awl_source_file_path(opaque,0)&&Awl_source_file_path(opaque,1)&&!Awl_source_file_path(opaque,2),"bad source enumeration");
        require_project(Awl_source_file_count(nullptr)==0&&!Awl_source_file_path(nullptr,0),"bad null enumeration");
        require_project(Awl_check_unit(opaque)==0&&Awl_verify_unit(opaque)==0,"filesystem API check rejected");
        const char *c=nullptr;size_t size=0;require_project(Awl_emit_c(opaque,&c,&size)==0&&c&&size,"filesystem API emission failed");
        std::cout<<"native projects: resolved arena, read-only verifier, 8 provenance corruptions, filesystem C ABI passed\n";
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
