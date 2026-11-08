/* Awl experimental platform runtime. Embedded into generated C, not linked to
 * host Xlib/SDL. Windows uses native USER32/GDI; Linux window transport is a bounded local X11 protocol client.
 * This is a CPU framebuffer API, not a toolkit, Wayland or ownership checker. */
#include <string.h>
#include <errno.h>
#include <time.h>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif
#if defined(__linux__)
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/time.h>
#include <poll.h>
#endif
static _Noreturn void k_resource_trap(void) {
    fputs("Awl resource trap: invalid handle, bounds, or argument\n", stderr);
    abort();
}
/* OS family only, not keyboard-layout or text-input normalization. */
static int64_t k_platform_kind(void) {
#if defined(_WIN32)
    return 2;
#elif defined(__linux__)
    return 1;
#else
    return 0;
#endif
}
static int64_t k_clock_millis(void) {
#if defined(_WIN32)
    return (int64_t)GetTickCount64();
#else
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) k_resource_trap();
    return (int64_t)t.tv_sec*1000 + t.tv_nsec/1000000;
#endif
}
static void k_sleep_millis(int64_t ms) {
    if (ms < 0 || ms > 60000) k_resource_trap();
#if defined(_WIN32)
    Sleep((DWORD)ms);
#else
    struct timespec t = { (time_t)(ms/1000), (long)(ms%1000)*1000000 };
    while (nanosleep(&t, &t) && errno == EINTR) {}
#endif
}
#define K_BUFFER_TOTAL (64u*1024u*1024u)
typedef struct { int64_t id; size_t size; uint8_t *data; } KBuffer;
static KBuffer k_buffers[64];
static size_t k_buffer_bytes;
static int64_t k_next_buffer = 1;
static KBuffer *k_buffer(int64_t id) {
    for (size_t i=0; i<64; ++i) if (id > 0 && k_buffers[i].id == id) return &k_buffers[i];
    k_resource_trap();
}
static int64_t k_buffer_new(int64_t size) {
    if (size < 0 || size > 16*1024*1024 || (uint64_t)size > K_BUFFER_TOTAL-k_buffer_bytes || k_next_buffer>=INT64_C(4294967296)) return 0;
    for (size_t i=0; i<64; ++i) if (!k_buffers[i].id) {
        uint8_t *data = calloc(size ? (size_t)size : 1, 1);
        if (!data) return 0;
        k_buffers[i] = (KBuffer){k_next_buffer++, (size_t)size, data};
        k_buffer_bytes += (size_t)size;
        return k_buffers[i].id;
    }
    return 0;
}
static int64_t k_buffer_size(int64_t id) { return (int64_t)k_buffer(id)->size; }
static uint8_t k_buffer_get(int64_t id, int64_t index) {
    KBuffer *b=k_buffer(id);
    if (index<0 || (uint64_t)index>=b->size) k_resource_trap();
    return b->data[index];
}
static void k_buffer_set(int64_t id, int64_t index, uint8_t value) {
    KBuffer *b=k_buffer(id);
    if (index<0 || (uint64_t)index>=b->size) k_resource_trap();
    b->data[index]=value;
}
static void k_buffer_free(int64_t id) {
    KBuffer *b=k_buffer(id);
    k_buffer_bytes-=b->size;
    free(b->data); memset(b,0,sizeof(*b));
}
/* Windows also use generation-like monotonically increasing IDs, in a separate
 * range. No pointers are exposed; copied handles alias the same resource. */
