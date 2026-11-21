"""Launch the installed app, inspect its own windows/API and capture the client area."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import time
import urllib.request
import zlib

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/ui_overhaul_20261024'
EXE=Path.home()/'AppData/Local/Programs/Linda-Pro/Linda-Pro.exe'
BUILD=Path.home()/'Desktop/Linda_2.3.0.0/app'
u=c.WinDLL('user32',use_last_error=True);g=c.WinDLL('gdi32',use_last_error=True)
u.GetDC.argtypes=[w.HWND];u.GetDC.restype=w.HDC
u.ReleaseDC.argtypes=[w.HWND,w.HDC]
u.GetClientRect.argtypes=[w.HWND,c.POINTER(w.RECT)]
u.ClientToScreen.argtypes=[w.HWND,c.POINTER(w.POINT)]
u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
u.IsWindowVisible.argtypes=[w.HWND]
u.ShowWindow.argtypes=[w.HWND,c.c_int]
u.SetForegroundWindow.argtypes=[w.HWND]
u.PrintWindow.argtypes=[w.HWND,w.HDC,w.UINT]
u.PrintWindow.restype=w.BOOL
g.CreateCompatibleDC.argtypes=[w.HDC];g.CreateCompatibleDC.restype=w.HDC
g.CreateCompatibleBitmap.argtypes=[w.HDC,c.c_int,c.c_int];g.CreateCompatibleBitmap.restype=w.HBITMAP
g.SelectObject.argtypes=[w.HDC,w.HGDIOBJ];g.SelectObject.restype=w.HGDIOBJ
g.BitBlt.argtypes=[w.HDC,c.c_int,c.c_int,c.c_int,c.c_int,w.HDC,c.c_int,c.c_int,w.DWORD]
g.GetDIBits.argtypes=[w.HDC,w.HBITMAP,w.UINT,w.UINT,c.c_void_p,c.c_void_p,w.UINT]
g.DeleteObject.argtypes=[w.HGDIOBJ];g.DeleteDC.argtypes=[w.HDC]
CB=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
u.EnumWindows.argtypes=[CB,w.LPARAM]

def windows(pid):
    found=[]
    @CB
    def each(hwnd,_):
        owner=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(owner))
        if owner.value==pid and u.IsWindowVisible(hwnd):
            title=c.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
            rc=w.RECT();u.GetClientRect(hwnd,c.byref(rc))
            found.append((hwnd,title.value,rc.right,rc.bottom))
        return True
    u.EnumWindows(each,0)
    return found

def capture(hwnd,file,width,height,desktop=False,print_window=False):
    point=w.POINT(0,0)
    if desktop:u.ClientToScreen(hwnd,c.byref(point))
    dc=u.GetDC(None if desktop else hwnd);mem=g.CreateCompatibleDC(dc)
    bitmap=g.CreateCompatibleBitmap(dc,width,height);old=g.SelectObject(mem,bitmap)
    try:
        if print_window:
            assert u.PrintWindow(hwnd,mem,3)
        else:
            assert g.BitBlt(mem,0,0,width,height,dc,point.x,point.y,0x00CC0020)
        g.SelectObject(mem,old)
        header=c.create_string_buffer(struct.pack('<IiiHHIIiiII',40,width,-height,1,32,0,width*height*4,0,0,0,0))
        pixels=c.create_string_buffer(width*height*4)
        assert g.GetDIBits(mem,bitmap,0,height,pixels,header,0)==height
        raw=pixels.raw;rows=[]
        for y in range(height):
            row=raw[y*width*4:(y+1)*width*4];rgb=bytearray(width*3)
            rgb[0::3],rgb[1::3],rgb[2::3]=row[2::4],row[1::4],row[0::4];rows.append(b'\0'+rgb)
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        file.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b''))
    finally:
        g.SelectObject(mem,old);g.DeleteObject(bitmap);g.DeleteDC(mem);u.ReleaseDC(None if desktop else hwnd,dc)

def main():
    assert hashlib.sha256(EXE.read_bytes()).digest()==hashlib.sha256((BUILD/'Linda-Pro.exe').read_bytes()).digest()
    for name in ['index.html','cabinet.html','desktop-shell.css','desktop-shell.js','metro-dev.css']:
        assert (ROOT/'web'/name).read_bytes()==(EXE.parent/'_internal/web'/name).read_bytes(),name
    process=subprocess.Popen([str(EXE)])
    start=time.monotonic();splash=False
    while time.monotonic()-start<180:
        for hwnd,title,width,height in windows(process.pid):
            if title=='Linda' and not splash:
                capture(hwnd,OUT/'native-splash.png',width,height);splash=True
            if title=='Linda 2.3.0.0':
                time.sleep(2)
                u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd);time.sleep(.6)
                capture(hwnd,OUT/'native-main.png',width,height,print_window=True)
                instance=json.loads((Path.home()/'AppData/Local/Linda-Pro/instance.json').read_text())
                assert instance['pid']==process.pid
                base=f'http://127.0.0.1:{instance["port"]}'
                html=urllib.request.urlopen(base+'/',timeout=5).read().decode()
                assert all(marker in html for marker in ['desktopWorkspace','desktopTask','ld-settings-layout','Paste from clipboard'])
                token=re.search(r'''window\.__lindaToken\s*=\s*['"]([^'"]+)''',html)[1]
                req=urllib.request.Request(base+'/api/status',headers={'x-linda-token':token})
                status=json.loads(urllib.request.urlopen(req,timeout=5).read())
                result={'pid':process.pid,'title':title,'client_width':width,'client_height':height,'splash_seen':splash,'main_after_s':time.monotonic()-start,'desktop_workspace_in_real_response':True,'license_licensed':bool(status['license'].get('licensed')),'startup':status.get('startup'),'models_ready':status.get('models_ready'),'installed_resources_match':True,'installed_exe_matches':True}
                (OUT/'native-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
                print(json.dumps(result));return
        if process.poll() is not None:raise RuntimeError(f'App exited: {process.returncode}')
        time.sleep(.05)
    raise RuntimeError('Main window did not appear')

if __name__=='__main__':main()
