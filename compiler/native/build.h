#ifndef Awl_BUILD_H
#define Awl_BUILD_H
#include <cstddef>
#include <string>
#include <vector>
namespace Awl_driver {
struct Options {
    std::vector<std::string> protected_inputs; // Loaded module sources and Package manifests.
    std::vector<std::string> program_arguments;
    std::string host_cc; // Explicit absolute compiler path, Linux x86-64 only.
    int optimization=2;
    unsigned build_timeout_seconds=120;
    unsigned build_memory_mib=4096;
    unsigned run_timeout_seconds=0;
};
// Linux/Windows x86-64 bundles by default. No implicit host-tool fallback.
int build(const char *c_source,size_t length,const char *argv0,const std::string &source_path,
          const std::string &output,const Options &options,bool run);
}
#endif