typedef struct {
    int64_t id;
    int fd, closed, width, height, key, mouse_x, mouse_y;
    uint32_t xid, gc, pixmap, wm_delete, wm_protocols, net_name, utf8_string;
    uint32_t *pixels;
    unsigned char event[32]; size_t used;
    uint16_t max_request;
    uint8_t depth;
#if defined(_WIN32)
    HWND hwnd;
    struct {int kind,key,x,y;} queue[64];
    size_t queue_head,queue_count;
#endif
} KWindow;
static KWindow k_windows[16];
static int64_t k_next_window=INT64_C(4294967296);
static size_t k_window_bytes;
static KWindow *k_window(int64_t id) {
    for (size_t i=0;i<16;++i) if (id>0 && k_windows[i].id==id) return &k_windows[i];
    k_resource_trap();
}
static int64_t k_window_width(int64_t id) { return k_window(id)->width; }
static int64_t k_window_height(int64_t id) { return k_window(id)->height; }
static int64_t k_window_key(int64_t id) { return k_window(id)->key; }
static int64_t k_window_mouse_x(int64_t id) { return k_window(id)->mouse_x; }
static int64_t k_window_mouse_y(int64_t id) { return k_window(id)->mouse_y; }
static void k_window_set_pixel(int64_t id,int64_t x,int64_t y,int64_t rgb) {
    KWindow *w=k_window(id);
    if (x<0 || y<0 || x>=w->width || y>=w->height || rgb<0 || rgb>0xffffff) k_resource_trap();
    w->pixels[(size_t)y*(size_t)w->width+(size_t)x]=(uint32_t)rgb;
}
#if defined(_WIN32)
/* Single GUI thread, fixed per-window event queue, no callback enters Awl code.
 * Messages for all windows are dispatched together; each poll pops its own queue.
 * Overflow/unsupported resize/allocation failure closes the logical window. */
