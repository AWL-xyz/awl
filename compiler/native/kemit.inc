// Transitional native C11 backend. Verified arena in, deterministic C source out.
// All argument evaluation is explicitly sequenced; no host tools are invoked.
#include "kruntime.inc"
#include "kstrings.inc"
#include "kbuilders.inc"
#include "kvectors.inc"
#include "kgeneric.inc"
#include "karguments.inc"
#include "kfiles.inc"
#include "kstreams.inc"
#include "ktcp.inc"
#include "kplatform.inc"
#include "kwallclock.inc"
#include "kprocess.inc"
#include "kmaps.inc"
class CEmitter {
    const Unit &u;
    std::unordered_map<std::string,Id> aggregates;
    std::unordered_set<std::string> helpers,ordered,generic_used,containers_used;
    std::vector<std::string> order;
    std::unordered_map<std::string,std::string> arrays;
    std::string body;
    std::vector<std::vector<std::string>> cleanups;
    std::vector<size_t> loop_scopes;
    std::unordered_set<std::string> pointers;
    uint32_t serial=0,depth=0;
    bool process_used=false,tcp_used=false,streams_used=false,files_used=false,arguments_used=false,vectors_used=false,platform_used=false,wall_clock_used=false,strings_used=false,builders_used=false,arrays_used=false;
    const Node &n(Id id) const {return u.arena.at(id);}
    const List &list(Id id) const {return n(id).children;}
    std::string ct(const std::string &ty) const {
        if(arrays.contains(ty)) return arrays.at(ty);
        if(u.aesop_syntax&&ty=="f64") return "double";
        if(u.aesop_syntax&&generic_type(ty)) return "KGenericVector";
        if(u.aesop_syntax&&(map_type(ty)||set_type(ty))) return "KMap";
        if(u.aesop_syntax&&view_type(ty)) return "KGenericView";
        if(ty=="bool") return "bool";
        if(ty=="string") return "KString";
        if(ty=="spool") return "KSpool";
        if(u.project_syntax&&ty=="int_vector") return "KIntVector";
        if(ty=="unit") return "void";
        if(integers.contains(ty)) return std::string(ty[0]=='i'?"int":"uint")+ty.substr(1)+"_t";
        return "k_s_"+ty;
    }
    std::string release_name(const std::string &ty,const std::string &op) const {
        if(auto e=generic_type(ty)) return "k_vector_"+op+"_"+*e;
        if(auto m=map_type(ty)) return "k_map_"+op+"_"+m->first+"_"+m->second;
        if(auto s=set_type(ty)) return "k_set_"+op+"_"+*s;
        return "k_"+ty+"_"+op;
    }
    bool owner_field(const std::string &t) const {return generic_type(t)||map_type(t)||set_type(t)||t=="spool"||resource_struct(t);}
    bool resource_struct(const std::string &ty,uint32_t depth=0) const {
        if(depth>64||!aggregates.contains(ty)||n(aggregates.at(ty)).kind!="struct") return false;
        for(auto f:n(aggregates.at(ty)).children) if(owner_field(n(f).second)) return true;
        return false;
    }
    // generated valid/free for resource structs, valid means every owner field is still live
    std::string resource_struct_functions(const std::string &name) const {
        const auto &d=n(aggregates.at(name));std::string valid="static bool k_"+name+"_valid(k_s_"+name+" v) { return 1",release="static void k_"+name+"_free(k_s_"+name+" v) {";
        for(auto f:d.children) {const auto &t=n(f).second;if(!owner_field(t)) continue;const auto field="v.k_f_"+n(f).value;
            valid+=" && "+release_name(t,"valid")+"("+field+")";release+=" if ("+release_name(t,"valid")+"("+field+")) "+release_name(t,"free")+"("+field+");";}
        return valid+"; }\n"+release+" }\n";
    }
    std::string generic_wrappers() const {
        std::string out;
        for(size_t index=0;index<generic_elements.size();++index) {
            const auto &e=generic_elements[index];if(!generic_used.contains(e)) continue;
            const auto tag=std::to_string(index+1),t=ct(e);
            for(const std::string m:{"new","valid","free","length","capacity","reserve","push","pop","get","set","clear","insert","remove","slice","swap","truncate","view"}) {
                const auto name="vector_"+m+"_"+e;const auto &sig=platform_signatures.at(name);
                out+="static "+ct(sig.result)+" k_"+name+"(";
                for(size_t i=0;i<sig.parameters.size();++i) {if(i) out+=", ";out+=ct(sig.parameters[i])+" a"+std::to_string(i);}
                out+=") {";
                if(m=="new") out+="return k_generic_new("+tag+",sizeof("+t+"),a0);";
                else if(m=="valid") out+="return k_generic_find(a0,"+tag+")!=NULL;";
                else if(m=="free") out+="k_generic_free(a0,"+tag+");";
                else if(m=="length"||m=="capacity") out+="return (int64_t)k_generic_require(a0,"+tag+")->"+m+";";
                else if(m=="clear") out+="k_generic_clear(a0,"+tag+");";
                else if(m=="reserve") out+="return k_generic_reserve(a0,"+tag+",a1);";
                else if(m=="swap") out+="k_generic_swap(a0,"+tag+",a1,a2);";
                else if(m=="truncate") out+="return k_generic_truncate(a0,"+tag+",a1);";
                else if(m=="push") out+="return k_generic_push(a0,"+tag+",&a1);";
                else if(m=="get"||m=="set") {
                    out+="KGenericSlot *s=k_generic_require(a0,"+tag+");if(s->width!=sizeof("+t+")) k_generic_trap();const size_t i=k_generic_index(s,a1,false);";
                    if(m=="get") out+=t+" value;memcpy(&value,s->data+i*sizeof("+t+"),sizeof("+t+"));return value;";
                    else out+="memcpy(s->data+i*sizeof("+t+"),&a2,sizeof("+t+"));";
                }
                else if(m=="insert") out+="return k_generic_insert(a0,"+tag+",a1,&a2);";
                else if(m=="view") out+="return k_generic_view(a0,"+tag+",a1,a2);";
                else if(m=="slice") out+="return k_generic_slice(a0,"+tag+",a1,a2);";
                else out+=t+" value; k_generic_"+m+"(a0,"+tag+(m=="pop"?",&value);":",a1,&value);")+"return value;";
                out+="}\n";
            }
            for(const std::string m:{"valid","length","get","slice"}) {
                const auto name="view_"+m+"_"+e;const auto &sig=platform_signatures.at(name);
                out+="static "+ct(sig.result)+" k_"+name+"(";
                for(size_t i=0;i<sig.parameters.size();++i) {if(i) out+=", ";out+=ct(sig.parameters[i])+" a"+std::to_string(i);}
                out+=") {";
                if(m=="valid") out+="return k_view_find(a0,"+tag+")!=NULL;";
                else if(m=="length") out+="k_view_require(a0,"+tag+");return (int64_t)a0.length;";
                else if(m=="slice") out+="return k_view_slice(a0,"+tag+",a1,a2);";
                else out+=t+" value;k_view_get(a0,"+tag+",a1,&value,sizeof("+t+"));return value;";
                out+="}\n";
            }
        }
        return out;
    }
    std::string container_wrappers() const {
        std::string out;
        std::vector<std::string> sorted(containers_used.begin(),containers_used.end());std::sort(sorted.begin(),sorted.end());
        unsigned tag=100;
        for(const auto &ty:sorted) {
            const auto name="k_map_kind_"+std::to_string(tag++);
            const auto kind=std::to_string(tag-1);
            auto collect_vector=[&](const std::string &method,const std::string &element) {
                const auto vector_tag=std::to_string(static_cast<size_t>(std::find(generic_elements.begin(),generic_elements.end(),element)-generic_elements.begin())+1);
                const auto outputs=method.starts_with("map_values_")?"NULL,(unsigned char *)&item":"(unsigned char *)&item,NULL";
                out+="static KGenericVector k_"+method+"(KMap a0) {int64_t cursor=0; "+ct(element)+" item; const int64_t count=k_map_length(a0,"+kind+"); KGenericVector out=k_generic_new("+vector_tag+",sizeof("+ct(element)+"),count>0?count:1); while(k_map_iter_next(a0,"+kind+",&cursor,"+outputs+")) k_generic_push(out,"+vector_tag+",&item); return out;}\n";
            };
            if(auto m=map_type(ty)) {
                const auto &key=m->first,&value=m->second;
                const auto key_text=key=="string",value_text=value=="string";
                const std::string prefix="k_map_";
                out+="static const unsigned "+name+" = "+kind+";\n";
                out+="static KMap "+prefix+"new_"+key+"_"+value+"(int64_t a0) {return k_map_new("+kind+",sizeof("+ct(key)+"),sizeof("+ct(value)+"),"+std::to_string(key_text?1:0)+","+std::to_string(value_text?1:0)+",a0);}\n";
                out+="static bool "+prefix+"valid_"+key+"_"+value+"(KMap a0) {return k_map_valid(a0,"+kind+");}\n";
                out+="static void "+prefix+"free_"+key+"_"+value+"(KMap a0) {k_map_free(a0,"+kind+");}\n";
                out+="static int64_t "+prefix+"length_"+key+"_"+value+"(KMap a0) {return k_map_length(a0,"+kind+");}\n";
                out+="static void "+prefix+"clear_"+key+"_"+value+"(KMap a0) {k_map_clear(a0,"+kind+");}\n";
                out+="static void "+prefix+"set_"+key+"_"+value+"(KMap a0, "+ct(key)+" a1, "+ct(value)+" a2) {k_map_set(a0,"+kind+",(const unsigned char *)&a1,(const unsigned char *)&a2);}\n";
                out+="static "+ct(value)+" "+prefix+"get_"+key+"_"+value+"(KMap a0, "+ct(key)+" a1) {"+ct(value)+" value; k_map_get(a0,"+kind+",(const unsigned char *)&a1,(unsigned char *)&value); return value;}\n";
                out+="static bool "+prefix+"has_"+key+"_"+value+"(KMap a0, "+ct(key)+" a1) {return k_map_has(a0,"+kind+",(const unsigned char *)&a1);}\n";
                out+="static bool "+prefix+"remove_"+key+"_"+value+"(KMap a0, "+ct(key)+" a1) {return k_map_remove(a0,"+kind+",(const unsigned char *)&a1);}\n";
                out+="static bool "+prefix+"iter_"+key+"_"+value+"(KMap a0, int64_t *cursor, "+ct(key)+" *key, "+ct(value)+" *value) {return k_map_iter_next(a0,"+kind+",cursor,(unsigned char *)key,(unsigned char *)value);}\n";
                collect_vector("map_keys_"+key+"_"+value,key);
                collect_vector("map_values_"+key+"_"+value,value);
            } else {
                const auto element=*set_type(ty);const auto element_text=element=="string";
                const std::string prefix="k_set_";
                out+="static const unsigned "+name+" = "+kind+";\n";
                out+="static KMap "+prefix+"new_"+element+"(int64_t a0) {return k_map_new("+kind+",sizeof("+ct(element)+"),0,"+std::to_string(element_text?1:0)+",0,a0);}\n";
                out+="static bool "+prefix+"valid_"+element+"(KMap a0) {return k_map_valid(a0,"+kind+");}\n";
                out+="static void "+prefix+"free_"+element+"(KMap a0) {k_map_free(a0,"+kind+");}\n";
                out+="static int64_t "+prefix+"length_"+element+"(KMap a0) {return k_map_length(a0,"+kind+");}\n";
                out+="static void "+prefix+"clear_"+element+"(KMap a0) {k_map_clear(a0,"+kind+");}\n";
                out+="static bool "+prefix+"add_"+element+"(KMap a0, "+ct(element)+" a1) {const bool fresh=!k_map_has(a0,"+kind+",(const unsigned char *)&a1); k_map_set(a0,"+kind+",(const unsigned char *)&a1,NULL); return fresh;}\n";
                out+="static bool "+prefix+"has_"+element+"(KMap a0, "+ct(element)+" a1) {return k_map_has(a0,"+kind+",(const unsigned char *)&a1);}\n";
                out+="static bool "+prefix+"remove_"+element+"(KMap a0, "+ct(element)+" a1) {return k_map_remove(a0,"+kind+",(const unsigned char *)&a1);}\n";
                out+="static bool "+prefix+"iter_"+element+"(KMap a0, int64_t *cursor, "+ct(element)+" *element) {return k_map_iter_next(a0,"+kind+",cursor,(unsigned char *)element,NULL);}\n";
                collect_vector("set_values_"+element,element);
            }
        }
        return out;
    }
    void line(const std::string &text) {
        if(body.size()+4*depth+text.size()+1>67108864) throw Failure{{"E501","C emission budget exceeded",UINT32_MAX}};
        body+=std::string(4*depth,' ')+text+'\n';
    }
    static std::string join(const std::vector<std::string> &args) {
        std::string out;for(size_t i=0;i<args.size();++i) {if(i) out+=", ";out+=args[i];}return out;
    }
    std::string helper(const std::string &name,const std::vector<std::string> &args) {helpers.insert(name);return name+"("+join(args)+")";}
    std::string struct_equal(const std::string &a,const std::string &b,const std::string &ty) {
        std::string out="1";
        for(auto f:n(aggregates.at(ty)).children) {
            const auto &t=n(f).second;const auto fa=a+".k_f_"+n(f).value,fb=b+".k_f_"+n(f).value;
            out+=" && "+(t=="string"?helper("k_string_equal",{fa,fb}):aggregates.contains(t)?struct_equal(fa,fb,t):"("+fa+" == "+fb+")");
        }
        return "("+out+")";
    }
    std::string temp(const std::string &ty,const std::string &value) {
        if(ty=="unit") {line(value+";");return "";}
        const auto name="k_t"+std::to_string(++serial);line(ct(ty)+" "+name+" = "+value+";");return name;
    }
    std::pair<size_t,Id> variant(const std::string &owner,const std::string &name) const {
        const auto &variants=n(aggregates.at(owner)).children;
        for(size_t i=0;i<variants.size();++i) if(n(variants[i]).value==name) return {i,variants[i]};
        throw std::runtime_error("verified variant missing");
    }
    std::vector<std::string> arguments(const Node &node) {
        std::vector<std::string> out;
        for(auto id:node.children) out.push_back(u.mutable_arguments.contains(id)?"(&"+place(id)+")":expr(id));
        return out;
    }
    std::string initializers(const List &fields,const std::vector<std::string> &args) const {
        std::vector<std::string> out;for(size_t i=0;i<fields.size();++i) out.push_back(".k_f_"+n(fields[i]).value+" = "+args[i]);return join(out);
    }
    std::string expr(Id id) {
        const auto &node=n(id);const auto &k=node.kind;
        if(k=="float") return "((double)("+node.value+"))";
        if(k=="int"||k=="uint") {
            const auto value=node.value=="-9223372036854775808"?std::string("INT64_MIN"):std::string(k=="int"?"INT64_C(":"UINT64_C(")+node.value+")";
            return "(("+ct(node.type)+")("+value+"))";
        }
        if(k=="move") {
            const auto captured=expr(node.children[0]);
            line(n(node.children[0]).symbol+" = ("+ct(node.type)+"){0};");return captured;
        }
        if(k=="array_repeat") {
            const auto value=expr(node.children[0]);
            const auto name="k_t"+std::to_string(++serial),index="k_i"+std::to_string(++serial);
            line(ct(node.type)+" "+name+";");
            line("for (uint32_t "+index+" = 0; "+index+" < "+std::to_string(array_type(node.type)->count)+"; ++"+index+") {");
            ++depth;line(name+".data["+index+"] = "+value+";");--depth;line("}");return name;
        }
        if(k=="array") {const auto args=arguments(node);return temp(node.type,"("+ct(node.type)+"){.data = {"+join(args)+"}}");}
        if(k=="index") {
            const auto base=expr(node.children[0]);const auto index=expr(node.children[1]);const auto a=array_type(n(node.children[0]).type);
            return temp(node.type,base+".data[k_array_index("+index+","+std::to_string(a->count)+")]");
        }
        if(k=="string") {
            const char hex[]="0123456789abcdef";std::string bytes="\"";
            for(unsigned char c:node.value) {bytes+="\\x";bytes+=hex[c>>4];bytes+=hex[c&15];}
            bytes+='"';size_t count=0;
            if(!text_scalars(node.value,count)) throw std::runtime_error("verified string invalid");
            return "((KString){(const unsigned char *)"+bytes+","+std::to_string(node.value.size())+","+std::to_string(count)+"})";
        }
        if(k=="bool") return node.value;
        if(k=="name"||k=="global_ref") return temp(node.type,pointers.contains(node.symbol)?"(*"+node.symbol+")":node.symbol);
        if(k=="field") {const auto base=expr(node.children[0]);return temp(node.type,base+".k_f_"+node.value);}
        if(k=="convert") {const auto a=expr(node.children[0]);if(node.type=="f64") return temp("f64","((double)("+a+"))");return temp(node.type,helper("k_convert_"+n(node.children[0]).type+"_"+node.type,{a}));}
        if(k=="unary") {const auto a=expr(node.children[0]);return temp(node.type,node.value=="not"?"(!"+a+")":node.type=="f64"?"(-"+a+")":helper("k_"+node.type+"_sub",{"0",a}));}
        if(k=="binary") {
            const auto a=expr(node.children[0]);const auto &op=node.value;
            if(op=="and"||op=="or") {
                const auto t=temp("bool",a);line("if ("+std::string(op=="or"?"!":"")+t+") {");++depth;
                const auto b=expr(node.children[1]);line(t+" = "+b+";");--depth;line("}");return t;
            }
            const auto b=expr(node.children[1]);
            if(aggregates.contains(n(node.children[0]).type)) {
                const auto equal=struct_equal(a,b,n(node.children[0]).type);
                return temp("bool",op=="!="?"(!"+equal+")":equal);
            }
            if(n(node.children[0]).type=="string") {
                if(op=="+") return temp("string",helper("k_string_concat",{a,b}));
                const auto equal=helper("k_string_equal",{a,b});
                return temp("bool",op=="!="?"(!"+equal+")":equal);
            }
            if(n(node.children[0]).type=="f64") return temp(node.type,"("+a+" "+op+" "+b+")");
            static const std::unordered_map<std::string,std::string> operations={{"+","add"},{"-","sub"},{"*","mul"},{"/","div"},{"%","rem"}};
            return temp(node.type,operations.contains(op)?helper("k_"+n(node.children[0]).type+"_"+operations.at(op),{a,b}):"("+a+" "+op+" "+b+")");
        }
        if(k=="union_ctor") {
            const auto [index,v]=variant(node.value,node.second);const auto args=arguments(node);
            auto init=initializers(n(v).children,args);if(init.empty()) init=".k_unused = 0";
            return temp(node.type,"("+ct(node.type)+"){.k_tag = "+std::to_string(index)+", .k_data.k_v_"+node.second+" = {"+init+"}}");
        }
        if(k=="format") {
            const auto value=expr(node.children[0]);const auto &ty=n(node.children[0]).type;strings_used=true;
            if(ty=="string")return value;
            if(ty=="bool")return temp("string","("+value+" ? (KString){(const unsigned char *)\"true\",4,4} : (KString){(const unsigned char *)\"false\",5,5})");
            return temp("string","k_string_from_"+(ty=="f64"?std::string("f64"):ty.starts_with("u")?std::string("u64"):std::string("i64"))+"("+value+")");
        }
        if(k=="concat") {const auto a=expr(node.children[0]);const auto b=expr(node.children[1]);strings_used=true;return temp("string","k_string_concat("+a+", "+b+")");}
        if(k=="call") {
            const auto args=arguments(node);
            if(aggregates.contains(node.value)) return temp(node.type,"("+ct(node.type)+"){"+initializers(n(aggregates.at(node.value)).children,args)+"}");
            if(u.aesop_syntax&&math_signatures.contains(node.value)) return temp("f64",node.value+"("+join(args)+")");
            if(node.value=="array_length") return temp("i64",std::to_string(array_type(n(node.children[0]).type)->count));
            if(generic_specialization(node.value)||view_specialization(node.value)) return temp(node.type,"k_"+node.value+"("+join(args)+")");
            if(map_specialization(node.value)||set_specialization(node.value)||new_container_type(node.value)) return temp(node.type,"k_"+node.value+"("+join(args)+")");
            if(platform_signatures.contains(node.value)) {if(node.value=="wall_clock_millis") {wall_clock_used=true;platform_used=true;}else if(node.value=="process_capture") {process_used=true;platform_used=true;strings_used=true;builders_used=true;generic_used.insert("string");}else if(node.value.starts_with("tcp_")) {tcp_used=true;platform_used=true;}else if(node.value.starts_with("stdin_")||node.value.starts_with("stdout_")||node.value.starts_with("stderr_")||node.value.starts_with("env_")) {streams_used=true;files_used=true;strings_used=true;platform_used=true;}else if(node.value.starts_with("spool_")) {builders_used=true;strings_used=true;} else if(node.value.starts_with("int_vector_")) vectors_used=true;else if(node.value=="buffer_text"||node.value=="buffer_text_valid"||node.value=="buffer_write_text") {strings_used=true;platform_used=true;}else if(node.value.starts_with("file_")) {files_used=true;strings_used=true;platform_used=true;} else if(node.value.starts_with("arg_")) {arguments_used=true;if(node.value=="arg_text"||node.value=="arg_text_valid") strings_used=true;}else if(!node.value.starts_with("string_")) platform_used=true;return temp(node.type,"k_"+node.value+"("+join(args)+")");}
            const auto name=node.value=="print"?"k_print_"+n(node.children[0]).type:"k_fn_"+node.value;
            return temp(node.type,node.value=="print"?helper(name,args):name+"("+join(args)+")");
        }
        throw std::runtime_error("verified expression missing");
    }
    std::string place(Id id) {
        const auto &node=n(id);if(node.kind=="name") return pointers.contains(node.symbol)?"(*"+node.symbol+")":node.symbol;
        const auto base=place(node.children[0]);
        if(node.kind=="index") {const auto index=expr(node.children[1]);const auto checked=temp("u64","k_array_index("+index+","+std::to_string(array_type(n(node.children[0]).type)->count)+")");return base+".data["+checked+"]";}
        return base+".k_f_"+node.value;
    }
    void matched(const Node &node) {
        const auto snapshot=expr(node.children[0]);const auto owner=n(node.children[0]).type;
        line("switch ("+snapshot+".k_tag) {");++depth;
        for(auto arm_id:list(node.children[1])) {
            const auto &arm=n(arm_id);const auto [index,v]=variant(owner,arm.second);const auto &binders=list(arm.children[0]);const auto &fields=n(v).children;
            line("case "+std::to_string(index)+": {");++depth;
            for(size_t i=0;i<binders.size();++i) {
                const auto &b=n(binders[i]);if(b.value!="_") line(ct(b.type)+" "+b.symbol+" = "+snapshot+".k_data.k_v_"+arm.second+".k_f_"+n(fields[i]).value+";");
            }
            block(list(arm.children[1]));line("break;");--depth;line("}");
        }
        line("default: k_bad_tag();");--depth;line("}");
    }
    void unwind(size_t keep) {
        for(size_t i=cleanups.size();i>keep;--i) cleanup_scope(cleanups[i-1]);
    }
    void cleanup_scope(const std::vector<std::string> &scope) {
        for(auto it=scope.rbegin();it!=scope.rend();++it) line(*it);
    }
    void cleanup_all() {for(auto it=cleanups.rbegin();it!=cleanups.rend();++it) cleanup_scope(*it);}
    void block(const List &statements,const List &params={}) {
        cleanups.emplace_back();
        for(auto p:params) if(n(p).kind=="mut_param") pointers.insert(n(p).symbol);
        for(auto p:params) if(n(p).kind=="own_param") {
            const auto &param=n(p);if(generic_type(param.second)||map_type(param.second)||set_type(param.second)) {} else if(param.second=="int_vector") vectors_used=true;else {builders_used=true;strings_used=true;}
            cleanups.back().push_back("if ("+release_name(param.second,"valid")+"("+param.symbol+")) "+release_name(param.second,"free")+"("+param.symbol+");");
        }
        for(auto id:statements) {
            const auto &node=n(id);const auto &k=node.kind;
            if(k=="local"||k=="scoped_local") {
                const auto x=expr(node.children[0]);line(ct(node.second)+" "+node.symbol+" = "+x+";");
                if(k=="scoped_local") {
                    if(generic_type(node.second)||map_type(node.second)||set_type(node.second)) {} else if(node.second=="int_vector") vectors_used=true;else {builders_used=true;strings_used=true;}
                    cleanups.back().push_back("if ("+release_name(node.second,"valid")+"("+node.symbol+")) "+release_name(node.second,"free")+"("+node.symbol+");");
                }
            }
            else if(k=="assign"||k=="global_assign") {const auto x=expr(node.children[0]);line(node.symbol+" = "+x+";");}
            else if(k=="store") {const auto target=place(node.children[0]);const auto x=expr(node.children[1]);line(target+" = "+x+";");}
            else if(k=="return") {
                if(n(node.children[0]).kind=="unit") {cleanup_all();line("return;");continue;}
                const auto value=expr(node.children[0]);bool pending=false;
                for(const auto &scope:cleanups) pending=pending||!scope.empty();
                const auto x=pending&&!value.empty()?temp(n(node.children[0]).type,value):value;
                cleanup_all();line(x.empty()?"return;":"return "+x+";");
            }
            else if(k=="defer") {
                const auto &call=n(node.children[0]);const auto argument=expr(call.children[0]);
                const auto captured=temp(n(call.children[0]).type,argument);
                if(generic_free(call.value)||map_specialization(call.value)||set_specialization(call.value)) {} else if(call.value=="spool_free") {builders_used=true;strings_used=true;} else if(call.value=="int_vector_free") vectors_used=true;else if(call.value=="tcp_close") {tcp_used=true;platform_used=true;}else if(call.value=="file_close") {files_used=true;strings_used=true;platform_used=true;}else platform_used=true;
                cleanups.back().push_back("k_"+call.value+"("+captured+");");
            }
            else if(k=="expr") {const auto value=expr(node.children[0]);if(!value.empty()) line("(void)("+value+");");}
            else if(k=="if") {
                const auto condition=expr(node.children[0]);line("if ("+condition+") {");++depth;block(list(node.children[1]));--depth;
                line("} else {");++depth;block(list(node.children[2]));--depth;line("}");
            } else if(k=="break"||k=="continue") {
                unwind(loop_scopes.back());line(k=="break"?"break;":"continue;");
            } else if(k=="while") {
                line("while (true) {");++depth;const auto condition=expr(node.children[0]);line("if (!"+condition+") break;");
                loop_scopes.push_back(cleanups.size());block(list(node.children[1]));loop_scopes.pop_back();--depth;line("}");
            } else if(k=="for_range") {
                const auto start=expr(node.children[0]);const auto finish=temp("i64",expr(node.children[1]));
                line("for (int64_t "+node.symbol+" = "+start+"; "+node.symbol+" < "+finish+"; ++"+node.symbol+") {");++depth;
                loop_scopes.push_back(cleanups.size());block(list(node.children[2]));loop_scopes.pop_back();--depth;line("}");
            } else if(k=="for_each") {
                const auto collection_type=n(node.children[0]).type;
                const auto collection=temp(collection_type,expr(node.children[0]));
                const auto index="k_i"+std::to_string(++serial);
                if(map_type(collection_type)||set_type(collection_type)) {
                    const bool container_is_map=bool(map_type(collection_type));
                    const auto wrapper=container_is_map?"k_map_iter_"+map_type(collection_type)->first+"_"+map_type(collection_type)->second:"k_set_iter_"+*set_type(collection_type);
                    const auto epilogue=container_is_map?std::string(",NULL"):std::string();
                    line(ct(node.second)+" "+node.symbol+";");
                    line("int64_t "+index+" = 0;");
                    line("while ("+wrapper+"("+collection+",&"+index+",&"+node.symbol+epilogue+")) {");++depth;
                    loop_scopes.push_back(cleanups.size());block(list(node.children[1]));loop_scopes.pop_back();--depth;line("}");
                } else if(collection_type=="string") {
                    strings_used=true;line(ct(node.second)+" "+node.symbol+";");line("int64_t "+index+" = 0;");
                    line("while (k_string_next("+collection+",&"+index+",&"+node.symbol+")) {");++depth;
                    loop_scopes.push_back(cleanups.size());block(list(node.children[1]));loop_scopes.pop_back();--depth;line("}");
                } else {
                    std::string length,get;
                    if(auto element=generic_type(collection_type)) {generic_used.insert(*element);length="k_vector_length_"+*element+"("+collection+")";get="k_vector_get_"+*element+"("+collection+","+index+")";}
                    else if(auto element=view_type(collection_type)) {generic_used.insert(*element);length="k_view_length_"+*element+"("+collection+")";get="k_view_get_"+*element+"("+collection+","+index+")";}
                    else if(collection_type=="int_vector") {vectors_used=true;length="k_int_vector_length("+collection+")";get="k_int_vector_get("+collection+","+index+")";}
                    else {const auto a=array_type(collection_type);length=std::to_string(a->count);get=collection+".data["+index+"]";}
                    line("for (int64_t "+index+" = 0; "+index+" < "+length+"; ++"+index+") {");++depth;
                    line(ct(node.second)+" "+node.symbol+" = "+get+";");
                    loop_scopes.push_back(cleanups.size());block(list(node.children[1]));loop_scopes.pop_back();--depth;line("}");
                }
            }
            else if(k=="match") matched(node);
            else throw std::runtime_error("verified statement missing");
        }
        cleanup_scope(cleanups.back());cleanups.pop_back();
        for(auto p:params) if(n(p).kind=="mut_param") pointers.erase(n(p).symbol);
    }
    std::string signature(const Node &f) const {
        std::vector<std::string> args;for(auto id:list(f.children[0])) {const auto &p=n(id);args.push_back(ct(p.second)+(p.kind=="mut_param"?" *":" ")+p.symbol);}
        return "static "+ct(f.second)+" k_fn_"+f.value+"("+(args.empty()?"void":join(args))+")";
    }
    void visit(const std::string &name) {
        if(arrays.contains(name)) {if(ordered.insert(name).second) {visit(array_type(name)->element);order.push_back(name);}return;}
        if(!aggregates.contains(name)||!ordered.insert(name).second) return;
        const auto id=aggregates.at(name);const auto &d=n(id);
        if(d.kind=="struct") {for(auto f:d.children) visit(n(f).second);}
        else for(auto v:d.children) for(auto f:n(v).children) visit(n(f).second);
        order.push_back(name);
    }
public:
    explicit CEmitter(const Unit &unit):u(unit) {}
    std::string emit() {
        Verifier verifier(u);verifier.run(); // Mandatory on every emission, never cached.
        aggregates.clear();arrays.clear();generic_used.clear();containers_used.clear();
        std::unordered_set<std::string> array_types;
        auto collect=[&](std::string ty) {
            while(auto a=array_type(ty)) {array_types.insert(ty);ty=a->element;}
            if(auto e=generic_type(ty)) generic_used.insert(*e);
            if(auto e=view_type(ty)) generic_used.insert(*e);
            if(auto m=map_type(ty)) {containers_used.insert(ty);generic_used.insert(m->first);generic_used.insert(m->second);}
            if(auto s=set_type(ty)) {containers_used.insert(ty);generic_used.insert(*s);}
        };
        // The verifier validates the reachable tree, not arbitrary arena junk.
        // Never render types or infer runtime dependencies from orphan nodes.
        std::vector<Id> reachable,work=u.roots;
        while(!work.empty()) {const auto id=work.back();work.pop_back();reachable.push_back(id);const auto &node=n(id);work.insert(work.end(),node.children.begin(),node.children.end());}
        for(auto id:reachable) {const auto &node=n(id);collect(node.type);if(node.kind=="function"||(node.kind=="param"||(node.kind=="borrow_param"||node.kind=="own_param"))||(node.kind=="local"||node.kind=="scoped_local")||node.kind=="field_decl") collect(node.second);}
        std::vector<std::string> sorted(array_types.begin(),array_types.end());std::sort(sorted.begin(),sorted.end());
        for(size_t i=0;i<sorted.size();++i) arrays[sorted[i]]="k_array_"+std::to_string(i);
        arrays_used=!arrays.empty();
        for(auto id:u.roots) if(n(id).kind=="struct"||n(id).kind=="union") aggregates[n(id).value]=id;
        // Per-call state makes repeated output deterministic as well.
        process_used=false;tcp_used=false;streams_used=false;files_used=false;arguments_used=false;vectors_used=false;platform_used=false;strings_used=false;builders_used=false;
        for(auto id:reachable) {const auto &node=n(id);if(node.kind=="string"||node.type=="string"||((node.kind=="function"||node.kind=="field_decl"||(node.kind=="param"||(node.kind=="borrow_param"||node.kind=="own_param"))||(node.kind=="local"||node.kind=="scoped_local"))&&node.second=="string")) strings_used=true;}
        for(auto id:reachable) {const auto &node=n(id);if(node.type=="spool"||((node.kind=="function"||node.kind=="field_decl"||(node.kind=="param"||(node.kind=="borrow_param"||node.kind=="own_param"))||(node.kind=="local"||node.kind=="scoped_local"))&&node.second=="spool")) builders_used=true;}
        for(const auto &ty:sorted) {const auto a=array_type(ty);if(a->element=="string") strings_used=true;if(a->element=="spool") builders_used=true;}
        if(u.project_syntax) {
            for(auto id:reachable) {const auto &node=n(id);if(node.type=="int_vector"||node.second=="int_vector") vectors_used=true;}
            for(const auto &ty:sorted) if(array_type(ty)->element=="int_vector") vectors_used=true;
        }
        if(builders_used||generic_used.contains("string")) strings_used=true;
        cleanups.clear();body.clear();helpers.clear();ordered.clear();order.clear();serial=depth=0;
        for(auto id:u.roots) if(n(id).kind=="struct"||n(id).kind=="union") visit(n(id).value);
        for(const auto &ty:sorted) visit(ty);
        for(const auto &name:order) {
            if(auto a=array_type(name)) {line("typedef struct { "+ct(a->element)+" data["+std::to_string(a->count)+"]; } "+ct(name)+";");continue;}
            const auto &d=n(aggregates.at(name));line("typedef struct k_s_"+d.value+" {");
            if(d.kind=="struct") {for(auto f:d.children) line("    "+ct(n(f).second)+" k_f_"+n(f).value+";");}
            else {
                line("    uint32_t k_tag;");line("    union {");
                for(auto v:d.children) {
                    line("        struct {");
                    for(auto f:n(v).children) line("            "+ct(n(f).second)+" k_f_"+n(f).value+";");
                    if(n(v).children.empty()) line("            uint8_t k_unused;");
                    line("        } k_v_"+n(v).value+";");
                }
                line("    } k_data;");
            }
            line("} k_s_"+d.value+";");
        }
        for(const auto &name:order) if(!arrays.contains(name)&&resource_struct(name)) {
            // dependencies: struct typedefs precede; emitted before functions, after container wrappers via forward use only
            line(resource_struct_functions(name));
        }
        for(const auto id:u.global_order) line("static "+ct(n(id).second)+" "+n(id).symbol+";");
        if(!u.global_order.empty()) {
            line("static void k_init_globals(void) {");depth=1;
            for(const auto id:u.global_order) {const auto &g=n(id);const auto value=expr(g.children[0]);line(g.symbol+" = "+value+";");}
            depth=0;line("}");
        }
        for(auto id:u.roots) if(n(id).kind=="function") line(signature(n(id))+";");
        for(auto id:u.roots) if(n(id).kind=="function") {line(signature(n(id))+" {");depth=1;block(list(n(id).children[1]),list(n(id).children[0]));depth=0;line("}");}
        if(!u.global_order.empty()) line(arguments_used?"int main(int argc,char **argv) { k_program_argc=argc;k_program_argv=argv;k_init_globals();return (int)((uint64_t)k_fn_main() & UINT64_C(255)); }":"int main(void) { k_init_globals();return (int)((uint64_t)k_fn_main() & UINT64_C(255)); }");
        else line(arguments_used?"int main(int argc,char **argv) { k_program_argc=argc;k_program_argv=argv;return (int)((uint64_t)k_fn_main() & UINT64_C(255)); }":"int main(void) { return (int)((uint64_t)k_fn_main() & UINT64_C(255)); }");
        std::string runtime;for(const auto &entry:c_helpers) if(helpers.contains(entry.name)) runtime+=entry.body;
        if(helpers.contains("k_print_f64")) runtime+="\nstatic void k_print_f64(double x) {printf(\"%.17g\\n\", x); }\n";
        if(runtime.empty()) runtime="\n";
        auto output=((tcp_used||process_used)?std::string("#define _GNU_SOURCE 1\n"):std::string())+(platform_used?std::string("#define _POSIX_C_SOURCE 200809L\n"):std::string())+c_runtime+(u.aesop_syntax?std::string("\n#include <math.h>\n"):std::string())+runtime+(arrays_used?std::string("\nstatic size_t k_array_index(int64_t i,size_t n) {if(i<0 || (uint64_t)i>=n) {fputs(\"Awl array bounds trap\\n\",stderr);abort();}return (size_t)i;}\n"):std::string())+(strings_used?c_strings:std::string())+(builders_used?c_builders:std::string())+(vectors_used?c_vectors:std::string())+(!generic_used.empty()?std::string(c_generic)+generic_wrappers():std::string())+(!containers_used.empty()?std::string(c_maps)+container_wrappers():std::string())+(arguments_used?c_arguments:std::string())+(platform_used?c_platform:std::string())+(wall_clock_used?c_wall_clock:std::string())+(files_used?c_files:std::string())+(streams_used?c_streams:std::string())+(tcp_used?c_tcp:std::string())+(process_used?c_process:std::string())+body;
        if(output.size()>67108864) throw Failure{{"E501","C emission budget exceeded",UINT32_MAX}};
        return output;
    }
};
