"""
Captcha detection module - handles captcha detection and alerts
"""
import os
import requests
import sys
import time
from initialization import HAS_WINSOUND, HAS_PLYER, BASE_URL, get_headers

# Notify account/user for DM alerts
NOTIFY_USER_ID = "742378268220719187"
DISCORD_API_BASE = "https://discordapp.com/api/v9"


def check_for_captcha(token):
    """Check if bot is asking for captcha verification"""
    response = requests.get(BASE_URL + "?limit=15", headers=get_headers(token))
    if response.status_code == 200:
        messages = response.json()
        for msg in messages:
            content = msg.get('content', '').lower()
            # Check embeds too
            if 'embeds' in msg and msg['embeds']:
                for embed in msg['embeds']:
                    description = embed.get('description', '').lower()
                    title = embed.get('title', '').lower()
                    content += ' ' + description + ' ' + title
                    # Include embed fields and author text if present
                    for field in embed.get('fields', []):
                        content += ' ' + field.get('name', '').lower()
                        content += ' ' + field.get('value', '').lower()
                    author = embed.get('author', {})
                    content += ' ' + author.get('name', '').lower()
            
            # Check for captcha keywords
            captcha_keywords = [
                'captcha',
                'verify',
                'verification',
                'are you a real human',
                'verify that you are human',
                'please complete your captcha',
                'owobot.com/captcha'
            ]
            if any(keyword in content for keyword in captcha_keywords):
                return True
    return False


def notify_captcha():
    """Send notification alert for captcha"""
    # Send DM notification via secondary token (if available)
    notify_token = get_notify_token()
    if notify_token:
        send_notify_dm(notify_token, NOTIFY_USER_ID, "⚠️ CAPTCHA DETECTED. Please verify in Discord.")

    # Play alert sound - 3 beeps
    if HAS_WINSOUND:
        for i in range(3):
            import winsound
            winsound.Beep(1000, 500)  # 1000 Hz for 500ms
            time.sleep(0.3)
    
    # Try to show notification using plyer
    if HAS_PLYER:
        try:
            from plyer import notification
            notification.notify(
                title='⚠️ CAPTCHA DETECTED',
                message='OwO Bot requires captcha verification!\nPlease check Discord.',
                app_name='OwO Bot',
                timeout=10
            )
        except:
            pass
    
    # Always print to console as fallback
    print("\n" + "="*50)
    print("⚠️  CAPTCHA ALERT! ⚠️" * 3)
    print("="*50 + "\n")


def get_notify_token():
    """Load notify token from env or local file"""
    token = os.getenv("DISCORD_NOTIFY_TOKEN")
    if token:
        return token.strip()

    local_notify_file = os.path.join(os.path.dirname(__file__), "local_notify_token.txt")
    if os.path.exists(local_notify_file):
        try:
            with open(local_notify_file, "r") as f:
                token = f.read().strip()
            return token or None
        except Exception:
            return None
    return None


def send_notify_dm(token, user_id, message):
    """Send a DM to a user using the notify token"""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "authorization": token,
        "content-type": "application/json"
    }
    # Create DM channel
    dm_resp = requests.post(
        f"{DISCORD_API_BASE}/users/@me/channels",
        json={"recipient_id": str(user_id)},
        headers=headers
    )
    if dm_resp.status_code not in (200, 201):
        return False

    channel_id = dm_resp.json().get("id")
    if not channel_id:
        return False

    # Send message
    msg_resp = requests.post(
        f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
        json={"content": message},
        headers=headers
    )
    return msg_resp.status_code in (200, 201)


def test_notify_message():
    """Send a test DM using the notify token."""
    token = get_notify_token()
    if not token:
        print("Notify token not found. Set DISCORD_NOTIFY_TOKEN or src/local_notify_token.txt")
        return False

    ok = send_notify_dm(token, NOTIFY_USER_ID, "✅ Test notification from OwO bot")
    if ok:
        print("Test notification sent successfully.")
    else:
        print("Failed to send test notification.")
    return ok


if __name__ == "__main__":
    # Usage: python src/captcha_detect.py test-notify
    if len(sys.argv) > 1 and sys.argv[1] == "test-notify":
        test_notify_message()


def wait_for_captcha_resolution(token, max_wait_minutes=60*24):
    """Wait for captcha to be resolved, then resume
    
    Args:
        token: Discord token for API requests
        max_wait_minutes: Maximum time to wait before resuming anyway (default 30 min)
    """
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 360 
    check_interval = 30  # Check every 30 seconds
    
    print(f"\n⏳ PAUSED: Waiting for captcha to be resolved...")
    print(f"Will resume automatically in {max_wait_minutes} minutes if not resolved.")
    print(f"Complete the captcha in Discord to resume immediately.\n")
    
    while True:
        elapsed = time.time() - start_time
        
        # Check if captcha is still there
        if not check_for_captcha(token):
            elapsed_minutes = int(elapsed // 60)
            elapsed_seconds = int(elapsed % 60)
            print(f"\n✅ CAPTCHA RESOLVED! (waited {elapsed_minutes}m {elapsed_seconds}s)")
            print("Resuming requests...\n")
            break
        
        # Check if max wait time exceeded
        if elapsed >= max_wait_seconds:
            print(f"\n⏱️  TIMEOUT: {max_wait_minutes} minutes reached. Resuming anyway...")
            print("(You may still need to complete the captcha)\n")
            break
        
        # Wait before next check
        remaining = max_wait_seconds - elapsed
        remaining_minutes = int(remaining // 60)
        print(f"Captcha still active... ({remaining_minutes}m remaining) ", end='\r')
        time.sleep(check_interval)
