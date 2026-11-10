// Experimental native platform intrinsics. Shared ABI schema; checker and
// independent verifier each validate argument/result use against this schema.
// These are not user-declared functions or a general foreign-call escape hatch.
struct PlatformSignature { std::vector<std::string> parameters; std::string result; };
const std::unordered_map<std::string,PlatformSignature> platform_signatures=[] {
    std::unordered_map<std::string,PlatformSignature> table={
    {"tcp_listen_loopback",{{"i64","i64"},"i64"}},
    {"tcp_valid",{{"i64"},"bool"}},
    {"tcp_port",{{"i64"},"i64"}},
    {"tcp_accept",{{"i64","i64"},"i64"}},
    {"tcp_read",{{"i64","i64","i64","i64","i64"},"i64"}},
    {"tcp_write",{{"i64","i64","i64","i64","i64"},"i64"}},
    {"tcp_close",{{"i64"},"i64"}},
    {"process_capture",{{"string","view<string>","spool","spool","i64"},"i64"}},
    {"platform_kind",{{},"i64"}},
    {"buffer_text_valid",{{"i64","i64","i64"},"bool"}},
    {"buffer_text",{{"i64","i64","i64"},"string"}},
    {"buffer_write_text",{{"i64","i64","string"},"i64"}},
    {"file_replace",{{"string","string","string"},"i64"}},
    {"file_open",{{"string","i64"},"i64"}},
    {"file_valid",{{"i64"},"bool"}},
    {"file_close",{{"i64"},"i64"}},
    {"stdin_read",{{"i64","i64","i64"},"i64"}},
    {"stdout_write",{{"i64","i64","i64"},"i64"}},
    {"stderr_write",{{"i64","i64","i64"},"i64"}},
    {"stdout_flush",{{},"i64"}},
    {"stderr_flush",{{},"i64"}},
    {"env_size",{{"string"},"i64"}},
    {"env_read",{{"string","i64","i64","i64"},"i64"}},
    {"file_read",{{"i64","i64","i64","i64"},"i64"}},
    {"file_write",{{"i64","i64","i64","i64"},"i64"}},
    {"file_seek",{{"i64","i64"},"i64"}},
    {"file_size",{{"i64"},"i64"}},
    {"file_flush",{{"i64"},"i64"}},
    {"arg_text_valid",{{"i64"},"bool"}},
    {"arg_text",{{"i64"},"string"}},
    {"arg_count",{{},"i64"}},
    {"arg_i64_valid",{{"i64"},"bool"}},
    {"arg_i64",{{"i64"},"i64"}},
    {"int_vector_new",{{"i64"},"int_vector"}},
    {"int_vector_valid",{{"int_vector"},"bool"}},
    {"int_vector_free",{{"int_vector"},"unit"}},
    {"int_vector_length",{{"int_vector"},"i64"}},
    {"int_vector_capacity",{{"int_vector"},"i64"}},
    {"int_vector_reserve",{{"int_vector","i64"},"bool"}},
    {"int_vector_push",{{"int_vector","i64"},"bool"}},
    {"int_vector_pop",{{"int_vector"},"i64"}},
    {"int_vector_get",{{"int_vector","i64"},"i64"}},
    {"int_vector_set",{{"int_vector","i64","i64"},"unit"}},
    {"int_vector_clear",{{"int_vector"},"unit"}},
    {"int_vector_insert",{{"int_vector","i64","i64"},"bool"}},
    {"int_vector_remove",{{"int_vector","i64"},"i64"}},
    {"spool_new",{{"i64"},"spool"}},
    {"spool_valid",{{"spool"},"bool"}},
    {"spool_free",{{"spool"},"unit"}},
    {"spool_clear",{{"spool"},"unit"}},
    {"spool_reserve",{{"spool","i64"},"bool"}},
    {"spool_truncate",{{"spool","i64"},"bool"}},
    {"spool_capacity",{{"spool"},"i64"}},
    {"spool_bytes",{{"spool"},"i64"}},
    {"spool_length",{{"spool"},"i64"}},
    {"spool_append",{{"spool","string"},"i64"}},
    {"spool_codepoint",{{"spool","u32"},"i64"}},
    {"spool_i64",{{"spool","i64"},"i64"}},
    {"spool_u64",{{"spool","u64"},"i64"}},
    {"spool_print",{{"spool"},"i64"}},
    {"spool_snapshot",{{"spool"},"string"}},
    {"string_from_i64",{{"i64"},"string"}},
    {"string_from_u64",{{"u64"},"string"}},
    {"string_bytes",{{"string"},"i64"}},
    {"string_length",{{"string"},"i64"}},
    {"string_byte_at",{{"string","i64"},"u8"}},
    {"string_codepoint",{{"string","i64"},"u32"}},
    {"string_from_codepoint",{{"u32"},"string"}},
    {"string_slice",{{"string","i64","i64"},"string"}},
    {"string_compare",{{"string","string"},"i64"}},
    {"string_find",{{"string","string"},"i64"}},
    {"string_contains",{{"string","string"},"bool"}},
    {"string_starts_with",{{"string","string"},"bool"}},
    {"string_ends_with",{{"string","string"},"bool"}},
    {"string_replace",{{"string","string","string"},"string"}},
    {"window_set_title",{{"i64","string"},"bool"}},
    {"buffer_new",{{"i64"},"i64"}},
    {"buffer_size",{{"i64"},"i64"}},
    {"buffer_get",{{"i64","i64"},"u8"}},
    {"buffer_set",{{"i64","i64","u8"},"unit"}},
    {"buffer_free",{{"i64"},"unit"}},
    {"clock_millis",{{},"i64"}},
    {"wall_clock_millis",{{},"i64"}},
    {"sleep_millis",{{"i64"},"unit"}},
    {"window_open",{{"i64","i64"},"i64"}},
    {"window_width",{{"i64"},"i64"}},
    {"window_height",{{"i64"},"i64"}},
    {"window_set_pixel",{{"i64","i64","i64","i64"},"unit"}},
    {"window_present",{{"i64"},"bool"}},
    {"window_poll",{{"i64"},"i64"}},
    {"window_key",{{"i64"},"i64"}},
    {"window_mouse_x",{{"i64"},"i64"}},
    {"window_mouse_y",{{"i64"},"i64"}},
    {"window_close",{{"i64"},"unit"}}
    };
    for(const auto &e:generic_elements) {
        const auto v="vector<"+e+">";
        const std::unordered_map<std::string,PlatformSignature> methods={
            {"new",{{"i64"},v}},{"valid",{{v},"bool"}},{"free",{{v},"unit"}},
            {"length",{{v},"i64"}},{"capacity",{{v},"i64"}},{"reserve",{{v,"i64"},"bool"}},
            {"push",{{v,e},"bool"}},{"pop",{{v},e}},{"get",{{v,"i64"},e}},
            {"set",{{v,"i64",e},"unit"}},{"clear",{{v},"unit"}},
            {"insert",{{v,"i64",e},"bool"}},{"remove",{{v,"i64"},e}},
            {"view",{{v,"i64","i64"},"view<"+e+">"}},{"slice",{{v,"i64","i64"},v}},{"swap",{{v,"i64","i64"},"unit"}},{"truncate",{{v,"i64"},"bool"}}
        };
        const auto view="view<"+e+">";
        table.emplace("view_valid_"+e,PlatformSignature{{view},"bool"});
        table.emplace("view_length_"+e,PlatformSignature{{view},"i64"});
        table.emplace("view_get_"+e,PlatformSignature{{view,"i64"},e});
        table.emplace("view_slice_"+e,PlatformSignature{{view,"i64","i64"},view});
        for(const auto &[method,sig]:methods) table.emplace("vector_"+method+"_"+e,sig);
    }
    return table;
}();

