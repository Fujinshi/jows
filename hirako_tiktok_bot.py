#!/usr/bin/env python3
"""
HIRAKO AUTO LIKE TIKTOK BOT - GITHUB ACTIONS READY
- Support GitHub Actions 24/7
- Auto commit & save state
- No spam - Single shot langsung like sekali
"""

import requests
import time
import random
import json
import os
import threading
import re
import subprocess
import sys
from datetime import datetime
from collections import deque
from bs4 import BeautifulSoup

# Nonaktifkan warning SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== KONFIGURASI ====================

# 🔥 GANTI DENGAN DATA TELEGRAM KAMU 🔥
TELEGRAM_BOT_TOKEN = "8794092200:AAFgbuxPLGkUzLhFgFAp0q8plYl9AxmDAig"
TELEGRAM_ADMIN_ID = 8440381121

# File untuk menyimpan data
LINKS_FILE = "links.txt"
STATE_FILE = "bot_state.json"
PROXY_FILE = "proxy1.txt"

# GitHub config
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

# Proxy list (tanpa file eksternal untuk GitHub)
DEFAULT_PROXIES = [
    "45.155.221.114:80",
    "45.156.196.106:80", 
    "194.113.111.126:80",
    "103.152.232.156:80",
    "139.162.78.109:3128",
]

# Rate limiting
processed_messages = deque(maxlen=50)

# User agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0',
]

# ==================== BANNER ====================

def show_banner():
    banner = """
\033[95m
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██╗  ██╗██╗██████╗  █████╗ ██╗  ██╗ ██████╗             ║
║     ██║  ██║██║██╔══██╗██╔══██╗██║ ██╔╝██╔═══██╗            ║
║     ███████║██║██████╔╝███████║█████╔╝ ██║   ██║            ║
║     ██╔══██║██║██╔══██╗██╔══██║██╔═██╗ ██║   ██║            ║
║     ██║  ██║██║██║  ██║██║  ██║██║  ██╗╚██████╔╝            ║
║     ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝             ║
║                                                              ║
║        🤖 HIRAKO TIKTOK BOT - GITHUB ACTIONS 🤖             ║
║              ANTI-SPAM - SINGLE SHOT                        ║
╚══════════════════════════════════════════════════════════════╝
\033[0m
"""
    print(banner)

# ==================== GITHUB INTEGRATION ====================

def save_and_commit():
    """Save state and commit to GitHub"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    
    try:
        # Configure git
        subprocess.run(['git', 'config', '--global', 'user.email', 'bot@hirako.com'], capture_output=True)
        subprocess.run(['git', 'config', '--global', 'user.name', 'Hirako Bot'], capture_output=True)
        
        # Add files
        subprocess.run(['git', 'add', LINKS_FILE, STATE_FILE], capture_output=True)
        
        # Commit if changes
        result = subprocess.run(['git', 'commit', '-m', f'Auto-save: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'], 
                               capture_output=True)
        
        if result.returncode == 0:
            # Push to GitHub
            remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
            subprocess.run(['git', 'push', remote_url, 'HEAD:main'], capture_output=True)
            print("  💾 Saved to GitHub")
    except Exception as e:
        print(f"  ⚠️ GitHub save error: {e}")

def load_state():
    """Load saved state"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"success_count": 0, "fail_count": 0, "request_count": 0, "total_likes": 0}

def save_state(bot_instance):
    """Save current state"""
    state = {
        "timestamp": str(datetime.now()),
        "success_count": bot_instance.success_count,
        "fail_count": bot_instance.fail_count,
        "request_count": bot_instance.request_count,
        "total_likes": bot_instance.success_count * 10
    }
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except:
        return False

# ==================== MANAJEMEN VIDEO ====================

def load_videos():
    urls = []
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ('tiktok.com' in line or 'vt.tiktok.com' in line):
                        urls.append(line)
        except:
            pass
    return urls

def save_videos(urls):
    try:
        with open(LINKS_FILE, 'w') as f:
            for url in urls:
                f.write(url + '\n')
        return True
    except:
        return False

def add_video(url):
    urls = load_videos()
    if url not in urls:
        urls.append(url)
        save_videos(urls)
        return True, len(urls)
    return False, len(urls)

def remove_video(index):
    urls = load_videos()
    if 1 <= index <= len(urls):
        removed = urls.pop(index - 1)
        save_videos(urls)
        return True, removed, len(urls)
    return False, None, len(urls)

def clear_videos():
    save_videos([])
    return True

