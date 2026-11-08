#ifndef Awl_LEX_H
#define Awl_LEX_H
#include <stddef.h>
#include <stdint.h>
#if defined(_WIN32)
#define KLEX_API __declspec(dllexport)
#else
#define KLEX_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif
/* Offsets and columns are Unicode code points, NOT UTF-8 bytes. */
typedef struct { uint32_t start, end, line, column, flags; } AwlLexToken;
typedef struct {
    AwlLexToken *tokens;
    void *owner;
    uint32_t count, position, line, column;
} AwlLexResult;
/* 0 success; 1 unexpected character; 2 token cap; 3 source size;
   4 invalid UTF-8; 5 invalid argument/allocation/internal failure. */
KLEX_API uint32_t Awl_lex_abi_version(void);
KLEX_API size_t Awl_lex_token_size(void);
KLEX_API size_t Awl_lex_result_size(void);
/* out must not own a previous result; free before reuse. Do not shallow-copy
   owned results. Source pointer must address at least size readable bytes. */
KLEX_API int Awl_lex(const char *source, size_t size, AwlLexResult *out);
/* Filesystem-project scanner: flag4 UTF-8 string tokens; status6 unterminated
   string. Legacy scanner above retains its token/error compatibility policy. */
KLEX_API int Awl_lex_project(const char *,size_t,AwlLexResult *);
/* Opt-in next-dialect scanner; legacy project scanning is unchanged. */
KLEX_API int Awl_lex_next(const char *,size_t,AwlLexResult *);
KLEX_API void Awl_lex_free(AwlLexResult *out);
/* Isolated C++ scan+allocation+free time; excludes FFI/text marshalling. */
KLEX_API int Awl_lex_benchmark(const char *, size_t, uint32_t, double *, uint64_t *);
#ifdef __cplusplus
}
#endif
#endif
