/* External native Win32 controller/capture for the Awl Pixelboard application.
 * Sends programmatic input, validates real GDI pixels; no renderer lives here. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <wchar.h>
#include <stdio.h>
#include <stdlib.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
static HWND find(void){return FindWindowW(L"Awl.PixelWindow.v1",L"Awl Pixelboard | S: save new | L: load | other key: clear | right: color");}
static COLORREF pixel(HWND w,int x,int y){HDC dc=GetDC(w);COLORREF c=GetPixel(dc,x,y);ReleaseDC(w,dc);return c;}
static COLORREF rgb(int value){return RGB(value>>16&255,value>>8&255,value&255);}
static void wait_pixel(HWND w,int x,int y,COLORREF expected){for(int i=0;i<1000;++i){if(pixel(w,x,y)==expected)return;Sleep(10);}fprintf(stderr,"pixel mismatch at %d,%d: %lx vs %lx\n",x,y,(unsigned long)pixel(w,x,y),(unsigned long)expected);assert(0);}
static void capture(HWND w,const wchar_t *path){
 RECT r;assert(GetWindowRect(w,&r));int width=r.right-r.left,height=r.bottom-r.top;HDC source=GetWindowDC(w),memory=CreateCompatibleDC(source);assert(source&&memory);HBITMAP bitmap=CreateCompatibleBitmap(source,width,height);assert(bitmap);HGDIOBJ old=SelectObject(memory,bitmap);assert(BitBlt(memory,0,0,width,height,source,0,0,SRCCOPY));SelectObject(memory,old);
 BITMAPINFO info={0};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=width;info.bmiHeader.biHeight=-height;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
 DWORD bytes=(DWORD)width*(DWORD)height*4;unsigned char *data=malloc(bytes);assert(data&&GetDIBits(memory,bitmap,0,height,data,&info,DIB_RGB_COLORS)==height);
 BITMAPFILEHEADER header={0};header.bfType=0x4d42;header.bfOffBits=sizeof(header)+sizeof(info.bmiHeader);header.bfSize=header.bfOffBits+bytes;HANDLE file=CreateFileW(path,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);assert(file!=INVALID_HANDLE_VALUE);DWORD n;assert(WriteFile(file,&header,sizeof(header),&n,NULL)&&n==sizeof(header));assert(WriteFile(file,&info.bmiHeader,sizeof(info.bmiHeader),&n,NULL)&&n==sizeof(info.bmiHeader));assert(WriteFile(file,data,bytes,&n,NULL)&&n==bytes);CloseHandle(file);free(data);DeleteObject(bitmap);DeleteDC(memory);ReleaseDC(w,source);
}
static void key(HWND w,int code){SendMessageW(w,WM_KEYDOWN,code,0);SendMessageW(w,WM_KEYUP,code,0);}
static void title(HWND w,const wchar_t *needle){for(int i=0;i<1000;++i){wchar_t s[256];GetWindowTextW(w,s,256);if(wcsstr(s,needle))return;Sleep(10);}assert(!"status title did not arrive");}
int wmain(int argc,wchar_t **argv){
 assert(argc==3||argc==4);HWND w=NULL;for(int i=0;i<1000&&!w;++i){w=find();if(!w)Sleep(10);}assert(w);SetForegroundWindow(w);
 const char *letters[4][7]={{"10001","10010","10100","11000","10100","10010","10001"},{"11111","10000","10000","11110","10000","10000","11111"},{"11110","10001","10001","11110","10100","10010","10001"},{"10001","11001","11001","10101","10011","10011","10001"}};
 const int colors[]={2217134,7695615,16217750,16764784};
 if(argc==4){
  key(w,'L');title(w,L"Loaded file");for(int i=0;i<4;++i)wait_pixel(w,i*180+15,135,rgb(colors[i]));puts("PASS actual Awl reload restores four colors across process restart");
  key(w,'S');title(w,L"Saved new file");assert(GetFileAttributesW(argv[2])!=INVALID_FILE_ATTRIBUTES);puts("PASS actual Awl save-as from persisted drawing");
  key(w,'L');title(w,L"Loaded file");capture(w,argv[1]);SendMessageW(w,WM_CLOSE,0,0);return 0;
 }
 wait_pixel(w,15,135,rgb(1056816+263688));
 for(int letter=0;letter<4;++letter){if(letter){SendMessageW(w,WM_RBUTTONDOWN,0,MAKELPARAM(15,15));SendMessageW(w,WM_RBUTTONUP,0,MAKELPARAM(15,15));Sleep(30);}for(int row=0;row<7;++row)for(int col=0;col<5;++col)if(letters[letter][row][col]=='1'){
   int x=(letter*6+col)*30+15,y=(row+4)*30+15;SendMessageW(w,WM_LBUTTONDOWN,0,MAKELPARAM(x,y));SendMessageW(w,WM_LBUTTONUP,0,MAKELPARAM(x,y));Sleep(25);
  }
  wait_pixel(w,(letter*6)*30+15,135,rgb(colors[letter]));
 }
 puts("PASS actual Awl vector-backed paint, four brush colors, GDI pixels");fflush(stdout);
 key(w,'S');title(w,L"Saved new file");assert(GetFileAttributesW(argv[2])!=INVALID_FILE_ATTRIBUTES);puts("PASS actual Awl exclusive save");
 key(w,VK_SPACE);wait_pixel(w,15,135,rgb(1320504));key(w,'L');title(w,L"Loaded file");wait_pixel(w,15,135,rgb(colors[0]));puts("PASS actual Awl load restores cleared pixels");
 key(w,'S');title(w,L"Save refused");puts("PASS actual Awl refuses overwrite");
 key(w,'L');title(w,L"Loaded file");capture(w,argv[1]);
 RECT r={0,0,480,320};assert(AdjustWindowRectEx(&r,WS_OVERLAPPEDWINDOW,FALSE,0));assert(SetWindowPos(w,NULL,0,0,r.right-r.left,r.bottom-r.top,SWP_NOMOVE|SWP_NOZORDER));wait_pixel(w,10,90,rgb(colors[0]));puts("PASS actual Awl resize redraw preserves vector canvas");
 SendMessageW(w,WM_KEYDOWN,VK_SPACE,0);SendMessageW(w,WM_KEYUP,VK_SPACE,0);wait_pixel(w,10,90,rgb(1056816+263688));puts("PASS actual Awl keyboard clear");
 SendMessageW(w,WM_CLOSE,0,0);puts("PASS native close request sent");return 0;
}
