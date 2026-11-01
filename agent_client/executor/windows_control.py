"""
Hermes Relay - Windows 控制模块
提供截图、鼠标控制、键盘控制等功能
"""

from __future__ import annotations

import io
import logging
import os
import time
import base64
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 尝试导入 pyautogui (用于鼠标/键盘控制)
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    # 安全设置
    pyautogui.FAILSAFE = True  # 鼠标移到左上角触发异常
    pyautogui.PAUSE = 0.1  # 每个操作间隔 0.1 秒
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not installed. Mouse/keyboard control disabled. pip install pyautogui")

# 尝试导入 PIL (用于截图)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not installed. Screenshot quality reduced. pip install Pillow")

# 尝试导入 mss (快速截图)
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class WindowsController:
    """
    Windows 控制器
    
    提供功能:
    - 屏幕截图
    - 鼠标控制 (移动、点击、双击、右键)
    - 键盘控制 (输入、快捷键)
    - 文件传输
    """
    
    def __init__(self, screenshot_dir: str = "screenshots"):
        self._screenshot_dir = Path(screenshot_dir)
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # 截图功能
    # =========================================================================
    
    def screenshot(self, save_path: Optional[str] = None) -> Tuple[str, str]:
        """
        截取屏幕
        
        Args:
            save_path: 保存路径 (可选)
        
        Returns:
            (文件路径, base64 编码) 的元组
        """
        if save_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = str(self._screenshot_dir / f"screenshot_{timestamp}.png")
        
        # 使用 mss 快速截图
        if MSS_AVAILABLE:
            try:
                with mss.mss() as sct:
                    screenshot = sct.grab(sct.monitors[0])
                    raw = mss.tools.to_png(screenshot.rgb, screenshot.size)
                    
                    with open(save_path, "wb") as f:
                        f.write(raw)
                    
                    b64 = base64.b64encode(raw).decode("utf-8")
                    logger.info("[Screenshot] Saved to %s", save_path)
                    return save_path, b64
            except Exception as e:
                logger.warning("[Screenshot] mss failed, trying pyautogui: %s", e)
        
        # 使用 pyautogui 截图
        if PYAUTOGUI_AVAILABLE:
            try:
                screenshot = pyautogui.screenshot()
                screenshot.save(save_path)
                
                # 转换为 base64
                buffer = io.BytesIO()
                screenshot.save(buffer, format="PNG")
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                logger.info("[Screenshot] Saved to %s", save_path)
                return save_path, b64
            except Exception as e:
                logger.error("[Screenshot] pyautogui failed: %s", e)
        
        # 使用 Windows API 截图 (后备)
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            
            hdesktop = win32gui.GetDesktopWindow()
            width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            
            hdc = win32gui.GetWindowDC(hdesktop)
            mfcDC = win32ui.CreateDCFromHandle(hdc)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = Image.frombuffer("RGB", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRX", 0, 1)
            img.save(save_path)
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hdesktop, hdc)
            
            logger.info("[Screenshot] Saved to %s", save_path)
            return save_path, b64
            
        except Exception as e:
            logger.error("[Screenshot] All methods failed: %s", e)
            raise RuntimeError(f"Screenshot failed: {e}")
    
    def screenshot_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        save_path: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        截取屏幕指定区域
        
        Args:
            x, y: 左上角坐标
            width, height: 区域大小
            save_path: 保存路径
        
        Returns:
            (文件路径, base64 编码)
        """
        if save_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            save_path = str(self._screenshot_dir / f"screenshot_{timestamp}.png")
        
        if MSS_AVAILABLE:
            try:
                with mss.mss() as sct:
                    monitor = {"top": y, "left": x, "width": width, "height": height}
                    screenshot = sct.grab(monitor)
                    raw = mss.tools.to_png(screenshot.rgb, screenshot.size)
                    
                    with open(save_path, "wb") as f:
                        f.write(raw)
                    
                    b64 = base64.b64encode(raw).decode("utf-8")
                    return save_path, b64
            except Exception as e:
                logger.warning("[Screenshot] mss region failed: %s", e)
        
        # 使用 pyautogui
        if PYAUTOGUI_AVAILABLE:
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            screenshot.save(save_path)
            
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            return save_path, b64
        
        raise RuntimeError("No screenshot method available")
    
    # =========================================================================
    # 鼠标控制
    # =========================================================================
    
    def mouse_move(self, x: int, y: int, duration: float = 0.5) -> bool:
        """
        移动鼠标到指定位置
        
        Args:
            x, y: 目标坐标
            duration: 移动耗时(秒)
        
        Returns:
            是否成功
        """
        if not PYAUTOGUI_AVAILABLE:
            logger.error("[Mouse] pyautogui not available")
            return False
        
        try:
            pyautogui.moveTo(x, y, duration=duration)
            logger.info("[Mouse] Moved to (%d, %d)", x, y)
            return True
        except Exception as e:
            logger.error("[Mouse] Move failed: %s", e)
            return False
    
    def mouse_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1,
    ) -> bool:
        """
        点击指定位置
        
        Args:
            x, y: 目标坐标
            button: 鼠标按钮 ("left", "right", "middle")
            clicks: 点击次数
            interval: 多次点击间隔
        
        Returns:
            是否成功
        """
        if not PYAUTOGUI_AVAILABLE:
            logger.error("[Mouse] pyautogui not available")
            return False
        
        try:
            pyautogui.click(x, y, clicks=clicks, button=button, interval=interval)
            logger.info("[Mouse] Clicked (%d, %d) button=%s clicks=%d", x, y, button, clicks)
            return True
        except Exception as e:
            logger.error("[Mouse] Click failed: %s", e)
            return False
    
    def mouse_double_click(self, x: int, y: int) -> bool:
        """双击指定位置"""
        return self.mouse_click(x, y, clicks=2)
    
    def mouse_right_click(self, x: int, y: int) -> bool:
        """右键点击指定位置"""
        return self.mouse_click(x, y, button="right")
    
    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> bool:
        """
        拖拽鼠标
        
        Args:
            start_x, start_y: 起始坐标
            end_x, end_y: 结束坐标
            duration: 拖拽耗时
            button: 鼠标按钮
        
        Returns:
            是否成功
        """
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(
                end_x - start_x,
                end_y - start_y,
                duration=duration,
                button=button,
            )
            logger.info("[Mouse] Dragged from (%d,%d) to (%d,%d)", start_x, start_y, end_x, end_y)
            return True
        except Exception as e:
            logger.error("[Mouse] Drag failed: %s", e)
            return False
    
    def mouse_scroll(self, x: int, y: int, clicks: int = 3) -> bool:
        """
        滚动鼠标滚轮
        
        Args:
            x, y: 滚动位置
            clicks: 滚动次数 (正数向上，负数向下)
        
        Returns:
            是否成功
        """
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            pyautogui.moveTo(x, y)
            pyautogui.scroll(clicks)
            logger.info("[Mouse] Scrolled at (%d, %d) clicks=%d", x, y, clicks)
            return True
        except Exception as e:
            logger.error("[Mouse] Scroll failed: %s", e)
            return False
    
    # =========================================================================
    # 键盘控制
    # =========================================================================
    
    def keyboard_type(self, text: str, interval: float = 0.05) -> bool:
        """
        输入文字
        
        Args:
            text: 要输入的文字
            interval: 按键间隔
        
        Returns:
            是否成功
        """
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            pyautogui.typewrite(text, interval=interval)
            logger.info("[Keyboard] Typed: %s", text[:50])
            return True
        except Exception as e:
            logger.error("[Keyboard] Type failed: %s", e)
            return False
    
    def keyboard_hotkey(self, *keys) -> bool:
        """
        按下快捷键
        
        Args:
            *keys: 按键列表，如 "ctrl", "c"
        
        Returns:
            是否成功
        """
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            pyautogui.hotkey(*keys)
            logger.info("[Keyboard] Hotkey: %s", "+".join(keys))
            return True
        except Exception as e:
            logger.error("[Keyboard] Hotkey failed: %s", e)
            return False
    
    def keyboard_press(self, key: str) -> bool:
        """
        按下单个键
        
        Args:
            key: 按键名称
        
        Returns:
            是否成功
        """
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            pyautogui.press(key)
            logger.info("[Keyboard] Pressed: %s", key)
            return True
        except Exception as e:
            logger.error("[Keyboard] Press failed: %s", e)
            return False
    
    # =========================================================================
    # 文件传输
    # =========================================================================
    
    def file_to_base64(self, file_path: str) -> str:
        """将文件转换为 base64"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def base64_to_file(self, b64: str, file_path: str) -> bool:
        """将 base64 保存为文件"""
        try:
            data = base64.b64decode(b64)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            logger.error("[File] Save failed: %s", e)
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """获取文件信息"""
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path.absolute()),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }
    
    # =========================================================================
    # 系统信息
    # =========================================================================
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕分辨率"""
        if PYAUTOGUI_AVAILABLE:
            return pyautogui.size()
        
        import ctypes
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """获取当前鼠标位置"""
        if PYAUTOGUI_AVAILABLE:
            return pyautogui.position()
        
        import ctypes
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y


# 全局实例
_controller: Optional[WindowsController] = None


def get_controller() -> WindowsController:
    """获取全局控制器实例"""
    global _controller
    if _controller is None:
        _controller = WindowsController()
    return _controller
