// Next-dialect numeric schema. Not an FFI and not enabled in legacy mode.
struct MathSignature {std::vector<std::string> parameters;std::string result;};
const std::unordered_map<std::string,MathSignature> math_signatures={
    {"sin",{{"f64"},"f64"}},{"cos",{{"f64"},"f64"}},
    {"sqrt",{{"f64"},"f64"}},{"atan2",{{"f64","f64"},"f64"}}
};
bool finite_decimal(const std::string &s) {
    if(s.empty()||s.size()>257) return false;
    const auto dot=s.find('.');
    const size_t start=s[0]=='-'?1:0;
    if(dot==std::string::npos||dot==start||dot+1==s.size()||s.find('.',dot+1)!=std::string::npos) return false;
    for(size_t i=0;i<s.size();++i) if(i!=dot&&!(i==0&&start)&&(s[i]<'0'||s[i]>'9')) return false;
    double value=0;const auto converted=std::from_chars(s.data(),s.data()+s.size(),value,std::chars_format::fixed);
    return converted.ec==std::errc{}&&converted.ptr==s.data()+s.size()&&std::isfinite(value);
}
