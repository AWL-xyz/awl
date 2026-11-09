#include "kparse.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
void require(bool value) { if(!value) throw std::runtime_error("native frontend assertion failed"); }
void exercise(const std::string &source) {
    void *unit=nullptr;
    require(Awl_parse_source(source.data(),source.size(),&unit)==0&&unit);
    struct Cleanup {void *p; ~Cleanup(){Awl_parse_free(p);}} cleanup{unit};
    size_t size=0; require(Awl_parse_json(unit,&size)&&size>0);
    const auto result=Awl_check_unit(unit); require(result==0||result==1);
    require(Awl_check_unit(unit)==result);
    if(result==0) {
        require(Awl_verify_unit(unit)==0);require(Awl_verify_unit(unit)==0);
        const char *output=nullptr;size_t length=0;
        require(Awl_emit_c(unit,&output,&length)==0&&output&&length);
        const std::string before(output,length);
        require(Awl_emit_c(unit,&output,&length)==0&&std::string(output,length)==before);
    }
    require(Awl_parse_json(unit,&size)&&size>0);
    require(Awl_render_diagnostics(unit,"source.aw",1,&size)&&size>0);
    require(Awl_render_diagnostics(unit,"source.aw",0,&size));
    require(Awl_parse_node_count(unit)<=200002);
}
int main(int argc,char **argv) {
    try {
        require(Awl_parse_abi_version()==2);
        void *unit=nullptr; size_t size=0;
        require(Awl_parse_source(nullptr,1,&unit)==1&&!unit);
        require(Awl_parse_source("",0,nullptr)==1);
        require(Awl_check_unit(nullptr)==2);
        require(!Awl_parse_json(nullptr,&size)); Awl_parse_free(nullptr);
        AwlLexToken eof{0,0,1,1,0};
        require(Awl_parse_tokens("",0,&eof,1,&unit)==0&&unit); Awl_parse_free(unit); unit=nullptr;
        eof.end=1; require(Awl_parse_tokens("",0,&eof,1,&unit)==1&&!unit);
        exercise("struct P ) end"); exercise("union U V( end");
        exercise("func main[i64] { return "+std::string(100,'(')+"0"+std::string(100,')')+"; };");
        exercise(std::string(1048577,'x'));
        std::string tokens; for(int i=0;i<100001;++i) tokens+="1 "; exercise(tokens);
        std::vector<std::string> seeds={"func main[i64] { return 0; };"};
        for(int i=1;i<argc;++i) {
            std::ifstream file(argv[i],std::ios::binary); require(static_cast<bool>(file));
            seeds.emplace_back(std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>()); exercise(seeds.back());
        }
        std::mt19937 rng(709);
        for(int i=0;i<10000;++i) {
            std::string raw; for(unsigned j=0,limit=rng()%256;j<limit;++j) raw.push_back(static_cast<char>(rng()%256)); exercise(raw);
            auto source=seeds[rng()%seeds.size()]; const auto at=rng()%source.size(); const auto count=rng()%16;
            source.replace(at,count,std::vector<std::string>{"","end","case", "(",")","true","Missing","struct"}[rng()%8]); exercise(source);
        }
        std::cout<<"native frontend: ABI, limits, examples, 10000 raw-byte inputs, 10000 source mutations passed\n";
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
