const std::vector<std::string> generic_elements={"i8","i16","i32","i64","u8","u16","u32","u64","bool","f64","string"};
const std::unordered_set<std::string> generic_methods={"new","valid","free","length","capacity","reserve","push","pop","get","set","clear","insert","remove","slice","swap","truncate","view"};
bool generic_element(const std::string &s) {return std::find(generic_elements.begin(),generic_elements.end(),s)!=generic_elements.end();}
std::optional<std::string> generic_type(const std::string &s) {
    if(s.size()<9||!s.starts_with("vector<")||s.back()!='>') return {};
    const auto element=s.substr(7,s.size()-8);if(!generic_element(element)) return {};return element;
}
bool generic_call(const std::string &s) {return s.starts_with("vector_")&&generic_methods.contains(s.substr(7));}
bool generic_specialization(const std::string &s) {
    if(!s.starts_with("vector_")) return false;
    const auto split=s.rfind('_');return split>7&&generic_methods.contains(s.substr(7,split-7))&&generic_element(s.substr(split+1));
}
bool generic_free(const std::string &s) {return s=="vector_free"||(s.starts_with("vector_free_")&&generic_element(s.substr(12)));}
bool generic_borrow(const std::string &s) {return (generic_call(s)&&s!="vector_free"&&s!="vector_new")||(generic_specialization(s)&&!s.starts_with("vector_free_")&&!s.starts_with("vector_new_"));}
int generic_value_argument(const std::string &s) {return s=="vector_push"?1:(s=="vector_set"||s=="vector_insert")?2:-1;}
bool generic_fresh(const std::string &name,const std::string &ty) {
    const auto e=generic_type(ty);return e&&(name=="vector_slice"||name=="vector_new_"+*e||name=="vector_slice_"+*e);
}

std::optional<std::string> view_type(const std::string &s) {
    if(s.size()<7||!s.starts_with("view<")||s.back()!='>') return {};
    const auto element=s.substr(5,s.size()-6);if(!generic_element(element)) return {};return element;
}
const std::unordered_set<std::string> view_methods={"valid","length","get","slice"};
bool view_call(const std::string &s) {return s.starts_with("view_")&&view_methods.contains(s.substr(5));}
bool view_specialization(const std::string &s) {
    if(!s.starts_with("view_")) return false;
    const auto split=s.rfind('_');return split>5&&view_methods.contains(s.substr(5,split-5))&&generic_element(s.substr(split+1));
}