static void k_win_event(KWindow *w,int kind,int key,int x,int y) {
    if(w->closed) return;
    if(w->queue_count && (kind==2 || kind==3 || kind==6)) {
        size_t last=(w->queue_head+w->queue_count-1)%64;
        if(w->queue[last].kind==kind) {w->queue[last].key=key;w->queue[last].x=x;w->queue[last].y=y;return;}
    }
    if(w->queue_count==64) {w->closed=1;return;}
    size_t at=(w->queue_head+w->queue_count++)%64;
    w->queue[at].kind=kind;w->queue[at].key=key;w->queue[at].x=x;w->queue[at].y=y;
}
static int k_win_blit(KWindow *w,HDC dc) {
    BITMAPINFO info;memset(&info,0,sizeof(info));info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
    info.bmiHeader.biWidth=w->width;info.bmiHeader.biHeight=-w->height;
    info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
    int result=StretchDIBits(dc,0,0,w->width,w->height,0,0,w->width,w->height,w->pixels,&info,DIB_RGB_COLORS,SRCCOPY);
    return result!=0 && result!=-1;
}
static LRESULT CALLBACK k_win_proc(HWND hwnd,UINT message,WPARAM wp,LPARAM lp) {
    KWindow *w=(KWindow*)GetWindowLongPtrW(hwnd,GWLP_USERDATA);
    if(message==WM_NCCREATE) {
        w=(KWindow*)((CREATESTRUCTW*)lp)->lpCreateParams;
        if(!w) return FALSE;
        SetWindowLongPtrW(hwnd,GWLP_USERDATA,(LONG_PTR)w);w->hwnd=hwnd;
    }
    if(message==WM_GETMINMAXINFO){RECT r={0,0,2048,2048};
        if(AdjustWindowRectEx(&r,WS_OVERLAPPEDWINDOW,FALSE,0)) {MINMAXINFO *m=(MINMAXINFO*)lp;m->ptMaxTrackSize.x=r.right-r.left;m->ptMaxTrackSize.y=r.bottom-r.top;m->ptMinTrackSize.x=r.right-r.left-2048+1;m->ptMinTrackSize.y=r.bottom-r.top-2048+1;}
        return 0;}
    if(!w) return DefWindowProcW(hwnd,message,wp,lp);
    switch(message) {
    case WM_CLOSE:w->closed=1;return 0;
    case WM_DESTROY:w->closed=1;return 0;
    case WM_NCDESTROY:SetWindowLongPtrW(hwnd,GWLP_USERDATA,0);w->hwnd=NULL;return DefWindowProcW(hwnd,message,wp,lp);
    case WM_ERASEBKGND:return 1;
    case WM_PAINT:{PAINTSTRUCT paint;HDC dc=BeginPaint(hwnd,&paint);
        if(dc && w->pixels && !w->closed && !k_win_blit(w,dc)) w->closed=1;
        EndPaint(hwnd,&paint);k_win_event(w,2,0,0,0);return 0;}
    case WM_SIZE:{
        if(wp==SIZE_MINIMIZED || w->closed) return 0;
        int width=(int)(uint16_t)lp,height=(int)(uint16_t)((uintptr_t)lp>>16);
        k_win_event(w,3,0,width,height);return 0;}
    case WM_KEYDOWN:case WM_SYSKEYDOWN:case WM_KEYUP:case WM_SYSKEYUP:
        k_win_event(w,(message==WM_KEYDOWN || message==WM_SYSKEYDOWN)?4:5,(int)wp,0,0);
        if(message==WM_SYSKEYDOWN || message==WM_SYSKEYUP) return DefWindowProcW(hwnd,message,wp,lp);
        return 0;
    case WM_MOUSEMOVE:case WM_LBUTTONDOWN:case WM_LBUTTONUP:case WM_MBUTTONDOWN:case WM_MBUTTONUP:case WM_RBUTTONDOWN:case WM_RBUTTONUP:{
        int x=(int16_t)(uint16_t)lp,y=(int16_t)(uint16_t)((uintptr_t)lp>>16);
        int down=message==WM_LBUTTONDOWN || message==WM_MBUTTONDOWN || message==WM_RBUTTONDOWN;
        int up=message==WM_LBUTTONUP || message==WM_MBUTTONUP || message==WM_RBUTTONUP;
        int button=(message==WM_LBUTTONDOWN || message==WM_LBUTTONUP)?1:(message==WM_MBUTTONDOWN || message==WM_MBUTTONUP)?2:3;
        if(down) SetCapture(hwnd);if(up && GetCapture()==hwnd) ReleaseCapture();
        k_win_event(w,down?7:up?8:6,message==WM_MOUSEMOVE?0:button,x,y);return 0;}
    default:return DefWindowProcW(hwnd,message,wp,lp);
    }
}
static int k_win_class(void) {
    static ATOM atom;if(atom) return 1;
    WNDCLASSW type;memset(&type,0,sizeof(type));type.lpfnWndProc=k_win_proc;
    type.hInstance=GetModuleHandleW(NULL);type.lpszClassName=L"Awl.PixelWindow.v1";
    type.hCursor=LoadCursorW(NULL,MAKEINTRESOURCEW(32512));atom=RegisterClassW(&type);return atom!=0;
}
#endif
#if defined(__linux__)
static uint16_t k_x16(const unsigned char *p) { return (uint16_t)(p[0]|(uint16_t)p[1]<<8); }
static uint32_t k_x32(const unsigned char *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void k_put16(unsigned char *p,uint16_t n) { p[0]=(unsigned char)n; p[1]=(unsigned char)(n>>8); }
static void k_put32(unsigned char *p,uint32_t n) { for (unsigned i=0;i<4;++i) p[i]=(unsigned char)(n>>(8*i)); }
static int k_xwrite(int fd,const void *data,size_t size) {
    const unsigned char *p=data;
    while (size) {
        ssize_t n=send(fd,p,size,MSG_NOSIGNAL);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) return 0;
        p+=n; size-=(size_t)n;
    }
    return 1;
}
static int k_xread(int fd,void *data,size_t size) {
    unsigned char *p=data; int64_t deadline=k_clock_millis()+2500;
    while (size) {
        int64_t remaining=deadline-k_clock_millis();
        if (remaining<=0) return 0;
        struct pollfd f={fd,POLLIN,0};
        int r=poll(&f,1,(int)remaining);
        if (r<0 && errno==EINTR) continue;
        if (r<=0) return 0;
        ssize_t n=recv(fd,p,size,MSG_DONTWAIT);
        if (n<0 && (errno==EINTR || errno==EAGAIN)) continue;
        if (n<=0) return 0;
        p+=n; size-=(size_t)n;
    }
    return 1;
}
/* Xauthority fields are big-endian length-prefixed. Never read arbitrary-sized
 * fields, and only send MIT cookie credentials over the selected local socket. */
