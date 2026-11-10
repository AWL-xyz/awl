// Canonical bounded array type codec shared as syntax, not semantic proof.
struct ArrayType {std::string element;uint32_t count;};
std::optional<ArrayType> array_type(const std::string &ty) {
    if(ty.size()<5||ty.front()!='['||ty.back()!=']'||ty.size()>128) return {};
    const auto semi=ty.rfind(';');if(semi==std::string::npos||semi<2||semi+1>=ty.size()-1) return {};
    uint32_t count=0;
    for(size_t i=semi+1;i+1<ty.size();++i) {if(ty[i]<'0'||ty[i]>'9'||count>1024) return {};count=count*10+static_cast<unsigned>(ty[i]-'0');}
    if(!count||count>1024||ty.substr(semi+1,ty.size()-semi-2)!=std::to_string(count)) return {};
    return ArrayType{ty.substr(1,semi-1),count};
}
std::string array_name(const std::string &element,size_t count) {return "["+element+";"+std::to_string(count)+"]";}
