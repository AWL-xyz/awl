#ifndef Awl_PACKAGE_H
#define Awl_PACKAGE_H

#include <cstddef>
#include <filesystem>
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

// Private manifest reader shared by the compiler and the local package installer.
namespace Awl_package {
namespace fs=std::filesystem;
inline constexpr std::size_t manifest_limit=16*1024;
inline constexpr std::size_t source_limit=1024*1024;

inline bool ascii_alnum(char c) {
    return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9');
}
inline bool reserved_device_name(std::string_view filename) {
    // Win32 device names stay reserved even when followed by an extension.
    auto stem=filename.substr(0,filename.find('.'));
    while(stem.ends_with(' ')) stem.remove_suffix(1);
    std::string upper(stem);
    for(char &c:upper) if(c>='a'&&c<='z') c-='a'-'A';
    if(upper=="CON"||upper=="PRN"||upper=="AUX"||upper=="NUL"||upper=="CONIN$"||upper=="CONOUT$") return true;
    if(!upper.starts_with("COM")&&!upper.starts_with("LPT")) return false;
    const auto suffix=std::string_view(upper).substr(3);
    return (suffix.size()==1&&suffix[0]>='1'&&suffix[0]<='9')||
        suffix=="\xc2\xb9"||suffix=="\xc2\xb2"||suffix=="\xc2\xb3";
}
inline bool valid_name(std::string_view name) {
    if(name.empty()||name.size()>64) return false;
    for(char c:name) if(!ascii_alnum(c)&&c!='_'&&c!='-') return false;
    return !reserved_device_name(name);
}
inline bool valid_entry(std::string_view entry) {
    if(entry.size()>128||entry.starts_with('.')||!entry.ends_with(".aw")||
       entry.find_first_of("/\\:<>\"|?*")!=std::string_view::npos) return false;
    for(unsigned char c:entry) if(c<32) return false;
    return !reserved_device_name(entry);
}
inline std::string path_text(const fs::path &file) {
    const auto utf8=file.generic_u8string();
    return std::string(utf8.begin(),utf8.end());
}
inline std::string read_file(const fs::path &file,std::size_t limit) {
    if(!fs::is_regular_file(fs::symlink_status(file)))
        throw std::runtime_error("expected a regular non-symlink file: "+path_text(file));
    const auto size=fs::file_size(file);
    if(size>limit) throw std::runtime_error("file exceeds the size budget: "+path_text(file));
    std::ifstream in(file,std::ios::binary);
    std::string bytes(static_cast<std::size_t>(size),'\0');
    if(!in.read(bytes.data(),static_cast<std::streamsize>(bytes.size()))||
       in.peek()!=std::char_traits<char>::eof()||in.bad())
        throw std::runtime_error("cannot read file or its size changed: "+path_text(file));
    return bytes;
}
inline std::string trim(const std::string &line) {
    const auto first=line.find_first_not_of(" \t\r");
    return first==std::string::npos?std::string():line.substr(first,line.find_last_not_of(" \t\r")-first+1);
}
struct Manifest {std::string bytes,entry;};
inline Manifest read_manifest(const fs::path &file,const std::string &name) {
    if(!valid_name(name)||path_text(file.filename())!=name+".awpkg")
        throw std::runtime_error("expected a NAME.awpkg manifest with a valid Package name");
    // Do not let a case-insensitive filesystem select a differently named manifest.
    bool exact=false;
    for(const auto &item:fs::directory_iterator(file.parent_path()))
        if(item.path().filename()==file.filename()) {exact=true;break;}
    if(!exact) throw std::runtime_error("missing or wrong-case Package manifest: "+path_text(file));
    Manifest result{read_file(file,manifest_limit),name+".aw"};
    if(result.bytes.find('\0')!=std::string::npos) throw std::runtime_error("NUL byte in Package manifest");
    std::istringstream lines(result.bytes);std::string line;
    std::set<std::string> keys;bool format=false,kind=false,named=false;
    while(std::getline(lines,line)) {
        line=trim(line);
        if(line.empty()||line[0]=='#') continue;
        const auto colon=line.find(':');
        if(colon==std::string::npos) throw std::runtime_error("expected key: value in Package manifest");
        const auto key=trim(line.substr(0,colon)),value=trim(line.substr(colon+1));
        if(key.empty()) throw std::runtime_error("empty key in Package manifest");
        if(!keys.insert(key).second) throw std::runtime_error("duplicate Package manifest key: "+key);
        if(key=="format") format=value=="1";
        else if(key=="kind") kind=value=="package";
        else if(key=="name") named=value==name;
        else if(key=="entry") result.entry=value;
    }
    if(!format||!kind||!named)
        throw std::runtime_error("Package manifest must declare format: 1, kind: package and name: "+name);
    if(!valid_entry(result.entry))
        throw std::runtime_error("Package entry must be a plain .aw file name without reserved characters or device names");
    return result;
}

// Private ACC input enumeration, separate from the source/provenance C ABI.
void append_manifest_inputs(const void *unit,std::vector<std::string> &paths);
}
#endif