static int k_auth_field(FILE *f,unsigned char *out,size_t cap,size_t *len) {
    int a=fgetc(f), b=fgetc(f);
    if (a<0 || b<0) return 0;
    *len=(size_t)a*256+(size_t)b;
    if (*len>cap) return 0;
    return fread(out,1,*len,f)==*len;
}
static size_t k_xcookie(unsigned display,unsigned char cookie[16]) {
    char fallback[4096], number[32];
    const char *path=getenv("XAUTHORITY");
    if (!path || !*path) {
        const char *home=getenv("HOME"); if (!home) return 0;
        int n=snprintf(fallback,sizeof(fallback),"%s/.Xauthority",home);
        if (n<0 || (size_t)n>=sizeof(fallback)) return 0;
        path=fallback;
    }
    FILE *f=fopen(path,"rb"); if (!f) return 0;
    snprintf(number,sizeof(number),"%u",display);
    size_t result=0;
    for (unsigned records=0; records<1024; ++records) {
        int a=fgetc(f),b=fgetc(f); if (a<0 || b<0) break;
        unsigned family=(unsigned)a*256+(unsigned)b;
        unsigned char address[1024],num[128],name[128],data[1024];
        size_t al,nl,pl,dl;
        if (!k_auth_field(f,address,sizeof(address),&al) || !k_auth_field(f,num,sizeof(num),&nl) ||
            !k_auth_field(f,name,sizeof(name),&pl) || !k_auth_field(f,data,sizeof(data),&dl)) break;
        if ((family==256 || family==65535) && nl==strlen(number) && !memcmp(num,number,nl) &&
            pl==18 && !memcmp(name,"MIT-MAGIC-COOKIE-1",18) && dl==16) {
            memcpy(cookie,data,16); result=16; break;
        }
    }
    fclose(f); return result;
}
static uint32_t k_xatom(int fd,const char *name) {
    unsigned char request[128]={16,0}; size_t n=strlen(name),size=8+((n+3)&~(size_t)3);
    if (size>sizeof(request)) return 0;
    k_put16(request+2,(uint16_t)(size/4)); k_put16(request+4,(uint16_t)n); memcpy(request+8,name,n);
    unsigned char reply[32];
    if (!k_xwrite(fd,request,size) || !k_xread(fd,reply,32) || reply[0]!=1 || k_x32(reply+4)!=0) return 0;
    return k_x32(reply+8);
}
static int k_xproperty(int fd,uint32_t window,uint32_t property,uint32_t type,unsigned format,const void *data,size_t count) {
    unsigned char b[4096]={18,0}; size_t bytes=count*(format/8),size=24+((bytes+3)&~(size_t)3);
    if (size>sizeof(b)) return 0;
    k_put16(b+2,(uint16_t)(size/4)); k_put32(b+4,window); k_put32(b+8,property); k_put32(b+12,type);
    b[16]=(unsigned char)format; k_put32(b+20,(uint32_t)count); memcpy(b+24,data,bytes);
    return k_xwrite(fd,b,size);
}
static int k_xpixmap(KWindow *w,int width,int height,int replace) {
    if (replace) {
        unsigned char destroy[8]={54,0,2,0}; k_put32(destroy+4,w->pixmap);
        if (!k_xwrite(w->fd,destroy,8)) return 0;
    }
    unsigned char create[16]={53,0,4,0};create[1]=w->depth;
    k_put32(create+4,w->pixmap);k_put32(create+8,w->xid);
    k_put16(create+12,(uint16_t)width);k_put16(create+14,(uint16_t)height);
    return k_xwrite(w->fd,create,16);
}
static int k_xconnect(KWindow *w,int width,int height) {
    const char *display=getenv("DISPLAY"); if (!display) return 0;
    if (!strncmp(display,"unix:",5)) display+=4;
    if (*display++!=':') return 0;
    unsigned number=0,digits=0;
    while (*display>='0' && *display<='9') {number=number*10+(unsigned)(*display++-'0'); if (++digits>4 || number>4095) return 0;}
    if (!digits || (*display && strcmp(display,".0"))) return 0;
    int fd=socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0); if (fd<0) return 0;
    w->fd=fd;
    struct timeval timeout={2,0};
    if (setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout))) return 0;
    struct sockaddr_un address; memset(&address,0,sizeof(address)); address.sun_family=AF_UNIX;
    snprintf(address.sun_path,sizeof(address.sun_path),"/tmp/.X11-unix/X%u",number);
    if (connect(fd,(struct sockaddr *)&address,sizeof(address))) return 0;
    unsigned char hello[64]={'l',0,11,0},cookie[16]; size_t cookie_size=k_xcookie(number,cookie),hello_size=12;
    if (cookie_size) {
        k_put16(hello+6,18); k_put16(hello+8,16);
        memcpy(hello+12,"MIT-MAGIC-COOKIE-1",18); memcpy(hello+32,cookie,16); hello_size=48;
    }
    unsigned char h[8];
    if (!k_xwrite(fd,hello,hello_size) || !k_xread(fd,h,8) || h[0]!=1) return 0;
    size_t size=(size_t)k_x16(h+6)*4;
    if (size<32 || size>262140) return 0;
    unsigned char *setup=malloc(size); if (!setup) return 0;
    int ok=0;
    if (!k_xread(fd,setup,size)) goto done;
    uint32_t base=k_x32(setup+4),mask=k_x32(setup+8);
    size_t off=32+(((size_t)k_x16(setup+16)+3)&~(size_t)3),formats=setup[21];
    if (!setup[20] || setup[22]!=0 || (mask&3)!=3 || off>size || formats>(size-off)/8) goto done;
    size_t root=off+formats*8;
    if (root>size || size-root<40) goto done;
    uint8_t depth=setup[root+38]; int supported=0;
    if (depth!=24 && depth!=32) goto done;
    for (size_t i=0;i<formats;++i) if (setup[off+i*8]==depth && setup[off+i*8+1]==32 && setup[off+i*8+2]==32) supported=1;
    if (!supported) goto done;
    uint32_t visual=k_x32(setup+root+32); off=root+40; int truecolor=0;
    for (unsigned i=0;i<setup[root+39];++i) {
        if (off>size || size-off<8) goto done;
        size_t count=k_x16(setup+off+2); off+=8;
        if (count>(size-off)/24) goto done;
        for (size_t v=0;v<count;++v) {
            const unsigned char *p=setup+off+v*24;
            if (k_x32(p)==visual && p[4]==4 && k_x32(p+8)==0xff0000 && k_x32(p+12)==0xff00 && k_x32(p+16)==0xff) truecolor=1;
        }
        off+=count*24;
    }
    if (!truecolor) goto done;
    w->depth=depth; w->max_request=k_x16(setup+18);
    if ((size_t)width*4+24>(size_t)w->max_request*4) goto done;
    w->xid=base|1; w->gc=base|2; w->pixmap=base|3;
    w->wm_protocols=k_xatom(fd,"WM_PROTOCOLS"); w->wm_delete=k_xatom(fd,"WM_DELETE_WINDOW");
    w->net_name=k_xatom(fd,"_NET_WM_NAME");w->utf8_string=k_xatom(fd,"UTF8_STRING");
    if (!w->wm_protocols || !w->wm_delete || !w->net_name || !w->utf8_string) goto done;
    unsigned char create[40]={1,0};
    k_put16(create+2,10); k_put32(create+4,w->xid); k_put32(create+8,k_x32(setup+root));
    k_put16(create+16,(uint16_t)width); k_put16(create+18,(uint16_t)height); k_put16(create+22,1);
    k_put32(create+28,2|2048); k_put32(create+32,k_x32(setup+root+12));
    k_put32(create+36,1|2|4|8|64|32768|131072);
    unsigned char gc[16]={55,0,4,0}; k_put32(gc+4,w->gc); k_put32(gc+8,w->xid);
    unsigned char map[8]={8,0,2,0}; k_put32(map+4,w->xid);
    unsigned char atom[4]; k_put32(atom,w->wm_delete);
    if (!k_xwrite(fd,create,40) || !k_xwrite(fd,gc,16) || !k_xpixmap(w,width,height,0) ||
        !k_xproperty(fd,w->xid,39,31,8,"Awl native window",18) ||
        !k_xproperty(fd,w->xid,w->wm_protocols,4,32,atom,1) || !k_xwrite(fd,map,8)) goto done;
    ok=1;
