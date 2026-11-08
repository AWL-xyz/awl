// Compiler-side UTF-8/string literal policy. No locale/normalization/grapheme
// assumptions. Raw UTF-8 source is validated by the selected native scanner.
bool text_scalars(std::string_view s,size_t &count) {
    count=0;
    for(size_t i=0;i<s.size();) {
        const auto c=static_cast<unsigned char>(s[i]);size_t width=1;uint32_t cp=c;
        if(c>=0x80) {
            if(c>=0xc2&&c<=0xdf) {width=2;cp=c&31;}
            else if(c>=0xe0&&c<=0xef) {width=3;cp=c&15;}
            else if(c>=0xf0&&c<=0xf4) {width=4;cp=c&7;}
            else return false;
            if(width>s.size()-i) return false;
            for(size_t j=1;j<width;++j) {const auto b=static_cast<unsigned char>(s[i+j]);if((b&0xc0)!=0x80) return false;cp=(cp<<6)|(b&63);}
            if((width==3&&cp<0x800)||(width==4&&cp<0x10000)||cp>0x10ffff||(cp>=0xd800&&cp<=0xdfff)) return false;
        }
        i+=width;++count;
    }
    return true;
}
void text_append(std::string &out,uint32_t cp) {
    if(cp<0x80) out+=static_cast<char>(cp);
    else if(cp<0x800) {out+=static_cast<char>(0xc0|(cp>>6));out+=static_cast<char>(0x80|(cp&63));}
    else if(cp<0x10000) {out+=static_cast<char>(0xe0|(cp>>12));out+=static_cast<char>(0x80|((cp>>6)&63));out+=static_cast<char>(0x80|(cp&63));}
    else {out+=static_cast<char>(0xf0|(cp>>18));out+=static_cast<char>(0x80|((cp>>12)&63));out+=static_cast<char>(0x80|((cp>>6)&63));out+=static_cast<char>(0x80|(cp&63));}
}
std::string text_literal(const std::string &source,uint32_t token) {
    auto fail=[&](const std::string &message)->void {throw Failure{{"E102",message,token}};};
    std::string out;
    if(source.size()<2||source.front()!='"'||source.back()!='"') fail("malformed string literal");
    for(size_t i=1;i+1<source.size();++i) {
        if(source[i]!='\\') out+=source[i];
        else {
            if(++i+1>=source.size()) fail("incomplete string escape");
            switch(source[i]) {
                case 'n':out+='\n';break;
                case 'r':out+='\r';break;
                case 't':out+='\t';break;
                case 'b':out+='\b';break;
                case 'f':out+='\f';break;
                case '0':out+='\0';break;
                case '\\':out+='\\';break;
                case '"':out+='"';break;
                case 'u': {
                    if(++i+1>=source.size()||source[i]!='{') fail("Unicode escape must use \\u{hex}");
                    uint32_t cp=0;unsigned digits=0;
                    while(++i+1<source.size()&&source[i]!='}') {
                        const char c=source[i];unsigned value=16;
                        if(c>='0'&&c<='9') value=static_cast<unsigned>(c-'0');
                        else if(c>='a'&&c<='f') value=static_cast<unsigned>(c-'a'+10);
                        else if(c>='A'&&c<='F') value=static_cast<unsigned>(c-'A'+10);
                        if(value==16||++digits>6) fail("invalid Unicode escape digits");
                        cp=cp*16+value;
                    }
                    if(i+1>=source.size()||source[i]!='}'||!digits||cp>0x10ffff||(cp>=0xd800&&cp<=0xdfff)) fail("Unicode escape is not a scalar value");
                    text_append(out,cp);break;
                }
                default:fail("unknown string escape");
            }
        }
        if(out.size()>65536) throw Failure{{"E103","decoded string literal exceeds 65536 bytes",token}};
    }
    size_t count=0;if(!text_scalars(out,count)) fail("string literal is not valid UTF-8");
    return out;
}
