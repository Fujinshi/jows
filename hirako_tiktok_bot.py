#!/usr/bin/env python3
"""
HIRAKO BOT - GITHUB ACTIONS VERSION
Proses pesan lalu exit (tidak infinite loop)
"""

import requests
import time
import random
import json
import os
import re
from datetime import datetime
from collections import deque
from bs4 import BeautifulSoup

# Nonaktifkan warning SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== KONFIGURASI ====================

TELEGRAM_BOT_TOKEN = "8794092200:AAFgbuxPLGkUzLhFgFAp0q8plYl9AxmDAig"
TELEGRAM_ADMIN_ID = 8440381121

LINKS_FILE = "links.txt"
STATE_FILE = "bot_state.json"

DEFAULT_PROXIES = [
    "45.155.221.114:80",
    "45.156.196.106:80", 
    "194.113.111.126:80",
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0',
]

processed_messages = deque(maxlen=50)
telegram_offset = 0

# ==================== FUNCTIONS ====================

def load_videos():
    urls = []
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and 'tiktok.com' in line:
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

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"success": 0, "fail": 0}

def save_state(success, fail):
    state = {
        "timestamp": str(datetime.now()),
        "success": success,
        "fail": fail,
        "total_likes": success * 10
    }
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except:
        pass

def get_service_id(session):
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

def send_like_to_url(target_url):
    """Kirim like ke URL (single shot)"""
    try:
        proxy = random.choice(DEFAULT_PROXIES)
        proxy_dict = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': 'https://jasatambahfollowers.com/',
        })
        session.proxies = proxy_dict
        session.verify = False
        session.timeout = 30
        
        service_id = get_service_id(session)
        if not service_id:
            return {"success": False, "message": "❌ Gagal dapat service ID"}
        
        response = session.post(
            'https://jasatambahfollowers.com/',
            data={'service': service_id, 'target': target_url, 'jumlah': '10'},
            timeout=20,
            allow_redirects=True,
            verify=False
        )
        
        text = response.text.lower()
        
        if 'sukses' in text or 'berhasil' in text or 'success' in text:
            return {"success": True, "message": "✅ +10 Likes!"}
        elif 'limit' in text or 'maksimal' in text or 'sudah pernah' in text:
            return {"success": False, "message": "⚠️ Limit tercapai"}
        else:
            return {"success": False, "message": "❌ Gagal"}
            
    except Exception as e:
        return {"success": False, "message": f"❌ Error"}

def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
        requests.post(url, json=payload, timeout=10)
        return True
    except:
        return False

def get_updates(offset):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {'offset': offset, 'timeout': 10}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json().get('result', [])
        return []
    except:
        return []