done:
    free(setup); return ok;
}
#endif
static int64_t k_window_open(int64_t width,int64_t height) {
    if (width<1 || height<1 || width>2048 || height>2048 || k_next_window==INT64_C(4611686018427387904)) return 0;
    size_t bytes=(size_t)width*(size_t)height*4;
    if (bytes>K_BUFFER_TOTAL-k_window_bytes) return 0;
    for (size_t i=0;i<16;++i) if (!k_windows[i].id) {
#if defined(_WIN32)
        if(!k_win_class()) return 0;
        KWindow *slot=&k_windows[i];memset(slot,0,sizeof(*slot));
        slot->pixels=calloc(1,bytes);if(!slot->pixels) return 0;
        slot->width=(int)width;slot->height=(int)height;slot->id=k_next_window++;
        k_window_bytes+=bytes;
        RECT rect={0,0,(LONG)width,(LONG)height};
        if(!AdjustWindowRectEx(&rect,WS_OVERLAPPEDWINDOW,FALSE,0)) {k_window_bytes-=bytes;free(slot->pixels);memset(slot,0,sizeof(*slot));return 0;}
        HWND hwnd=CreateWindowExW(0,L"Awl.PixelWindow.v1",L"Awl native window",WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT,CW_USEDEFAULT,rect.right-rect.left,rect.bottom-rect.top,NULL,NULL,GetModuleHandleW(NULL),slot);
        if(!hwnd) {k_window_bytes-=bytes;free(slot->pixels);memset(slot,0,sizeof(*slot));return 0;}
        ShowWindow(hwnd,SW_SHOWNORMAL);return slot->id;
#else
        KWindow w; memset(&w,0,sizeof(w)); w.fd=-1;
#if defined(__linux__)
        if (!k_xconnect(&w,(int)width,(int)height)) {if (w.fd>=0) close(w.fd); return 0;}
#else
        return 0;
#endif
        w.pixels=calloc(1,bytes);
        if (!w.pixels) {
#if defined(__linux__)
            close(w.fd);
#endif
            return 0;
        }
        w.width=(int)width; w.height=(int)height; w.id=k_next_window++;
        k_windows[i]=w; k_window_bytes+=bytes; return w.id;
#endif
    }
    return 0;
}
static bool k_window_present(int64_t id) {
    KWindow *w=k_window(id); if (w->closed) return false;
#if defined(__linux__)
    unsigned char packet[24+2048*4];
    size_t size=24+(size_t)w->width*4;
    if (size>(size_t)w->max_request*4) {w->closed=1;return false;}
    for (int y=0;y<w->height;++y) {
        memset(packet,0,24); packet[0]=72; packet[1]=2;
        k_put16(packet+2,(uint16_t)(size/4)); k_put32(packet+4,w->pixmap); k_put32(packet+8,w->gc);
        k_put16(packet+12,(uint16_t)w->width); k_put16(packet+14,1); k_put16(packet+18,(uint16_t)y); packet[21]=w->depth;
        memcpy(packet+24,w->pixels+(size_t)y*(size_t)w->width,(size_t)w->width*4);
        if (!k_xwrite(w->fd,packet,size)) {w->closed=1;return false;}
    }
    unsigned char copy[28]={62,0,7,0};
    k_put32(copy+4,w->pixmap);k_put32(copy+8,w->xid);k_put32(copy+12,w->gc);
    k_put16(copy+24,(uint16_t)w->width);k_put16(copy+26,(uint16_t)w->height);
    if (!k_xwrite(w->fd,copy,28)) {w->closed=1;return false;}
    return true;
#elif defined(_WIN32)
    if(!w->hwnd || !IsWindow(w->hwnd)) {w->closed=1;return false;}
    if(IsIconic(w->hwnd)) return true;
    HDC dc=GetDC(w->hwnd);if(!dc) {w->closed=1;return false;}
    int ok=k_win_blit(w,dc);ReleaseDC(w->hwnd,dc);if(!ok) w->closed=1;return ok!=0;
#else
    return false;
#endif
}
/* Events: 0 none, 1 close/disconnect, 2 expose, 3 resize, 4/5 key down/up,
 * 6 pointer motion, 7/8 button down/up. Key values: X11 physical keycodes on Linux, virtual-key codes on Windows.
 * Poll consumes ONE event; callers should drain until 0 before drawing. */