// Public surface names use namespace.method with lowercase method names.
// Internal IR keeps the stable ABI names above; the parser translates surface calls.
const std::unordered_map<std::string,std::string> builtin_internal_to_surface={
    {"arg_count","arg.count"},
    {"arg_i64","arg.i64"},
    {"arg_i64_valid","arg.i64valid"},
    {"arg_text","arg.text"},
    {"arg_text_valid","arg.textvalid"},
    {"array_length","array.length"},
    {"buffer_free","buffer.free"},
    {"buffer_get","buffer.get"},
    {"buffer_new","buffer.new"},
    {"buffer_set","buffer.set"},
    {"buffer_size","buffer.size"},
    {"buffer_text","buffer.text"},
    {"buffer_text_valid","buffer.textvalid"},
    {"buffer_write_text","buffer.writetext"},
    {"clock_millis","clock.millis"},
    {"env_read","env.read"},
    {"env_size","env.size"},
    {"file_close","file.close"},
    {"file_flush","file.flush"},
    {"file_open","file.open"},
    {"file_read","file.read"},
    {"file_replace","file.replace"},
    {"file_seek","file.seek"},
    {"file_size","file.size"},
    {"file_valid","file.valid"},
    {"file_write","file.write"},
    {"int_vector_capacity","intvector.capacity"},
    {"int_vector_clear","intvector.clear"},
    {"int_vector_free","intvector.free"},
    {"int_vector_get","intvector.get"},
    {"int_vector_insert","intvector.insert"},
    {"int_vector_length","intvector.length"},
    {"int_vector_new","intvector.new"},
    {"int_vector_pop","intvector.pop"},
    {"int_vector_push","intvector.push"},
    {"int_vector_remove","intvector.remove"},
    {"int_vector_reserve","intvector.reserve"},
    {"int_vector_set","intvector.set"},
    {"int_vector_valid","intvector.valid"},
    {"map_clear","map.clear"},
    {"map_free","map.free"},
    {"map_get","map.get"},
    {"map_has","map.has"},
    {"map_keys","map.keys"},
    {"map_length","map.length"},
    {"map_new","map.new"},
    {"map_remove","map.remove"},
    {"map_set","map.set"},
    {"map_valid","map.valid"},
    {"map_values","map.values"},
    {"platform_kind","platform.kind"},
    {"process_capture","process.capture"},
    {"set_add","set.add"},
    {"set_clear","set.clear"},
    {"set_free","set.free"},
    {"set_has","set.has"},
    {"set_length","set.length"},
    {"set_new","set.new"},
    {"set_remove","set.remove"},
    {"set_valid","set.valid"},
    {"set_values","set.values"},
    {"sleep_millis","clock.sleep"},
    {"spool_append","spool.append"},
    {"spool_bytes","spool.bytes"},
    {"spool_capacity","spool.capacity"},
    {"spool_clear","spool.clear"},
    {"spool_codepoint","spool.codepoint"},
    {"spool_free","spool.free"},
    {"spool_i64","spool.i64"},
    {"spool_length","spool.length"},
    {"spool_new","spool.new"},
    {"spool_print","spool.print"},
    {"spool_reserve","spool.reserve"},
    {"spool_snapshot","spool.snapshot"},
    {"spool_truncate","spool.truncate"},
    {"spool_u64","spool.u64"},
    {"spool_valid","spool.valid"},
    {"stderr_flush","stderr.flush"},
    {"stderr_write","stderr.write"},
    {"stdin_read","stdin.read"},
    {"stdout_flush","stdout.flush"},
    {"stdout_write","stdout.write"},
    {"string_byte_at","string.byteat"},
    {"string_bytes","string.bytes"},
    {"string_codepoint","string.codepoint"},
    {"string_compare","string.compare"},
    {"string_contains","string.contains"},
    {"string_ends_with","string.endswith"},
    {"string_find","string.find"},
    {"string_from_codepoint","string.fromcodepoint"},
    {"string_from_i64","string.fromi64"},
    {"string_from_u64","string.fromu64"},
    {"string_length","string.length"},
    {"string_replace","string.replace"},
    {"string_slice","string.slice"},
    {"string_starts_with","string.startswith"},
    {"tcp_accept","tcp.accept"},
    {"tcp_close","tcp.close"},
    {"tcp_listen_loopback","tcp.listenloopback"},
    {"tcp_port","tcp.port"},
    {"tcp_read","tcp.read"},
    {"tcp_valid","tcp.valid"},
    {"tcp_write","tcp.write"},
    {"vector_capacity","vector.capacity"},
    {"vector_clear","vector.clear"},
    {"vector_free","vector.free"},
    {"vector_get","vector.get"},
    {"vector_insert","vector.insert"},
    {"vector_length","vector.length"},
    {"vector_new","vector.new"},
    {"vector_pop","vector.pop"},
    {"vector_push","vector.push"},
    {"vector_remove","vector.remove"},
    {"vector_reserve","vector.reserve"},
    {"vector_set","vector.set"},
    {"vector_slice","vector.slice"},
    {"vector_swap","vector.swap"},
    {"vector_truncate","vector.truncate"},
    {"vector_valid","vector.valid"},
    {"vector_view","vector.view"},
    {"view_get","view.get"},
    {"view_length","view.length"},
    {"view_slice","view.slice"},
    {"view_valid","view.valid"},
    {"wall_clock_millis","clock.wall"},
    {"window_close","window.close"},
    {"window_height","window.height"},
    {"window_key","window.key"},
    {"window_mouse_x","window.mousex"},
    {"window_mouse_y","window.mousey"},
    {"window_open","window.open"},
    {"window_poll","window.poll"},
    {"window_present","window.present"},
    {"window_set_pixel","window.pixel"},
    {"window_set_title","window.title"},
    {"window_width","window.width"}
};
const std::unordered_map<std::string,std::string> builtin_surface_to_internal=[] {
    std::unordered_map<std::string,std::string> table;
    for(const auto &[internal,surface]:builtin_internal_to_surface) table.emplace(surface,internal);
    return table;
}();
const std::unordered_set<std::string> builtin_internal_prefixes={
    "spool_","map_","set_","vector_","view_","string_","int_vector_","window_","buffer_","file_","tcp_","arg_","env_","stdin_","stdout_","stderr_","process_","platform_","clock_","wall_clock_","sleep_","array_"
};
bool builtin_internal_name(const std::string &name) {
    if(name.starts_with("kn_")) return false;
    for(const auto &prefix:builtin_internal_prefixes) if(name.starts_with(prefix)) return true;
    return false;
}
std::string builtin_surface_hint(const std::string &internal);
std::string builtin_surface_call(const std::string &internal) {
    const auto exact=builtin_internal_to_surface.find(internal);
    if(exact!=builtin_internal_to_surface.end()) return exact->second;
    if(internal.starts_with("vector_new_")) {
        const auto element=internal.substr(11);
        if(generic_element(element)) return "vector.new<"+element+">";
    }
    if(internal.starts_with("set_new_")) {
        const auto element=internal.substr(8);
        if(map_key_element(element)) return "set.new<"+element+">";
    }
    if(internal.starts_with("map_new_")) {
        const std::string rest=internal.substr(8);const size_t split=rest.find('_');
        if(split!=std::string::npos) {
            const auto key=rest.substr(0,split),value=rest.substr(split+1);
            if(map_key_element(key)&&generic_element(value)) return "map.new<"+key+","+value+">";
        }
    }
    std::string base=internal;bool stripped=false;
    for(int depth=0;depth<2;++depth) for(const auto &element:generic_elements) {
        const std::string suffix="_"+element;
        if(base.size()>suffix.size()&&base.ends_with(suffix)) {base.resize(base.size()-suffix.size());stripped=true;break;}
    }
    if(stripped) {const auto found=builtin_internal_to_surface.find(base);if(found!=builtin_internal_to_surface.end()) return found->second;}
    const auto hint=builtin_surface_hint(internal);return hint.empty()?internal:hint;
}
std::string builtin_surface_hint(const std::string &internal) {
    const auto found=builtin_internal_to_surface.find(internal);
    if(found!=builtin_internal_to_surface.end()) return found->second;
    for(const auto &element:generic_elements) {
        const std::string suffix="_"+element;
        if(internal.size()>suffix.size()&&internal.ends_with(suffix)) return builtin_surface_hint(internal.substr(0,internal.size()-suffix.size()));
    }
    return {};
}
