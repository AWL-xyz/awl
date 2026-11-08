#define _GNU_SOURCE 1
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <poll.h>
#include <assert.h>
typedef struct {size_t size;unsigned char *data;} KBuffer;
static unsigned char bytes[16];
static KBuffer buffer={16,bytes};
static KBuffer *k_buffer(int64_t id) {assert(id==1);return &buffer;}
static _Noreturn void k_resource_trap(void) {abort();}
static int64_t now;
static int64_t k_clock_millis(void) {return now;}
static int mode,reads,polls,sends,closed,last_fd;
static int timeouts[16];
static ssize_t fault_recv(int fd,void *data,size_t size,int flags) {
    ++reads;
    if(mode==1&&reads==1) {now+=5;errno=EINTR;return -1;}
    if(mode==1) {assert(size>=3);memcpy(data,"abc",3);return 3;}
    if(mode==2) {errno=EAGAIN;return -1;}
    return recv(fd,data,size,flags);
}
static int fault_poll(struct pollfd *p,nfds_t n,int ms) {
    assert(n==1&&polls<16);timeouts[polls++]=ms;
    if(mode==1&&polls==1) {now+=7;errno=EINTR;return -1;}
    if(mode==1) {now+=3;p->revents=POLLIN;return 1;}
    if(mode==2) {now+=5;errno=EINTR;return -1;}
    return poll(p,n,ms);
}
static ssize_t fault_send(int fd,const void *data,size_t size,int flags) {
    ++sends;assert(flags&MSG_NOSIGNAL);
    if(mode==3) {assert(data==bytes+4&&size==3);return 2;}
    return send(fd,data,size,flags);
}
static int fault_close(int fd) {
    ++closed;int result=close(fd);
    if(mode==4) {errno=EINTR;return -1;}
    return result;
}
static int fault_bind(int fd,const struct sockaddr *address,socklen_t size) {
    if(mode==5) {last_fd=fd;errno=EADDRINUSE;return -1;}
    return bind(fd,address,size);
}
#define recv fault_recv
#define send fault_send
#define poll fault_poll
#define close fault_close
#define bind fault_bind
#include "../compiler/native/ktcp.c"
#undef recv
#undef send
#undef poll
#undef close
#undef bind
int main(void) {
    int pair[2];assert(!socketpair(AF_UNIX,SOCK_STREAM|SOCK_NONBLOCK|SOCK_CLOEXEC,0,pair));
    k_tcp_slots[0]=(KTcp){K_TCP_BASE,pair[0],false};
    mode=1;assert(k_tcp_read(K_TCP_BASE,1,2,3,20)==3);assert(!memcmp(bytes+2,"abc",3));assert(reads==2&&polls==2&&timeouts[0]==15&&timeouts[1]==8&&now==15);
    mode=2;now=0;polls=0;reads=0;assert(k_tcp_read(K_TCP_BASE,1,0,1,20)==-10);assert(now==20&&polls==4&&timeouts[0]==20&&timeouts[3]==5);
    mode=3;assert(k_tcp_write(K_TCP_BASE,1,4,3,0)==2);assert(sends==1);
    mode=0;close(pair[1]);struct sigaction before,after;assert(!sigaction(SIGPIPE,NULL,&before));assert(k_tcp_write(K_TCP_BASE,1,0,1,0)==-11);assert(!sigaction(SIGPIPE,NULL,&after));assert(before.sa_handler==after.sa_handler);
    mode=4;int old=pair[0];assert(k_tcp_close(K_TCP_BASE)==-1);assert(!k_tcp_valid(K_TCP_BASE)&&closed==1);assert(fcntl(old,F_GETFD)==-1&&errno==EBADF);
    mode=5;int previous=closed;int64_t next=k_tcp_next;assert(k_tcp_listen_loopback(0,1)==-3);assert(closed==previous+1&&k_tcp_next==next);assert(fcntl(last_fd,F_GETFD)==-1&&errno==EBADF);
    mode=0;int64_t listener=k_tcp_listen_loopback(0,1);assert(listener>=K_TCP_BASE);KTcp *slot=k_tcp_require(listener);assert((fcntl(slot->fd,F_GETFL)&O_NONBLOCK)&&(fcntl(slot->fd,F_GETFD)&FD_CLOEXEC));
    assert(k_tcp_accept(listener,0)==-10);
    int peer=socket(AF_INET,SOCK_STREAM,0);assert(peer>=0);struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);address.sin_port=htons((uint16_t)k_tcp_port(listener));assert(!connect(peer,(struct sockaddr *)&address,sizeof(address)));
    int64_t accepted=k_tcp_accept(listener,0);assert(accepted>=K_TCP_BASE);KTcp *connection=k_tcp_require(accepted);assert((fcntl(connection->fd,F_GETFL)&O_NONBLOCK)&&(fcntl(connection->fd,F_GETFD)&FD_CLOEXEC));assert(!k_tcp_close(accepted));close(peer);
    assert(k_tcp_accept(listener,0)==-10);assert(k_tcp_accept(listener,-1)==-5);assert(k_tcp_read(listener,1,0,0,0)==-5);assert(!k_tcp_close(listener));
    k_tcp_next=INT64_C(4611686018427387904);assert(k_tcp_listen_loopback(0,1)==-7);
    puts("PASS EINTR absolute deadlines, partial transfer, per-call SIGPIPE, close EINTR, bind rollback, fd flags, id exhaustion");return 0;
}
