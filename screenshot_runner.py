import sys, os, ctypes, time
sys.path.insert(0, os.path.dirname(__file__))
import win32gui, win32ui, win32con
from PIL import Image
import customtkinter as ctk
from app.ui.main_window import MainWindow

def capture_hwnd(hwnd):
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bot - top
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    bmp    = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(bmp)
    ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
    info   = bmp.GetInfo()
    bits   = bmp.GetBitmapBits(True)
    img    = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), bits, "raw", "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    saveDC.DeleteDC(); mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    return img

class ScreenshotWindow(MainWindow):
    def __init__(self):
        super().__init__()
        self.attributes("-topmost", True)
        self.after(3000, self._shoot)
        self._steps = ["개요", "프로세스", "설정"]
        self._names = ["ss_overview.png", "ss_processes.png", "ss_settings.png"]
        self._idx = 0

    def _shoot(self):
        if self._idx >= len(self._steps):
            self.after(200, self.on_closing); return
        self._tabs.set(self._steps[self._idx])
        self.update_idletasks()
        self.after(1200, self._capture)

    def _capture(self):
        hwnd = win32gui.FindWindow(None, "SysMonitor")
        if hwnd:
            img = capture_hwnd(hwnd)
            img.save(os.path.join(os.path.dirname(__file__), self._names[self._idx]))
            print(f"Saved {self._names[self._idx]}")
        self._idx += 1
        self.after(300, self._shoot)

if __name__ == "__main__":
    app = ScreenshotWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