def extract_tiktok_urls(text):
    pattern = r'https?://(?:vt\.tiktok\.com/|www\.tiktok\.com/|tiktok\.com/|vm\.tiktok\.com/)[^\s]+'
    return re.findall(pattern, text)

# ==================== PROXY MANAGER ====================

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.blacklisted = set()
        self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from file or use defaults"""
        proxies_list = []
        
        # Try to load from file
        if os.path.exists(PROXY_FILE):
            try:
                with open(PROXY_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and ':' in line:
                            proxies_list.append(f"http://{line}")
            except:
                pass
        
        # Use defaults if no proxies found
        if not proxies_list:
            for proxy in DEFAULT_PROXIES:
                proxies_list.append(f"http://{proxy}")
        
        # Filter blacklisted
        self.proxies = [p for p in proxies_list if p not in self.blacklisted]
        random.shuffle(self.proxies)
        return len(self.proxies)
    
    def get_proxy(self):
        if not self.proxies:
            self.load_proxies()
            if not self.proxies:
                return None
        proxy = self.proxies.pop(0)
        self.proxies.append(proxy)
        return {'http': proxy, 'https': proxy}
    
    def blacklist_proxy(self, proxy_url):
        self.blacklisted.add(proxy_url)
        # Remove from active list
        if proxy_url in self.proxies:
            self.proxies.remove(proxy_url)

# ==================== AUTO LIKE BOT ====================

class AutoLikeBot:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.request_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.is_running = False
        self.processing = False
        
        # Load saved state
        saved = load_state()
        self.success_count = saved.get('success_count', 0)
        self.fail_count = saved.get('fail_count', 0)
        self.request_count = saved.get('request_count', 0)
    
    def get_service_id(self, session):
        try:
            response = session.post(
                'https://jasatambahfollowers.com/ajax/order/services.php',
                data={'category': 'tiktok'},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=15,
                verify=False
            )
            soup = BeautifulSoup(response.text, 'html.parser')
            for option in soup.find_all('option'):
                text = option.text.lower()
                if 'like' in text and ('gratis' in text or 'free' in text):
                    return option.get('value')
            return None
        except:
            return None
    
    def send_like_to_url(self, target_url):
        """Kirim like ke URL tertentu (SINGLE SHOT)"""
        if self.processing:
            return {"success": False, "message": "Sedang memproses request lain"}
        
        self.processing = True
        
        try:
            if not target_url:
                self.processing = False
                return {"success": False, "message": "URL tidak valid"}
            
            proxy = self.proxy_manager.get_proxy()
            if not proxy:
                self.processing = False
                return {"success": False, "message": "Tidak ada proxy available"}
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': random.choice(USER_AGENTS),
                'Referer': 'https://jasatambahfollowers.com/',
                'Origin': 'https://jasatambahfollowers.com',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
            })
            session.proxies = proxy
            session.verify = False
            session.timeout = 30
            
            proxy_url = proxy.get('http', '')
            
            service_id = self.get_service_id(session)
            if not service_id:
                self.proxy_manager.blacklist_proxy(proxy_url)
                self.processing = False
                return {"success": False, "message": "Gagal dapat service ID"}
            
            response = session.post(
                'https://jasatambahfollowers.com/',
                data={'service': service_id, 'target': target_url, 'jumlah': '10'},
                timeout=20,
                allow_redirects=True,
                verify=False
            )
            
            text = response.text.lower()
            
            if 'sukses' in text or 'berhasil' in text or 'success' in text:
                self.success_count += 1
                self.request_count += 1
                self.processing = False
                save_state(self)  # Auto-save after success
                return {"success": True, "message": "✅ +10 Likes!", "url": target_url}
            elif 'limit' in text or 'maksimal' in text or 'sudah pernah' in text or 'already' in text:
                self.fail_count += 1
                self.request_count += 1
                self.proxy_manager.blacklist_proxy(proxy_url)
                self.processing = False
                return {"success": False, "message": "⚠️ Limit tercapai (video sudah pernah di-like)", "url": target_url}
            else:
                self.fail_count += 1
                self.request_count += 1
                self.processing = False
                return {"success": False, "message": "❌ Gagal", "url": target_url}
                
        except Exception as e:
            self.fail_count += 1
            self.processing = False
            return {"success": False, "message": f"❌ Error: {str(e)[:30]}", "url": target_url}
    
    def get_stats(self):
        return {
            "running": self.is_running,
            "request": self.request_count,
            "success": self.success_count,
            "fail": self.fail_count,
            "total_likes": self.success_count * 10,
            "videos": len(load_videos()),
            "proxies_left": len(self.proxy_manager.proxies)
        }

# ==================== TELEGRAM HANDLER ====================

telegram_offset = 0
bot_instance = None
telegram_running = True

def send_telegram(chat_id, text):
    """Kirim pesan ke Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
        requests.post(url, json=payload, timeout=10)
        return True
    except:
        return False