static int64_t k_window_poll(int64_t id) {
    KWindow *w=k_window(id); if (w->closed) return 1;
#if defined(__linux__)
    for (unsigned skipped=0;skipped<1024;++skipped) {
        while (w->used<32) {
            ssize_t n=recv(w->fd,w->event+w->used,32-w->used,MSG_DONTWAIT);
            if (n<0 && errno==EINTR) continue;
            if (n<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) return 0;
            if (n<=0) {w->closed=1;return 1;}
            w->used+=(size_t)n;
        }
        unsigned char *e=w->event; unsigned type=e[0]&127; w->used=0;
        if (type==0 || type==35 || (type==1 && k_x32(e+4)!=0)) {w->closed=1;return 1;}
        if (type==17 || (type==33 && e[1]==32 && k_x32(e+8)==w->wm_protocols && k_x32(e+12)==w->wm_delete)) {w->closed=1;return 1;}
        if (type==12) return 2;
        if (type==22) {
            int width=k_x16(e+20),height=k_x16(e+22);
            if (width==w->width && height==w->height) continue;
            if (width<1 || height<1 || width>2048 || height>2048) {w->closed=1;return 1;}
            size_t bytes=(size_t)width*(size_t)height*4,old=(size_t)w->width*(size_t)w->height*4;
            if (bytes>K_BUFFER_TOTAL-(k_window_bytes-old)) {w->closed=1;return 1;}
            uint32_t *pixels=calloc(1,bytes); if (!pixels) {w->closed=1;return 1;}
            free(w->pixels); w->pixels=pixels; w->width=width; w->height=height;
            k_window_bytes=k_window_bytes-old+bytes;
            if (!k_xpixmap(w,width,height,1)) {w->closed=1;return 1;}
            return 3;
        }
        if (type>=2 && type<=6) {
            w->mouse_x=(int16_t)k_x16(e+24); w->mouse_y=(int16_t)k_x16(e+26); w->key=e[1];
            if (type==2) return 4;
            if (type==3) return 5;
            if (type==4) return 7;
            if (type==5) return 8;
            return 6;
        }
    }
#elif defined(_WIN32)
    MSG message;
    for(unsigned dispatched=0;dispatched<1024 && PeekMessageW(&message,NULL,0,0,PM_REMOVE);++dispatched) {
        if(message.message==WM_QUIT) {for(size_t i=0;i<16;++i) if(k_windows[i].id) k_windows[i].closed=1;break;}
        TranslateMessage(&message);DispatchMessageW(&message);
    }
    if(w->closed) return 1;
    while(w->queue_count) {
        size_t at=w->queue_head;int kind=w->queue[at].kind,key=w->queue[at].key,x=w->queue[at].x,y=w->queue[at].y;
        w->queue_head=(at+1)%64;--w->queue_count;
        if(kind==3) {
            if(x==w->width && y==w->height) continue;
            if(x<1 || y<1 || x>2048 || y>2048) {w->closed=1;return 1;}
            size_t bytes=(size_t)x*(size_t)y*4,old=(size_t)w->width*(size_t)w->height*4;
            if(bytes>K_BUFFER_TOTAL-(k_window_bytes-old)) {w->closed=1;return 1;}
            uint32_t *pixels=calloc(1,bytes);if(!pixels) {w->closed=1;return 1;}
            free(w->pixels);w->pixels=pixels;w->width=x;w->height=y;k_window_bytes=k_window_bytes-old+bytes;
        }
        if(kind>=4) {w->key=key;if(kind>=6) {w->mouse_x=x;w->mouse_y=y;}}
        return kind;
    }

#endif
    return 0;
}
static void k_window_close(int64_t id) {
    KWindow *w=k_window(id);
#if defined(__linux__)
    /* Connection teardown destroys server-side window/GC even on error. */
    close(w->fd);
#elif defined(_WIN32)
    if(w->hwnd && !DestroyWindow(w->hwnd)) k_resource_trap();
#endif
    k_window_bytes-=(size_t)w->width*(size_t)w->height*4;
    free(w->pixels); memset(w,0,sizeof(*w));
}