def handle_message(msg, stats):
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    text = msg.get('text', '').strip()
    
    if user_id != TELEGRAM_ADMIN_ID:
        send_telegram(chat_id, "❌ Akses ditolak!")
        return stats
    
    # SINGLE SHOT - Process TikTok links
    if text and not text.startswith('/'):
        tiktok_urls = extract_tiktok_urls(text)
        if tiktok_urls:
            send_telegram(chat_id, f"🎯 *HIRAKO SINGLE SHOT!*\nMemproses {len(tiktok_urls)} link...")
            
            results = []
            for url in tiktok_urls:
                result = send_like_to_url(url)
                results.append(result)
                time.sleep(1)
            
            success_count = sum(1 for r in results if r['success'])
            
            # Update stats
            stats['success'] += success_count
            stats['fail'] += len(results) - success_count
            save_state(stats['success'], stats['fail'])
            
            summary = f"✅ *HIRAKO RESULT*\n"
            summary += f"✅ Berhasil: *{success_count}*\n"
            summary += f"📈 Total Like: *{success_count * 10}*\n\n"
            
            for r in results:
                summary += f"{r['message']}\n"
            
            send_telegram(chat_id, summary)
            return stats
    
    # COMMANDS
    if text == '/start':
        menu = f"""🤖 *HIRAKO TIKTOK BOT*

🎯 *SINGLE SHOT:* Kirim link langsung!

📊 *STATUS:*
✅ Total Like: *{stats['success'] * 10}*
📹 Video: *{len(load_videos())}*

📋 *COMMANDS:*
/start - Menu
/add url - Add video
/list - List videos
/remove 1 - Remove
/clear - Clear all
/status - Status
/stats - Statistics

🔥 *HIRAKO BOT*"""
        send_telegram(chat_id, menu)
    
    elif text == '/status':
        msg = f"""📊 *HIRAKO STATUS*

✅ Success: *{stats['success']}*
📈 Total Likes: *{stats['success'] * 10}*
📹 Videos: *{len(load_videos())}*

💡 Send link for single shot!"""
        send_telegram(chat_id, msg)
    
    elif text == '/stats':
        msg = f"""📈 *HIRAKO STATISTICS*

✅ Success: *{stats['success']}*
❌ Failed: *{stats['fail']}*
📈 Total Likes: *{stats['success'] * 10}*
📹 Videos: *{len(load_videos())}*

🔥 *HIRAKO BOT*"""
        send_telegram(chat_id, msg)
    
    elif text.startswith('/add'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_telegram(chat_id, "❌ /add <url>")
            return stats
        urls = extract_tiktok_urls(parts[1])
        if not urls:
            send_telegram(chat_id, "❌ Invalid URL")
            return stats
        added = 0
        for url in urls:
            success, total = add_video(url)
            if success:
                added += 1
        send_telegram(chat_id, f"✅ Added *{added}* video! Total: *{total}*")
    
    elif text == '/list':
        videos = load_videos()
        if not videos:
            send_telegram(chat_id, "📹 No videos")
            return stats
        msg = f"📹 *VIDEOS ({len(videos)}):*\n"
        for i, url in enumerate(videos[:10], 1):
            msg += f"{i}. {url[:40]}...\n"
        send_telegram(chat_id, msg)
    
    elif text.startswith('/remove'):
        parts = text.split()
        if len(parts) < 2:
            send_telegram(chat_id, "❌ /remove <number>")
            return stats
        try:
            index = int(parts[1])
            success, removed, total = remove_video(index)
            if success:
                send_telegram(chat_id, f"✅ Removed video {index}")
            else:
                send_telegram(chat_id, f"❌ Invalid number")
        except:
            send_telegram(chat_id, "❌ Invalid number")
    
    elif text == '/clear':
        count = len(load_videos())
        clear_videos()
        send_telegram(chat_id, f"🗑️ Cleared {count} videos")
    
    elif text == '/help':
        help_msg = """📖 *HIRAKO HELP*

🎯 *SINGLE SHOT:* Send TikTok link
📹 *ADD:* /add url
📋 *LIST:* /list
🗑️ *REMOVE:* /remove 1
🧹 *CLEAR:* /clear
📊 *STATUS:* /status
📈 *STATS:* /stats

🔥 *HIRAKO BOT*"""
        send_telegram(chat_id, help_msg)
    
    return stats

# ==================== MAIN ====================

def main():
    print("="*55)
    print("     🤖 HIRAKO GITHUB ACTIONS BOT 🤖")
    print("="*55)
    print("   📱 Processing Telegram messages...")
    print("   ⏱️  This will exit after processing")
    print("="*55)
    
    # Load stats
    stats = load_state()
    print(f"📊 Previous stats: {stats['success'] * 10} total likes")
    
    # Process updates
    global telegram_offset
    
    # Load saved offset
    if os.path.exists("offset.txt"):
        try:
            with open("offset.txt", "r") as f:
                telegram_offset = int(f.read().strip())
        except:
            pass
    
    updates = get_updates(telegram_offset)
    
    if updates:
        print(f"📨 Found {len(updates)} updates")
        for update in updates:
            if 'message' in update:
                stats = handle_message(update['message'], stats)
            telegram_offset = update['update_id'] + 1
        
        # Save offset
        with open("offset.txt", "w") as f:
            f.write(str(telegram_offset))
        
        save_state(stats['success'], stats['fail'])
        print("💾 State saved")
    else:
        print("📭 No new messages")
    
    print("✅ Done! Exiting...")
    print("="*55)

if __name__ == "__main__":
    main()
