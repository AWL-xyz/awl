#include "klex.h"
#include <algorithm>
#include <chrono>
#include <memory>
#include <string_view>
#include <vector>

namespace {
constexpr size_t max_source=1048576;
constexpr uint32_t max_tokens=100000;
constexpr uint32_t number=1, identifier=2;
using Tokens=std::vector<AwlLexToken>;
bool digit(unsigned char c) { return c>='0' && c<='9'; }
bool letter(unsigned char c) { return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||c=='_'; }
/* Strict UTF-8 including rejection of overlong encodings, surrogates, >U+10FFFF. */
size_t utf8_width(std::string_view s,size_t i) {
    const auto c=static_cast<unsigned char>(s[i]);
    if(c<0x80) return 1;
    size_t width=0; uint32_t cp=0;
    if(c>=0xc2&&c<=0xdf) { width=2; cp=c&31; }
    else if(c>=0xe0&&c<=0xef) { width=3; cp=c&15; }
    else if(c>=0xf0&&c<=0xf4) { width=4; cp=c&7; }
    else return 0;
    if(width>s.size()-i) return 0;
    for(size_t n=1;n<width;++n) {
        const auto next=static_cast<unsigned char>(s[i+n]);
        if((next&0xc0)!=0x80) return 0;
        cp=(cp<<6)|(next&63);
    }
    if((width==3&&cp<0x800)||(width==4&&cp<0x10000)||
       (cp>=0xd800&&cp<=0xdfff)||cp>0x10ffff) return 0;
    return width;
}
}
extern "C" {
uint32_t Awl_lex_abi_version(void) { return 2; }
size_t Awl_lex_token_size(void) { return sizeof(AwlLexToken); }
size_t Awl_lex_result_size(void) { return sizeof(AwlLexResult); }
void Awl_lex_free(AwlLexResult *out) {
    if(!out) return;
    delete static_cast<Tokens*>(out->owner); *out={};
}
static int scan(const char *input,size_t size,AwlLexResult *out) {
    if(!out) return 5;
    *out={}; out->line=out->column=1;
    if(size>max_source) return 3;
    if(!input&&size) return 5;
    const std::string_view source(input?input:"",size);
    try {
        /* Encoding errors precede lexical errors, matching file decoding. */
        for(size_t i=0;i<size;) { const auto n=utf8_width(source,i); if(!n) return 4; i+=n; }
        auto tokens=std::make_unique<Tokens>();
        tokens->reserve(std::min(size/3+1,static_cast<size_t>(max_tokens+1)));
        size_t i=0; uint32_t cp=0,line=1,column=1; int status=0;
        while(i<size) {
            const auto c=static_cast<unsigned char>(source[i]);
            if(c==' '||c=='\t'||c=='\r') { ++i; ++cp; ++column; continue; }
            if(c=='\n') { ++i; ++cp; ++line; column=1; continue; }
            if(c=='-'&&i+1<size&&source[i+1]=='-') {
                while(i<size&&source[i]!='\n') { i+=utf8_width(source,i); ++cp; ++column; }
                continue;
            }
            const size_t start=i; const auto start_cp=cp, start_column=column; uint32_t flags=0;
            if(c=='"') {
                flags=4; ++i; bool closed=false;
                while(i<size) {
                    if(source[i]=='"') {++i;closed=true;break;}
                    if(source[i]=='\n'||source[i]=='\r') break;
                    if(source[i]=='\\') {++i;if(i==size||source[i]=='\n'||source[i]=='\r') break;}
                    i+=utf8_width(source,i);
                }
                if(!closed) {status=6;break;}
            } else if(digit(c)) {
                flags=number;
                while(i<size&&digit(static_cast<unsigned char>(source[i]))) ++i;
                if(i<size&&(source[i]=='i'||source[i]=='u')) {
                    const auto suffix=source.substr(i+1);
                    size_t width=0;
                    if(suffix.starts_with("8")) width=1;
                    else if(suffix.starts_with("16")||suffix.starts_with("32")||suffix.starts_with("64")) width=2;
                    if(width) i+=1+width;
                }
            } else if(letter(c)) {
                flags=identifier;
                while(i<size&&(letter(static_cast<unsigned char>(source[i]))||digit(static_cast<unsigned char>(source[i])))) ++i;
            } else {
                const auto rest=source.substr(i);
                if((rest.starts_with("..")||rest.starts_with("::"))||rest.starts_with("->")||rest.starts_with("==")||rest.starts_with("!=")||
                   rest.starts_with("<=")||rest.starts_with(">=")) i+=2;
                else if((c=='['||c==']'||c=='@'||c=='{'||c=='}')) ++i;
                else if(std::string_view("+*/%<>=():,;.-").find(static_cast<char>(c))!=std::string_view::npos) ++i;
                else { status=1; break; }
            }
            uint32_t width=0;
            if(flags==4) {for(size_t p=start;p<i;p+=utf8_width(source,p)) ++width;}
            else width=static_cast<uint32_t>(i-start);
            cp+=width;column+=width;
            tokens->push_back({start_cp,cp,line,start_column,flags});
            /* One extra token is retained so the adapter can preserve exact
               diagnostic priority among boundary, length and token limits. */
            if(tokens->size()>max_tokens) { status=2; break; }
        }
        out->position=cp; out->line=line; out->column=column;
        out->count=static_cast<uint32_t>(tokens->size()); out->tokens=tokens->data();
        out->owner=tokens.release(); return status;
    } catch(...) { *out={}; return 5; }
}
int Awl_lex(const char *input,size_t size,AwlLexResult *out) {return scan(input,size,out);}
int Awl_lex_benchmark(const char *source,size_t size,uint32_t repeat,double *seconds,uint64_t *count) {
    if(!seconds||!count||!repeat||repeat>100000) return 5;
    *seconds=0; *count=0;
    const auto begin=std::chrono::steady_clock::now();
    for(uint32_t i=0;i<repeat;++i) {
        AwlLexResult result{}; const int status=Awl_lex(source,size,&result);
        *count+=result.count; Awl_lex_free(&result);
        if(status) return status;
    }
    *seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
    return 0;
}
}
