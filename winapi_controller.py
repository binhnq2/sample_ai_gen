import time
import random
import win32gui
import win32api
import win32con
import win32process

class WinAPIController:
    def __init__(self, browser_pid=None):
        self.browser_pid = browser_pid
        self.main_hwnd = None
        self.render_hwnd = None

        if self.browser_pid:
            self.find_browser_window()

    def set_pid(self, pid):
        self.browser_pid = pid
        self.find_browser_window()

    def find_browser_window(self, log=True):
        """Finds the main Chrome window and the RenderWidgetHost for the given PID."""
        self.main_hwnd = None
        self.render_hwnd = None

        if not self.browser_pid:
            return

        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == self.browser_pid:
                    class_name = win32gui.GetClassName(hwnd)
                    if "Chrome_WidgetWin_1" in class_name:
                        self.main_hwnd = hwnd
                        return False
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            pass

        if self.main_hwnd:
            self.render_hwnd = self.find_render_host(self.main_hwnd)
            if log:
                print(f"[WinAPI] Found Main Window: {self.main_hwnd}")
                print(f"[WinAPI] Found Render Host: {self.render_hwnd}")
        elif log:
            print(f"[WinAPI] Could not find window for PID {self.browser_pid}")

    def get_main_hwnd(self, log=False):
        if not self.main_hwnd or not win32gui.IsWindow(self.main_hwnd):
            self.find_browser_window(log=log)
        return self.main_hwnd

    def is_browser_window_visible(self):
        hwnd = self.get_main_hwnd(log=False)
        if not hwnd:
            return False
        try:
            return win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)
        except Exception:
            return False

    def close_browser_window(self):
        hwnd = self.get_main_hwnd(log=False)
        if not hwnd:
            return False
        try:
            win32api.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception:
            return False

    def wait_for_window_disappear(self, timeout=30, poll_interval=0.5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.find_browser_window(log=False)
            if not self.main_hwnd:
                return True
            try:
                if not win32gui.IsWindow(self.main_hwnd) or not win32gui.IsWindowVisible(self.main_hwnd):
                    return True
            except Exception:
                return True
            time.sleep(poll_interval)

        self.find_browser_window(log=False)
        if not self.main_hwnd:
            return True
        try:
            return (not win32gui.IsWindow(self.main_hwnd)) or (not win32gui.IsWindowVisible(self.main_hwnd))
        except Exception:
            return True

    def find_render_host(self, parent_hwnd):
        """Recursively finds Chrome_RenderWidgetHostHWND."""
        result = None
        def enum_child_callback(hwnd, _):
            nonlocal result
            class_name = win32gui.GetClassName(hwnd)
            if "Chrome_RenderWidgetHostHWND" in class_name:
                result = hwnd
                return False # Stop
            return True
        
        try:
            win32gui.EnumChildWindows(parent_hwnd, enum_child_callback, None)
        except:
            pass
        return result

    def get_target_hwnd(self):
        """Returns the handle to send input to (RenderHost preferably)."""
        if not self.render_hwnd or not win32gui.IsWindow(self.render_hwnd):
            # Try to re-find if lost
            self.find_browser_window()
        return self.render_hwnd if self.render_hwnd else self.main_hwnd

    # ================= INPUT METHODS =================

    def click_background(self, x, y):
        """Sends a background click to the specific coordinates."""
        hwnd = self.get_target_hwnd()
        if not hwnd:
            print("[WinAPI] No HWND found to click!")
            return
        print("[WinAPI] INPUT_BACKEND=winapi_message ACTION=click_background")

        # Random micro-delay before click
        time.sleep(random.uniform(0.05, 0.2))

        # Make coordinates relative to client area (Puppeteer gives viewport coordinates)
        # Note: RenderWidgetHost coordinates usually match viewport coordinates directly
        
        # Pack coordinates into lParam (Low word = X, High word = Y)
        lParam = win32api.MAKELONG(int(x), int(y))
        
        # PostMessage is async and works for background windows
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        
        # Random hold time
        time.sleep(random.uniform(0.05, 0.15))
        
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        
        # Random cool-down
        time.sleep(random.uniform(0.05, 0.2))

    def type_background(self, text):
        """Sends background keystrokes."""
        hwnd = self.get_target_hwnd()
        if not hwnd: return

        print(f"[WinAPI] INPUT_BACKEND=winapi_message ACTION=type_background Typing: {text}")

        for char in text:
            # Random delay between keystrokes
            time.sleep(random.uniform(0.03, 0.15))
            
            # Send WM_CHAR (handles casing mostly correctly for standard chars)
            win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(char), 0)

    # ================= FILE UPLOAD HANDLING =================

    def handle_upload_dialog(self, file_path):
        """
        Waits for the standard Windows 'Open' dialog to appear (class #32770),
        sets the file path, and clicks Open.
        """
        print(f"[WinAPI] INPUT_BACKEND=winapi_message ACTION=handle_upload_dialog file={file_path}")
        

        dialog_hwnd = None
        start_time = time.time()
        
        # 1. Wait for dialog
        while time.time() - start_time < 10: # 10s timeout
            # Find window with class #32770 (Dialog) and title "Open" or "Mở"
            # Note: Title depends on OS language. Using class is safer, but #32770 is common.
            # We can check specific children to confirm it's a file dialog.
            
            def check_dialog(hwnd, _):
                nonlocal dialog_hwnd
                cls = win32gui.GetClassName(hwnd)
                if cls == "#32770":
                    # Check if it has "Edit" and "Button" children
                    if win32gui.FindWindowEx(hwnd, 0, "ComboBoxEx32", None) or \
                       win32gui.FindWindowEx(hwnd, 0, "Button", "Open") or \
                       win32gui.FindWindowEx(hwnd, 0, "Button", "&Open"):
                        dialog_hwnd = hwnd
                        return False
                return True

            try:
                win32gui.EnumWindows(check_dialog, None)
            except: pass
            
            if dialog_hwnd: break
            time.sleep(0.5)

        if not dialog_hwnd:
            print("[WinAPI] Upload dialog not found!")
            return False

        print(f"[WinAPI] Found Dialog HWND: {dialog_hwnd}")
        time.sleep(1)

        # 2. Find the Edit control (File Name input)
        # Usually inside ComboBoxEx32 -> ComboBox -> Edit
        # Or sometimes directly Edit (older styles). Windows 10/11 usually:
        # Dialog -> Soldier (DUIViewWndClassName) -> ... -> Breadcrumb Parent ... -> Edit
        # BUT simpler method: The file name box is usually the first "Edit" control (or inside ComboBox)
        
        # Method: Use SetText on the "Edit" control inside "ComboBoxEx32"
        # Hierarchy: #32770 -> ComboBoxEx32 -> ComboBox -> Edit
        
        cmb_ex = win32gui.FindWindowEx(dialog_hwnd, 0, "ComboBoxEx32", None)
        cmb = win32gui.FindWindowEx(cmb_ex, 0, "ComboBox", None)
        edit_hwnd = win32gui.FindWindowEx(cmb, 0, "Edit", None)
        
        if not edit_hwnd:
            # Fallback for some dialog styles
            edit_hwnd = win32gui.FindWindowEx(dialog_hwnd, 0, "Edit", None)

        if edit_hwnd:
            print(f"[WinAPI] Found Edit HWND: {edit_hwnd}. Setting text...")
            # For Python win32gui, SetWindowText works nicely
            try:
                win32gui.SendMessage(edit_hwnd, win32con.WM_SETTEXT, 0, file_path)
            except:
                pass
            time.sleep(0.5)
        else:
            print("[WinAPI] Could not find Edit box in dialog!")
            return False

        # 3. Click "Open" Button
        # Button usually has ID 1 (IDOK)
        # Or look for text "Open" / "Mở" / "Save"
        
        # Try sending IDOK to dialog
        print("[WinAPI] Clicking Open...")
        win32api.PostMessage(dialog_hwnd, win32con.WM_COMMAND, 1, 0) # 1 is usually IDOK
        
        # Fallback: Find button and click
        # btn = win32gui.FindWindowEx(dialog_hwnd, 0, "Button", "&Open") ...
        
        time.sleep(0.5)
        return True
