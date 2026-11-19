#ifndef Awl_FORMAT_H
#define Awl_FORMAT_H

#include <string>
#include <string_view>

// Private toolkit interface: parse and lay out a single source, without
// imports, type checking, backend selection, or changes to the C ABI.
namespace Awl_format {
struct Result {
    std::string source;
    std::string diagnostic;
};
Result source(std::string_view input,const std::string &label,bool json);
}

#endif