#ifdef Awl_STRINGS_RUNTIME
static unsigned char *k_buffer_text_range(int64_t buffer,int64_t offset,int64_t count) {
    KBuffer *b=k_buffer(buffer);if(offset<0 || count<0 || (uint64_t)offset>b->size || (uint64_t)count>b->size-(size_t)offset) k_resource_trap();return b->data+(size_t)offset;
}
static bool k_buffer_text_valid(int64_t buffer,int64_t offset,int64_t count) {
    unsigned char *data=k_buffer_text_range(buffer,offset,count);size_t scalars=0;return k_utf8_scan(data,(size_t)count,&scalars);
}
static KString k_buffer_text(int64_t buffer,int64_t offset,int64_t count) {
    unsigned char *data=k_buffer_text_range(buffer,offset,count);size_t scalars=0;if(!k_utf8_scan(data,(size_t)count,&scalars)) k_resource_trap();
    unsigned char *copy=k_string_allocate((size_t)count);memcpy(copy,data,(size_t)count);return (KString){copy,(size_t)count,scalars};
}
static int64_t k_buffer_write_text(int64_t buffer,int64_t offset,KString text) {
    KBuffer *b=k_buffer(buffer);if(offset<0 || (uint64_t)offset>b->size) k_resource_trap();
    if(text.bytes>b->size-(size_t)offset) return -5;
    memcpy(b->data+(size_t)offset,text.data,text.bytes);return (int64_t)text.bytes;
}
static bool k_window_set_title(int64_t id,KString title) {
    KWindow *w=k_window(id);
    if(w->closed||title.bytes>1024||(title.bytes&&memchr(title.data,0,title.bytes))) return false;
#if defined(__linux__)
    if(24+((title.bytes+3)&~(size_t)3)>(size_t)w->max_request*4) return false;
    if(!k_xproperty(w->fd,w->xid,w->net_name,w->utf8_string,8,title.data,title.bytes) ||
       !k_xproperty(w->fd,w->xid,39,31,8,title.data,title.bytes)) {w->closed=1;return false;}
    return true;
#elif defined(_WIN32)
    if(!w->hwnd) return false;
    wchar_t text[1025];int count=0;
    if(title.bytes) {count=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,(const char*)title.data,(int)title.bytes,text,1024);if(!count) return false;}
    text[count]=0;return SetWindowTextW(w->hwnd,text)!=0;

#else
    return false;
#endif
}
#endif
