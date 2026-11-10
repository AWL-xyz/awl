#include "lex.h"
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
void require(bool ok) { if(!ok) throw std::runtime_error("native lexer assertion failed"); }
int main() {
    try {
        AwlLexResult r{};
        require(Awl_lex_abi_version()==2);
        const std::string valid="-- \xc3\xa9\nx";
        require(Awl_lex(valid.data(),valid.size(),&r)==0);
        require(r.count==1&&r.tokens[0].start==5&&r.tokens[0].end==6&&r.tokens[0].line==2&&r.tokens[0].column==1);
        Awl_lex_free(&r); Awl_lex_free(&r); Awl_lex_free(nullptr);
        require(Awl_lex(nullptr,1,&r)==5); require(Awl_lex("x",1048577,&r)==3);
        require(Awl_lex("\xed\xa0\x80",3,&r)==4);
        const std::string text="x=\"é🚀\";\n";
        require(Awl_lex(text.data(),text.size(),&r)==0);
        require(r.count==4&&r.tokens[2].flags==4&&r.tokens[2].start==2&&r.tokens[2].end==6&&r.position==8&&r.line==2&&r.column==1);Awl_lex_free(&r);
        require(Awl_lex("\"missing",8,&r)==6&&r.position==0);Awl_lex_free(&r);
        std::string many;
        for(int i=0;i<100001;++i) many+="1 ";
        require(Awl_lex(many.data(),many.size(),&r)==2&&r.count==100001); Awl_lex_free(&r);
        std::mt19937 rng(606);
        for(int n=0;n<10000;++n) {
            std::string source;
            for(unsigned i=0,limit=rng()%256;i<limit;++i) source.push_back(static_cast<char>(rng()%256));
            const auto status=Awl_lex(source.data(),source.size(),&r);
            require(status==0||status==1||status==4||status==6);
            require(r.count<=100001);
            for(uint32_t i=0;i<r.count;++i) require(r.tokens[i].start<r.tokens[i].end&&r.tokens[i].end<=source.size());
            Awl_lex_free(&r);
            const auto project=Awl_lex(source.data(),source.size(),&r);
            require(project==0||project==1||project==4||project==6);
            require(r.count<=100001);
            for(uint32_t i=0;i<r.count;++i) require(r.tokens[i].start<r.tokens[i].end&&r.tokens[i].end<=source.size());
            Awl_lex_free(&r);
        }
        std::cout<<"native lexer: boundaries, UTF-8, ownership, cap, 10000 raw-byte inputs Aesop scanner passed\n";
    } catch(const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
