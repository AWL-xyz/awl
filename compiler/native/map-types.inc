// map<K,V> and set<T> type surface shared by parser, checker, verifier, emitter.
bool map_key_element(const std::string &s) {return generic_element(s)&&s!="f64";}
std::optional<std::pair<std::string,std::string>> map_type(const std::string &s) {
    if(s.size()<10||!s.starts_with("map<")||s.back()!='>') return {};
    const auto inner=s.substr(4,s.size()-5);
    if(inner.find('<')!=std::string::npos) return {};
    const auto comma=inner.find(',');
    if(comma==std::string::npos) return {};
    const auto key=inner.substr(0,comma),value=inner.substr(comma+1);
    if(!map_key_element(key)||!generic_element(value)) return {};
    return std::make_pair(key,value);
}
std::optional<std::string> set_type(const std::string &s) {
    if(s.size()<7||!s.starts_with("set<")||s.back()!='>') return {};
    const auto element=s.substr(4,s.size()-5);
    if(element.find('<')!=std::string::npos||!map_key_element(element)) return {};
    return element;
}
std::string map_name(const std::string &key,const std::string &value) {return "map<"+key+","+value+">";}
std::string set_name(const std::string &element) {return "set<"+element+">";}
const std::unordered_set<std::string> map_methods={"new","valid","free","length","clear","set","get","has","remove","keys","values"};
const std::unordered_set<std::string> set_methods={"new","valid","free","length","clear","add","has","remove","values"};
bool map_call(const std::string &s) {return s.starts_with("map_")&&map_methods.contains(s.substr(4));}
bool set_call(const std::string &s) {return s.starts_with("set_")&&set_methods.contains(s.substr(4));}
struct MapSpecialization {std::string method,key,value;};
struct SetSpecialization {std::string method,element;};
std::optional<MapSpecialization> map_specialization_of(const std::string &s) {
    if(!s.starts_with("map_")) return {};
    for(const auto &method:map_methods) {
        if(method=="new") continue;
        const auto head="map_"+method+"_";
        if(!s.starts_with(head)) continue;
        const auto rest=s.substr(head.size());
        const auto middle=rest.find('_');
        if(middle==std::string::npos) return {};
        const auto key=rest.substr(0,middle),value=rest.substr(middle+1);
        if(!map_type(map_name(key,value))) return {};
        return MapSpecialization{method,key,value};
    }
    return {};
}
std::optional<SetSpecialization> set_specialization_of(const std::string &s) {
    if(!s.starts_with("set_")) return {};
    for(const auto &method:set_methods) {
        if(method=="new") continue;
        const auto head="set_"+method+"_";
        if(!s.starts_with(head)) continue;
        const auto element=s.substr(head.size());
        if(!set_type(set_name(element))) return {};
        return SetSpecialization{method,element};
    }
    return {};
}
bool map_specialization(const std::string &s) {return bool(map_specialization_of(s));}
bool set_specialization(const std::string &s) {return bool(set_specialization_of(s));}
std::optional<std::string> map_container_type(const std::string &s) {
    if(auto m=map_specialization_of(s)) return map_name(m->key,m->value);
    if(auto set=set_specialization_of(s)) return set_name(set->element);
    return {};
}
std::optional<std::pair<std::vector<std::string>,std::string>> map_signature(const std::string &method,const std::string &key,const std::string &value) {
    if(!map_methods.contains(method)||method=="new") return {};
    const std::vector<std::string> container{"__container__"};
    if(method=="set") return std::make_pair(std::vector<std::string>{"__container__",key,value},std::string("unit"));
    if(method=="get") return std::make_pair(std::vector<std::string>{"__container__",key},value);
    if(method=="has"||method=="remove") return std::make_pair(std::vector<std::string>{"__container__",key},std::string("bool"));
    if(method=="length") return std::make_pair(container,std::string("i64"));
    if(method=="valid") return std::make_pair(container,std::string("bool"));
    if(method=="clear"||method=="free") return std::make_pair(container,std::string("unit"));
    if(method=="keys") return std::make_pair(container,"vector<"+key+">");
    return std::make_pair(container,"vector<"+value+">");
}
std::optional<std::pair<std::vector<std::string>,std::string>> set_signature(const std::string &method,const std::string &element) {
    if(!set_methods.contains(method)||method=="new") return {};
    const std::vector<std::string> container{"__container__"};
    if(method=="add"||method=="has"||method=="remove") return std::make_pair(std::vector<std::string>{"__container__",element},std::string("bool"));
    if(method=="length") return std::make_pair(container,std::string("i64"));
    if(method=="valid") return std::make_pair(container,std::string("bool"));
    if(method=="clear"||method=="free") return std::make_pair(container,std::string("unit"));
    return std::make_pair(container,"vector<"+element+">");
}
// Resolves a bare map_*/set_* call against its container argument type.
std::optional<std::pair<std::string,std::pair<std::vector<std::string>,std::string>>> map_resolve(const std::string &name,const std::string &container) {
    const auto method=name.substr(4);
    if(name.starts_with("map_")) {
        const auto types=map_type(container);if(!types) return {};
        const auto signature=map_signature(method,types->first,types->second);if(!signature) return {};
        return std::make_pair("map_"+method+"_"+types->first+"_"+types->second,*signature);
    }
    if(name.starts_with("set_")) {
        const auto element=set_type(container);if(!element) return {};
        const auto signature=set_signature(method,*element);if(!signature) return {};
        return std::make_pair("set_"+method+"_"+*element,*signature);
    }
    return {};
}
bool container_call(const std::string &s) {return map_call(s)||set_call(s)||map_specialization(s)||set_specialization(s);}
bool container_borrow(const std::string &s) {return container_call(s)&&s.find("free")==std::string::npos;}
std::optional<std::string> new_container_type(const std::string &s) {
    const bool map_like=s.starts_with("map_new_");
    if(!map_like&&!s.starts_with("set_new_")) return {};
    const auto rest=s.substr(8);
    if(map_like) {
        const auto split=rest.find('_');
        if(split==std::string::npos) return {};
        const auto ty=map_name(rest.substr(0,split),rest.substr(split+1));
        if(!map_type(ty)) return {};
        return ty;
    }
    const auto ty=set_name(rest);
    if(!set_type(ty)) return {};
    return ty;
}
bool container_fresh(const std::string &name,const std::string &ty) {
    const auto created=new_container_type(name);
    return created&&*created==ty;
}
std::optional<std::pair<std::vector<std::string>,std::string>> container_signature(const std::string &name) {
    if(auto m=map_specialization_of(name)) return map_signature(m->method,m->key,m->value);
    if(auto s=set_specialization_of(name)) return set_signature(s->method,s->element);
    return {};
}
