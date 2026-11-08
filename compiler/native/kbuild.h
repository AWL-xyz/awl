#ifndef Awl_BUILD_H
#define Awl_BUILD_H
#include <cstddef>
#include <string>
#include <vector>
namespace Awl_driver {
struct Options {
    std::vector<std::string> protected_sources;
    int optimization=2;
    unsigned build_timeout_seconds=120;
    unsigned build_memory_mib=4096;
    unsigned run_timeout_seconds=0;
};
// Linux/Windows x86-64 engineering bundles. No PATH lookup or host-tool fallback.
int build(const char *c_source,size_t length,const char *argv0,const std::string &source_path,
          const std::string &output,const Options &options,bool run);
}
#endif