def get_updates():
    """Ambil update dari Telegram"""
    global telegram_offset
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {'offset': telegram_offset, 'timeout': 25}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            return r.json().get('result', [])
        return []
    except:
        return []

def is_message_processed(message_id):
    if message_id in processed_messages:
        return True
    processed_messages.append(message_id)
    return False

def handle_message(msg):
    global bot_instance
    
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    message_id = msg['message_id']
    text = msg.get('text', '').strip()
    
    if user_id != TELEGRAM_ADMIN_ID:
        send_telegram(chat_id, "❌ Akses ditolak!")
        return
    
    if is_message_processed(message_id):
        return
    
    print(f"  📨 Process: {text[:50] if text else '(empty)'}")
    
    # SINGLE SHOT - Kirim link langsung
    if text and not text.startswith('/'):
        tiktok_urls = extract_tiktok_urls(text)
        if tiktok_urls:
            send_telegram(chat_id, f"🎯 *HIRAKO SINGLE SHOT!*\n📹 Memproses {len(tiktok_urls)} link...")
            
            results = []
            for i, url in enumerate(tiktok_urls):
                send_telegram(chat_id, f"🔄 [{i+1}/{len(tiktok_urls)}] Like ke:\n`{url[:50]}...`")
                result = bot_instance.send_like_to_url(url)
                time.sleep(2)
                results.append(result)
            
            success_count = sum(1 for r in results if r['success'])
            
            summary = f"✅ *HIRAKO - HASIL SINGLE SHOT*\n\n"
            summary += f"✅ Berhasil: *{success_count}* like\n"
            summary += f"📈 Total Like: *{success_count * 10}* likes\n\n"
            
            for r in results:
                if r['success']:
                    summary += f"✅ `{r['url'][:40]}...` → +10 Likes!\n"
                else:
                    summary += f"❌ `{r['url'][:40]}...` → {r['message'][:30]}\n"
            
            send_telegram(chat_id, summary)
            save_state(bot_instance)
            save_and_commit()
            return
    
    # COMMANDS
    if text == '/start':
        stats = bot_instance.get_stats()
        menu = f"""🤖 *HIRAKO TIKTOK BOT - GITHUB EDITION*

🎯 *SINGLE SHOT MODE:*
Kirim link TikTok → langsung like!

📊 *STATUS:*
✅ Total Like: *{stats['total_likes']}* likes
📹 Video: *{stats['videos']}*

📋 *PERINTAH:*
/start - Menu ini
/add url - Tambah video
/list - Lihat video
/remove 1 - Hapus video
/clear - Hapus semua
/status - Cek status
/stats - Statistik

🔥 *HIRAKO BOT* - 24/7 Active"""
        send_telegram(chat_id, menu)
    
    elif text == '/status':
        stats = bot_instance.get_stats()
        msg = f"""📊 *HIRAKO BOT STATUS*

✅ Sukses: *{stats['success']}* likes
❌ Gagal: *{stats['fail']}* request
📈 Total: *{stats['total_likes']}* likes
📹 Video: *{stats['videos']}*
🌐 Proxy: *{stats['proxies_left']}* active

💡 Kirim link untuk single shot!"""
        send_telegram(chat_id, msg)
    
    elif text == '/stats':
        stats = bot_instance.get_stats()
        msg = f"""📈 *HIRAKO STATISTIK*

*Total Performance:*
✅ Success: *{stats['success']}*
❌ Failed: *{stats['fail']}*
📈 Total Likes: *{stats['total_likes']}*
📡 Requests: *{stats['request']}*

*System:*
📹 Videos: *{stats['videos']}*
🌐 Proxies: *{stats['proxies_left']}*

🔥 *HIRAKO BOT - Always Online*"""
        send_telegram(chat_id, msg)
    
    elif text.startswith('/add'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_telegram(chat_id, "❌ /add <url>")
            return
        urls = extract_tiktok_urls(parts[1])
        if not urls:
            send_telegram(chat_id, "❌ URL tidak valid")
            return
        added = 0
        for url in urls:
            success, total = add_video(url)
            if success:
                added += 1
        send_telegram(chat_id, f"✅ Added *{added}* video! Total: *{total}*")
        save_and_commit()
    
    elif text == '/list':
        videos = load_videos()
        if not videos:
            send_telegram(chat_id, "📹 No videos")
            return
        msg = f"📹 *VIDEOS ({len(videos)}):*\n"
        for i, url in enumerate(videos[:10], 1):
            msg += f"{i}. {url[:40]}...\n"
        send_telegram(chat_id, msg)
    
    elif text.startswith('/remove'):
        parts = text.split()
        if len(parts) < 2:
            send_telegram(chat_id, "❌ /remove <number>")
            return
        try:
            index = int(parts[1])
            success, removed, total = remove_video(index)
            if success:
                send_telegram(chat_id, f"✅ Removed video {index}")
                save_and_commit()
            else:
                send_telegram(chat_id, f"❌ Invalid number")
        except:
            send_telegram(chat_id, "❌ Invalid number")
    
    elif text == '/clear':
        count = len(load_videos())
        clear_videos()
        send_telegram(chat_id, f"🗑️ Cleared {count} videos")
        save_and_commit()
    
    elif text == '/help':
        help_msg = """📖 *HIRAKO BOT HELP*

🎯 *SINGLE SHOT:* Kirim link TikTok langsung!
📹 *ADD:* /add https://tiktok.com/xxx
📋 *LIST:* /list
🗑️ *REMOVE:* /remove 1
🧹 *CLEAR:* /clear
📊 *STATUS:* /status
📈 *STATS:* /stats

🔥 *HIRAKO - Auto Like TikTok Bot*"""
        send_telegram(chat_id, help_msg)
    
    elif text.startswith('/'):
        send_telegram(chat_id, f"❌ Unknown command. Use /help")

def telegram_worker():
    send_telegram(TELEGRAM_ADMIN_ID, """✅ *HIRAKO BOT ONLINE - GITHUB ACTIONS*

🎯 *SINGLE SHOT READY*
Cukup kirim link TikTok, bot akan like!

📋 *Commands:*
/start - Menu
/status - Status
/stats - Statistics
/help - Help

🔥 *24/7 Active on GitHub*""")
    
    print("\n✅ HIRAKO Telegram Bot Connected!")
    print("   🎯 Single Shot Mode Active")
    
    while telegram_running:
        try:
            updates = get_updates()
            for update in updates:
                if 'message' in update:
                    handle_message(update['message'])
                telegram_offset = update['update_id'] + 1
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            time.sleep(5)

# ==================== MAIN ====================

def main():
    global bot_instance, telegram_running
    
    show_banner()
    
    print("\033[93m" + "="*55)
    print("     🤖 HIRAKO GITHUB ACTIONS BOT 🤖")
    print("="*55 + "\033[0m")
    print("\033[96m   🎯 SINGLE SHOT MODE")
    print("   ✅ Auto-Save to GitHub")
    print("   ✅ 24/7 Support\033[0m")
    print("="*55)
    
    # Load data
    videos = load_videos()
    print(f"\n\033[92m📹 Loaded {len(videos)} videos\033[0m")
    
    # Create bot instance
    bot_instance = AutoLikeBot()
    print(f"\033[92m✅ Previous stats: {bot_instance.total_likes} total likes\033[0m")
    
    # Start Telegram
    print("\n\033[96m🤟 Connecting to Telegram...\033[0m")
    telegram_thread = threading.Thread(target=telegram_worker, daemon=True)
    telegram_thread.start()
    
    print("\n\033[92m✅ HIRAKO BOT ACTIVE!\033[0m")
    print("\033[96m📱 Send TikTok link to Telegram for single shot!\033[0m")
    print("\n\033[93m💡 Bot will auto-save to GitHub\033[0m")
    print("\033[93m🔧 Press Ctrl+C to stop\033[0m")
    print("="*55)
    
    # Auto-save every 5 minutes
    last_save = time.time()
    
    try:
        while True:
            time.sleep(1)
            
            # Auto-save every 5 minutes
            if time.time() - last_save > 300:
                save_state(bot_instance)
                save_and_commit()
                last_save = time.time()
                
    except KeyboardInterrupt:
        telegram_running = False
        print("\n\n\033[93m" + "="*55)
        print("         📊 HIRAKO FINAL STATISTICS")
        print("="*55 + "\033[0m")
        if bot_instance:
            print(f"\033[96m   ✅ Success: {bot_instance.success_count} likes\033[0m")
            print(f"\033[96m   📈 Total: {bot_instance.success_count * 10} likes\033[0m")
        print("\033[93m" + "="*55 + "\033[0m")
        print("\n\033[95m👋 HIRAKO Bot Stopped\033[0m")
        print("\033[96m   Created by HIRAKO | GitHub Actions Ready\033[0m\n")

if __name__ == "__main__":
    main()
