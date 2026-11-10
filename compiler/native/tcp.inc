// generated from ktcp.c
constexpr char c_tcp[]=R"KTCP(#if defined(__linux__)
#include <netinet/in.h>
#include <fcntl.h>
#endif
#define K_TCP_BASE INT64_C(2305843009213693952)
typedef struct {int64_t id;int fd;bool listener;} KTcp;
static KTcp k_tcp_slots[32];
static int64_t k_tcp_next=K_TCP_BASE;
#if defined(__linux__)
static bool k_tcp_registered;
#endif
static KTcp *k_tcp_require(int64_t id) {
    for(size_t i=0;i<32;++i) if(id>=K_TCP_BASE&&k_tcp_slots[i].id==id) return &k_tcp_slots[i];
    k_resource_trap();
}
static bool k_tcp_valid(int64_t id) {
    for(size_t i=0;i<32;++i) if(id>=K_TCP_BASE&&k_tcp_slots[i].id==id) return true;
    return false;
}
static void k_tcp_cleanup(void) {
#if defined(__linux__)
    for(size_t i=0;i<32;++i) if(k_tcp_slots[i].id) {close(k_tcp_slots[i].fd);k_tcp_slots[i]=(KTcp){0};}
#endif
}
static KTcp *k_tcp_empty(void) {
    if(k_tcp_next>=INT64_C(4611686018427387904)) return NULL;
    for(size_t i=0;i<32;++i) if(!k_tcp_slots[i].id) return &k_tcp_slots[i];
    return NULL;
}
static int64_t k_tcp_error(void) {
#if defined(__linux__)
    switch(errno) {
    case EADDRINUSE:return -3;
    case EACCES:case EPERM:return -4;
    case EINVAL:return -5;
    case EMFILE:case ENFILE:return -7;
    case ENOBUFS:case ENOMEM:return -9;
    case EAGAIN:case ETIMEDOUT:return -10;
    case EPIPE:case ECONNRESET:case ENOTCONN:return -11;
    default:return -1;
    }
#else
    return -6;
#endif
}
static bool k_tcp_timeout(int64_t ms) {return ms>=0&&ms<=3600000;}
#if defined(__linux__)
static int64_t k_tcp_wait(int fd,short events,int64_t deadline) {
    for(;;) {
        int64_t left=deadline-k_clock_millis();if(left<=0) return -10;
        struct pollfd p={fd,events,0};int n=poll(&p,1,(int)left);
        if(n>0) return (p.revents&POLLNVAL)?-1:0;
        if(n==0) return -10;
        if(errno!=EINTR) return k_tcp_error();
    }
}
#endif
static int64_t k_tcp_listen_loopback(int64_t port,int64_t backlog) {
    if(port<0||port>65535||backlog<1||backlog>128) return -5;
#if defined(__linux__)
    KTcp *slot=k_tcp_empty();if(!slot) return -7;
    if(!k_tcp_registered) {if(atexit(k_tcp_cleanup)) return -9;k_tcp_registered=true;}
    int fd=socket(AF_INET,SOCK_STREAM|SOCK_NONBLOCK|SOCK_CLOEXEC,0);if(fd<0) return k_tcp_error();
    struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);address.sin_port=htons((uint16_t)port);
    if(bind(fd,(struct sockaddr *)&address,sizeof(address))||listen(fd,(int)backlog)) {int64_t error=k_tcp_error();close(fd);return error;}
    *slot=(KTcp){k_tcp_next++,fd,true};return slot->id;
#else
    return -6;
#endif
}
static int64_t k_tcp_port(int64_t id) {
    KTcp *slot=k_tcp_require(id);if(!slot->listener) return -5;
#if defined(__linux__)
    struct sockaddr_in address={0};socklen_t size=sizeof(address);
    if(getsockname(slot->fd,(struct sockaddr *)&address,&size)) return k_tcp_error();
    return (int64_t)ntohs(address.sin_port);
#else
    return -6;
#endif
}
static int64_t k_tcp_accept(int64_t id,int64_t ms) {
    KTcp *listener=k_tcp_require(id);if(!listener->listener||!k_tcp_timeout(ms)) return -5;
#if defined(__linux__)
    KTcp *slot=k_tcp_empty();if(!slot) return -7;
    int64_t deadline=k_clock_millis()+ms;
    for(;;) {
        int fd=accept4(listener->fd,NULL,NULL,SOCK_NONBLOCK|SOCK_CLOEXEC);
        if(fd>=0) {*slot=(KTcp){k_tcp_next++,fd,false};return slot->id;}
        if(errno!=EAGAIN&&errno!=EWOULDBLOCK&&errno!=EINTR) return k_tcp_error();
        int64_t error=k_tcp_wait(listener->fd,POLLIN,deadline);if(error) return error;
    }
#else
    return -6;
#endif
}
static int64_t k_tcp_transfer(int64_t id,int64_t buffer,int64_t offset,int64_t count,int64_t ms,bool writing) {
    KTcp *slot=k_tcp_require(id);KBuffer *b=k_buffer(buffer);
    if(offset<0||count<0||(uint64_t)offset>b->size||(uint64_t)count>b->size-(size_t)offset) k_resource_trap();
    if(slot->listener||!k_tcp_timeout(ms)) return -5;
    if(!count) return 0;
#if defined(__linux__)
    int64_t deadline=k_clock_millis()+ms;
    for(;;) {
        ssize_t n=writing?send(slot->fd,b->data+(size_t)offset,(size_t)count,MSG_NOSIGNAL):recv(slot->fd,b->data+(size_t)offset,(size_t)count,0);
        if(n>=0) return (int64_t)n;
        if(errno!=EAGAIN&&errno!=EWOULDBLOCK&&errno!=EINTR) return k_tcp_error();
        int64_t error=k_tcp_wait(slot->fd,writing?POLLOUT:POLLIN,deadline);if(error) return error;
    }
#else
    (void)writing;return -6;
#endif
}
static int64_t k_tcp_read(int64_t id,int64_t buffer,int64_t offset,int64_t count,int64_t ms) {return k_tcp_transfer(id,buffer,offset,count,ms,false);}
static int64_t k_tcp_write(int64_t id,int64_t buffer,int64_t offset,int64_t count,int64_t ms) {return k_tcp_transfer(id,buffer,offset,count,ms,true);}
static int64_t k_tcp_close(int64_t id) {
    KTcp *slot=k_tcp_require(id);
#if defined(__linux__)
    int result=close(slot->fd);*slot=(KTcp){0};return result?k_tcp_error():0;
#else
    (void)slot;return -6;
#endif
}
)KTCP";
