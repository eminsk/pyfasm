import sys
import subprocess
import time
import ctypes
from ctypes import wintypes
import struct

exe_path = sys.argv[1] if len(sys.argv) > 1 else r'C:\proekts\0122\main.exe'
out_bmp = sys.argv[2] if len(sys.argv) > 2 else r'C:\Users\M_N_N\.gemini\antigravity\brain\53126218-a3a6-4583-a129-b9581ebecf5b\so_0122_native.bmp'

p = subprocess.Popen([exe_path])
time.sleep(2.0)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

target_hwnd = None
def enum_windows_callback(hwnd, lParam):
    global target_hwnd
    if user32.IsWindowVisible(hwnd):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == p.pid:
            target_hwnd = hwnd
            return False
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

if target_hwnd:
    print('Found HWND:', target_hwnd)
    rect = wintypes.RECT()
    user32.GetWindowRect(target_hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hwnd_dc = user32.GetDC(target_hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    hbitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    old_bmp = gdi32.SelectObject(mem_dc, hbitmap)

    res = user32.PrintWindow(target_hwnd, mem_dc, 2)

    bmi = bytearray(40)
    ctypes.c_int32.from_buffer(bmi, 0).value = 40
    ctypes.c_int32.from_buffer(bmi, 4).value = w
    ctypes.c_int32.from_buffer(bmi, 8).value = -h
    ctypes.c_int16.from_buffer(bmi, 12).value = 1
    ctypes.c_int16.from_buffer(bmi, 14).value = 32
    ctypes.c_int32.from_buffer(bmi, 16).value = 0

    raw_buf = bytearray(w * h * 4)
    gdi32.GetDIBits(mem_dc, hbitmap, 0, h, (ctypes.c_char * len(raw_buf)).from_buffer(raw_buf), (ctypes.c_char * 40).from_buffer(bmi), 0)

    file_size = 54 + len(raw_buf)
    file_header = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, 54)
    stride = w * 4
    bottom_up_data = bytearray(len(raw_buf))
    for row in range(h):
        src_offset = row * stride
        dst_offset = (h - 1 - row) * stride
        bottom_up_data[dst_offset:dst_offset + stride] = raw_buf[src_offset:src_offset + stride]

    info_header = struct.pack('<IIIHHIIIIII', 40, w, h, 1, 32, 0, len(raw_buf), 2835, 2835, 0, 0)

    with open(out_bmp, 'wb') as f:
        f.write(file_header)
        f.write(info_header)
        f.write(bottom_up_data)
    print(f'Captured to {out_bmp}')

    gdi32.SelectObject(mem_dc, old_bmp)
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(target_hwnd, hwnd_dc)

p.terminate()
