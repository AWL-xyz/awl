/* Contributor white-box runtime tests: real USER32/GDI windows, not mocks.
 * Programmatic messages exercise dispatch; this is not physical input evidence. */
#include <stdint.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
static int fail_allocation;
static void *fixture_calloc(size_t n,size_t s){return fail_allocation?NULL:calloc(n,s);}
#define calloc fixture_calloc
#include "../compiler/native/strings.c"
#include "../compiler/native/platform.c"
#undef calloc
static void drain(int64_t id){for(int i=0;i<1024;++i){int64_t e=k_window_poll(id);assert(e!=1);if(!e)return;}assert(!"event queue did not drain");}
static int next(int64_t id){for(int i=0;i<1024;++i){int e=(int)k_window_poll(id);if(e!=2)return e;}assert(0);return -1;}
static void pass(const char *s){puts(s);fflush(stdout);}
int main(void){
 assert(!k_window_open(0,32)&&!k_window_open(32,0)&&!k_window_open(-1,32)&&!k_window_open(2049,32));pass("PASS invalid dimensions");
 fail_allocation=1;assert(!k_window_open(32,32));fail_allocation=0;assert(k_window_bytes==0);pass("PASS open allocation failure");
 int64_t id=k_window_open(96,64);assert(id);KWindow *w=k_window(id);assert(IsWindow(w->hwnd));drain(id);assert(k_window_width(id)==96&&k_window_height(id)==64);
 k_window_set_pixel(id,0,0,0x112233);k_window_set_pixel(id,95,63,0x3399cc);assert(k_window_present(id));
 HDC dc=GetDC(w->hwnd);assert(GetPixel(dc,0,0)==RGB(0x11,0x22,0x33));assert(GetPixel(dc,95,63)==RGB(0x33,0x99,0xcc));ReleaseDC(w->hwnd,dc);pass("PASS real GDI top-down corner pixels");
 const unsigned char title[]="Awl \xc3\xa9 \xf0\x9f\x8e\xa8";KString text={title,sizeof(title)-1,0};assert(k_window_set_title(id,text));wchar_t got[64];GetWindowTextW(w->hwnd,got,64);assert(wcscmp(got,L"Awl \u00e9 \U0001f3a8")==0);
 unsigned char nul[]={0},bad[]={0xff},large[1025]={1};assert(!k_window_set_title(id,(KString){nul,1,1}));assert(!k_window_set_title(id,(KString){bad,1,1}));assert(!k_window_set_title(id,(KString){large,1025,1025}));assert(k_window_set_title(id,(KString){NULL,0,0}));GetWindowTextW(w->hwnd,got,64);assert(!got[0]);pass("PASS UTF-8 title, empty, NUL, length, malformed rejection");
 drain(id);SendMessageW(w->hwnd,WM_KEYDOWN,'A',0);SendMessageW(w->hwnd,WM_KEYUP,'A',0);SendMessageW(w->hwnd,WM_MOUSEMOVE,0,MAKELPARAM(7,9));SendMessageW(w->hwnd,WM_LBUTTONDOWN,0,MAKELPARAM(7,9));SendMessageW(w->hwnd,WM_LBUTTONUP,0,MAKELPARAM(7,9));
 assert(next(id)==4&&k_window_key(id)=='A');assert(next(id)==5&&k_window_key(id)=='A');assert(next(id)==6&&k_window_mouse_x(id)==7&&k_window_mouse_y(id)==9);assert(next(id)==7&&k_window_key(id)==1);assert(next(id)==8&&k_window_key(id)==1);pass("PASS key, motion, button dispatch snapshots");
 drain(id);for(int i=0;i<100;++i)SendMessageW(w->hwnd,WM_MOUSEMOVE,0,MAKELPARAM(i,i+1));assert(w->queue_count==1);assert(next(id)==6&&k_window_mouse_x(id)==99&&k_window_mouse_y(id)==100);pass("PASS pointer event coalescing");
 RECT rect={0,0,80,72};assert(AdjustWindowRectEx(&rect,WS_OVERLAPPEDWINDOW,FALSE,0));assert(SetWindowPos(w->hwnd,NULL,0,0,rect.right-rect.left,rect.bottom-rect.top,SWP_NOMOVE|SWP_NOZORDER));assert(k_window_width(id)==96);assert(next(id)==3);assert(k_window_width(id)==80&&k_window_height(id)==72);assert(w->pixels[0]==0&&k_window_bytes==80*72*4);assert(k_window_present(id));pass("PASS actual client resize, deferred allocation and cleared pixels");
 ShowWindow(w->hwnd,SW_MINIMIZE);drain(id);assert(!w->closed&&k_window_width(id)==80);ShowWindow(w->hwnd,SW_RESTORE);drain(id);pass("PASS minimize/restore retains framebuffer");
 int64_t second=k_window_open(40,40);assert(second);drain(id);drain(second);SendMessageW(k_window(second)->hwnd,WM_KEYDOWN,'B',0);assert(next(id)==0);assert(next(second)==4&&k_window_key(second)=='B');k_window_close(second);pass("PASS independent multiwindow queues");
 drain(id);fail_allocation=1;SendMessageW(w->hwnd,WM_SIZE,SIZE_RESTORED,MAKELPARAM(90,80));assert(next(id)==1);fail_allocation=0;assert(k_window_width(id)==80&&k_window_bytes==80*72*4);k_window_close(id);assert(!k_window_bytes);pass("PASS failed resize preserves allocation until cleanup");
 id=k_window_open(32,32);assert(id);drain(id);w=k_window(id);SendMessageW(w->hwnd,WM_SIZE,SIZE_RESTORED,MAKELPARAM(2049,32));assert(next(id)==1);k_window_close(id);assert(!k_window_bytes);pass("PASS oversized resize closes safely");
 int64_t last=id;for(int i=0;i<100;++i){id=k_window_open(32,32);assert(id>last);last=id;k_window_close(id);}assert(!k_window_bytes);pass("PASS 100 create/destroy identities and reclamation");
 int64_t ids[16];for(int i=0;i<16;++i){ids[i]=k_window_open(32,32);assert(ids[i]);}assert(!k_window_open(32,32));for(int i=0;i<16;++i)k_window_close(ids[i]);assert(!k_window_bytes);pass("PASS 16-window slot bound");
 for(int i=0;i<4;++i){ids[i]=k_window_open(2048,2048);assert(ids[i]);}assert(k_window_bytes==K_BUFFER_TOTAL&&!k_window_open(1,1));k_window_close(ids[0]);ids[0]=k_window_open(1,1);assert(ids[0]);for(int i=0;i<4;++i)k_window_close(ids[i]);assert(!k_window_bytes);pass("PASS 64MiB payload budget and refill");
 id=k_window_open(32,32);assert(id);drain(id);w=k_window(id);for(int i=0;i<65;++i)SendMessageW(w->hwnd,i%2?WM_KEYDOWN:WM_KEYUP,'C',0);assert(k_window_poll(id)==1&&!k_window_present(id));k_window_close(id);assert(!k_window_bytes);pass("PASS bounded discrete-event overflow closes safely");
 id=k_window_open(32,32);assert(id);drain(id);w=k_window(id);SendMessageW(w->hwnd,WM_CLOSE,0,0);assert(k_window_poll(id)==1&&!k_window_present(id)&&!k_window_set_title(id,text));k_window_close(id);assert(!k_window_bytes);pass("PASS sticky close and cleanup");
 id=k_window_open(32,32);assert(id);PostQuitMessage(0);assert(k_window_poll(id)==1);k_window_close(id);assert(!k_window_bytes);pass("PASS thread quit cleanup");
 return 0;
}
