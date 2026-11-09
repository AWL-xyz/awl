#ifndef Awl_PARSE_H
#define Awl_PARSE_H
#include "klex.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Caller supplies validated tokens including EOF, and matching UTF-8 source.
   A successful call owns an opaque arena unit, even if it contains diagnostics.
   Return 0: unit created; 1: argument/encoding/budget failure; 2: internal failure.
   Valid caller memory and authentic live handles are required; not a sandbox.
   Free each unit exactly once. Returned strings are invalidated by the next
   corresponding export, checking/verifier rejection (JSON), or free. No concurrent use of a unit.
   Awl_parse_tokens requires lexically validated records; Awl_parse_source
   accepts untrusted source bytes and applies all scanner/policy checks.
   Awl_check_unit returns 0 accepted, 1 diagnosed, 2 internal/argument failure.
   It annotates the arena in place; not an independent IR-verification pass. */
KLEX_API uint32_t Awl_parse_abi_version(void);
KLEX_API int Awl_parse_tokens(const char *,size_t,const AwlLexToken *,uint32_t,void **);
KLEX_API int Awl_parse_source(const char *,size_t,void **);
/* Filesystem project entry: canonical entry directory is import root; bounded
   graph loading, namespace resolution and file provenance. No code execution.
   Paths returned below live until unit free. Source-byte APIs do not do I/O. */
KLEX_API int Awl_parse_file(const char *,void **);
KLEX_API uint32_t Awl_source_file_count(void *);
KLEX_API const char *Awl_source_file_path(void *,uint32_t);
KLEX_API uint32_t Awl_diagnostic_count(void *);
KLEX_API const char *Awl_render_diagnostics(void *,const char *,int,size_t *);
KLEX_API const char *Awl_parse_json(void *,size_t *);
KLEX_API int Awl_check_unit(void *);
/* Independent read-only arena verification; no checked-flag trust or caching.
   Return 0 valid, 1 rejected (E500 diagnostic), 2 internal/argument failure.
   Rejection updates diagnostics/export cache only, never arena annotations. */
KLEX_API int Awl_verify_unit(void *);
/* C11 transitional backend; independently verifies before every emission.
   Same status meanings as verify. Output owned by unit until next emit/free.
   Does not invoke a compiler/linker; not a binary build command. */
KLEX_API int Awl_emit_c(void *,const char **,size_t *);
KLEX_API uint32_t Awl_parse_node_count(void *);
KLEX_API void Awl_parse_free(void *);
KLEX_API int Awl_parse_benchmark(const char *,size_t,const AwlLexToken *,uint32_t,uint32_t,double *,uint64_t *);
#ifdef __cplusplus
}
#endif
#endif
