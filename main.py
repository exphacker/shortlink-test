import os
import json
import random
import string
import pymysql
from flask import Flask, request, jsonify
import requests
from urllib.parse import quote

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'aidpkrwp_exp',
    'password': 'aidpkrwp_exp',
    'database': 'aidpkrwp_exp'
}

# Telegram bot token
BOT_TOKEN = "7681690998:AAHKPsAnNkk3NpBJy-LS6WFKqfqm_CKrG3k"
ADMIN_CHAT_ID = "7807437342"
ADMIN_USERNAME = "@ExpHere"

# Channels to join
CHANNELS = [
    {"name": "Channel", "link": "https://t.me/expstores"},
    {"name": "Channel", "link": "https://t.me/+8oPGvSMFpqZkZGU9"}
]

# API configuration
API_URL = "https://event-offers.xyz/api.php?apikey=spa58gjap38fhpah&theme=DIRECT USE.py&name={random}&url={url}"

# Payment details
PAYTM_UPI = 'paytmqr1qdwapwer9@paytm'
PAYMENT_MERCHANT_ID = 'srwcRE81523186060028'

def get_db_connection():
    return pymysql.connect(**db_config)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        username = message['from'].get('username', message['from'].get('first_name', ''))
        text = message.get('text', '')
        
        # Check if user exists in database
        user = get_user(user_id, username)
        
        # Handle commands
        if text.startswith('/'):
            command = text.split(' ')[0]
            
            if command == '/start':
                handle_start(chat_id, user_id, username, CHANNELS)
            elif command == '/admin':
                handle_admin_command(chat_id, user_id)
            elif command == '/redeem':
                handle_redeem_command(chat_id, user_id, text)
            else:
                send_message(chat_id, "❌ Unknown command. Type /start to begin.")
        elif 'text' in message:
            # Handle regular messages
            if is_waiting_for_link(user_id):
                handle_link_submission(chat_id, user_id, text)
            elif is_waiting_for_amount(user_id):
                handle_amount_submission(chat_id, user_id, text)
    
    elif 'callback_query' in update:
        # Handle callback queries (button presses)
        callback = update['callback_query']
        chat_id = callback['message']['chat']['id']
        user_id = callback['from']['id']
        data = callback['data']
        message_id = callback['message']['message_id']
        
        user = get_user(user_id, '')
        
        if data.startswith('check_channels_'):
            handle_channel_check(chat_id, user_id, message_id, CHANNELS)
        elif data == 'make_sr':
            handle_make_sr(chat_id, user_id)
        elif data == 'profile':
            handle_profile(chat_id, user_id)
        elif data == 'statistics':
            handle_statistics(chat_id)
        elif data == 'buy_credits':
            handle_buy_credits(chat_id, user_id)
        elif data == 'done_payment':
            handle_done_payment(chat_id, user_id)
        elif data.startswith('admin_'):
            handle_admin_callback(chat_id, user_id, data, message_id)
    
    return jsonify({'status': 'ok'})

def handle_start(chat_id, user_id, username, channels):
    user = get_user(user_id, username)
    is_new = user['is_new']
    
    if is_new:
        add_credits(user_id, 10)
        mark_user_as_old(user_id)
    
    keyboard = []
    all_joined = True
    message = f"❤️‍🔥 Welcome {username} ❤️‍🔥\n\n💸 Make Easy ShortLink Today 💸\n\n🤍 Owner • @ExpHere"
    
    for channel in channels:
        is_member = check_channel_membership(user_id, channel['link'])
        if not is_member:
            all_joined = False
            keyboard.append([{'text': f"Join {channel['name']}", 'url': channel['link']}])
    
    if not all_joined:
        keyboard.append([{'text': "✅ I've Joined", 'callback_data': f'check_channels_{int(time.time())}'}])
        send_message_with_keyboard(chat_id, f"{message}\n\n⚠️ Please join our channels first:", keyboard)
    else:
        show_main_menu(chat_id, message)

def show_main_menu(chat_id, message=''):
    keyboard = [
        [{'text': "🔗 Make SR", 'callback_data': 'make_sr'}],
        [{'text': "👤 Profile", 'callback_data': 'profile'}],
        [{'text': "📊 Statistics", 'callback_data': 'statistics'}],
        [{'text': "💰 Buy Credits", 'callback_data': 'buy_credits'}]
    ]
    
    send_message_with_keyboard(chat_id, message, keyboard)

def handle_make_sr(chat_id, user_id):
    user = get_user(user_id, '')
    
    if user['credits'] < 1:
        send_message(chat_id, "❌ You don't have enough credits. Please buy credits first.")
        return
    
    add_credits(user_id, -1)
    set_user_state(user_id, 'waiting_for_link')
    send_message(chat_id, "📤 Please send the link you want to shorten:")

def handle_link_submission(chat_id, user_id, link):
    if not link.startswith(('http://', 'https://')):
        send_message(chat_id, "❌ Invalid URL. Please send a valid URL.")
        return
    
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    api_url = API_URL.format(random=random_str, url=quote(link))
    
    try:
        response = requests.get(api_url)
        result = response.json()
        
        if 'shortlink' in result:
            shortlink = result['shortlink']
            save_shortlink(user_id, link, shortlink)
            
            message = f"⚡ Congratulations Your Shortlink Have Been Created ⚡\n\n"
            message += f"☠️ ShortLink • {shortlink}\n"
            message += "🗿Bot Made By • @ExpHere\n"
            message += "💀Join Uss • @ExpStores"
            
            send_message(chat_id, message)
        else:
            send_message(chat_id, "❌ Failed to create shortlink. Please try again later.")
            add_credits(user_id, 1)  # Refund credit
    except Exception as e:
        send_message(chat_id, "❌ Error creating shortlink. Please try again later.")
        add_credits(user_id, 1)  # Refund credit
    
    clear_user_state(user_id)
    show_main_menu(chat_id)

def handle_profile(chat_id, user_id):
    user = get_user(user_id, '')
    
    message = "👤 Your Profile 👤\n\n"
    message += f"⚡ Credits • {user['credits']}\n"
    message += f"⚡ Username • @{user['username']}\n"
    message += f"⚡ {'New User' if user['is_new'] else 'Old User'}\n\n"
    message += "🗿 Owner • @ExpHere"
    
    send_message(chat_id, message)

def handle_statistics(chat_id):
    shortlinks = get_total_shortlinks()
    users = get_total_users()
    
    message = "📊 Bot Statistics 📊\n\n"
    message += f"🔗 Total Shortlinks Created: {shortlinks}\n"
    message += f"👥 Total Users: {users}\n\n"
    message += "⚡ Powered by @ExpHere"
    
    send_message(chat_id, message)

def handle_buy_credits(chat_id, user_id):
    set_user_state(user_id, 'waiting_for_amount')
    
    message = "💰 Buy Credits 💰\n\n"
    message += "Please enter the amount you want to pay (1 INR = 10 credits)\n\n"
    message += "Example: 10 (for 100 credits)"
    
    send_message(chat_id, message)

def handle_amount_submission(chat_id, user_id, amount):
    try:
        amount = float(amount)
        if amount < 1:
            raise ValueError
    except ValueError:
        send_message(chat_id, "❌ Invalid amount. Please enter a number greater than 0.")
        return
    
    credits = int(amount * 10)
    
    message = f"🔄 Please pay ₹{amount} to get {credits} credits\n\n"
    message += "📲 Payment Methods:\n"
    message += f"PayTM UPI: {PAYTM_UPI}\n"
    message += f"Merchant ID: {PAYMENT_MERCHANT_ID}\n\n"
    message += "⚠️ After payment, click the button below to verify"
    
    keyboard = [
        [{'text': "✅ Done Payment", 'callback_data': 'done_payment'}]
    ]
    
    send_message_with_keyboard(chat_id, message, keyboard)
    set_temp_data(user_id, 'pending_credits', credits)
    clear_user_state(user_id)

def handle_done_payment(chat_id, user_id):
    credits = get_temp_data(user_id, 'pending_credits')
    
    if not credits:
        send_message(chat_id, "❌ No pending payment found. Please start the process again.")
        return
    
    add_credits(user_id, credits)
    clear_temp_data(user_id, 'pending_credits')
    
    amount = credits / 10
    message = f"✅ Congratulations Your Payment Has Successful\n\n"
    message += f"Amount ₹{amount} 💗\n\n"
    message += "Thanks For Buying"
    
    send_message(chat_id, message)
    show_main_menu(chat_id)

def handle_admin_command(chat_id, user_id):
    if str(user_id) != ADMIN_CHAT_ID:
        send_message(chat_id, "❌ You are not authorized to use this command.")
        return
    
    keyboard = [
        [{'text': "📢 Broadcast", 'callback_data': 'admin_broadcast'}],
        [{'text': "🎟️ Gen Redeem Code", 'callback_data': 'admin_gen_redeem'}],
        [{'text': "🆕 New User Credits", 'callback_data': 'admin_new_user_credits'}],
        [{'text': "🔗 Change API", 'callback_data': 'admin_change_api'}],
        [{'text': "🚫 Ban/Unban User", 'callback_data': 'admin_ban_user'}],
        [{'text': "➕ Add Credits", 'callback_data': 'admin_add_credits'}]
    ]
    
    send_message_with_keyboard(chat_id, "👑 Admin Panel 👑", keyboard)

def handle_admin_callback(chat_id, user_id, data, message_id):
    if str(user_id) != ADMIN_CHAT_ID:
        send_message(chat_id, "❌ You are not authorized to use this command.")
        return
    
    action = data.replace('admin_', '')
    
    if action == 'broadcast':
        set_user_state(user_id, 'admin_broadcast')
        send_message(chat_id, "📢 Please send the message you want to broadcast:")
    elif action == 'gen_redeem':
        handle_gen_redeem(chat_id)
    elif action == 'new_user_credits':
        set_user_state(user_id, 'admin_new_user_credits')
        send_message(chat_id, "🆕 Please enter the amount of credits to give new users:")
    elif action == 'change_api':
        set_user_state(user_id, 'admin_change_api')
        send_message(chat_id, "🔗 Please send the new API URL:")
    elif action == 'ban_user':
        set_user_state(user_id, 'admin_ban_user')
        send_message(chat_id, "🚫 Please send the user ID to ban/unban:")
    elif action == 'add_credits':
        set_user_state(user_id, 'admin_add_credits')
        send_message(chat_id, "➕ Please send the user ID and credits in format: user_id|credits")
    else:
        send_message(chat_id, "❌ Unknown admin action.")

def handle_redeem_command(chat_id, user_id, text):
    if str(user_id) != ADMIN_CHAT_ID:
        send_message(chat_id, "❌ You are not authorized to use this command.")
        return
    
    parts = text.split(' ')
    if len(parts) < 2:
        send_message(chat_id, "❌ Usage: /redeem <amount>")
        return
    
    try:
        amount = int(parts[1])
        if amount < 1:
            raise ValueError
    except ValueError:
        send_message(chat_id, "❌ Amount must be a number greater than 0")
        return
    
    handle_gen_redeem(chat_id, amount)

def handle_gen_redeem(chat_id, amount=None):
    if amount is None:
        set_user_state(int(ADMIN_CHAT_ID), 'admin_redeem_amount')
        send_message(chat_id, "🎟️ Please enter the amount for the redeem code:")
        return
    
    code = f"EXPxSR{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO redeem_codes (code, amount) VALUES (%s, %s)", (code, amount))
        conn.commit()
    finally:
        conn.close()
    
    message = f"✅ Redeem Code Gen Successful ✅\n\n"
    message += f"☠️ Redeem Code • {code}\n"
    message += "⚡ Powered By • @ExpHere"
    
    send_message(chat_id, message)

# Database helper functions
def get_user(user_id, username=''):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            
            if user:
                return {
                    'user_id': user[1],
                    'username': user[2],
                    'credits': user[3],
                    'is_new': bool(user[4])
                }
            else:
                cursor.execute("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))
                conn.commit()
                return {
                    'user_id': user_id,
                    'username': username,
                    'credits': 0,
                    'is_new': True
                }
    finally:
        conn.close()

def mark_user_as_old(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET is_new = 0 WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()

def add_credits(user_id, credits):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET credits = credits + %s WHERE user_id = %s", (credits, user_id))
        conn.commit()
    finally:
        conn.close()

def get_total_shortlinks():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM shortlinks")
            return cursor.fetchone()[0]
    finally:
        conn.close()

def get_total_users():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM users")
            return cursor.fetchone()[0]
    finally:
        conn.close()

def save_shortlink(user_id, original, shortlink):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO shortlinks (user_id, original_url, short_url) VALUES (%s, %s, %s)",
                (user_id, original, shortlink)
            )
        conn.commit()
    finally:
        conn.close()

def set_user_state(user_id, state):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_states (user_id, state) VALUES (%s, %s) ON DUPLICATE KEY UPDATE state = %s",
                (user_id, state, state)
            )
        conn.commit()
    finally:
        conn.close()

def clear_user_state(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM user_states WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()

def is_waiting_for_link(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT state FROM user_states WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result and result[0] == 'waiting_for_link'
    finally:
        conn.close()

def is_waiting_for_amount(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT state FROM user_states WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result and result[0] == 'waiting_for_amount'
    finally:
        conn.close()

def set_temp_data(user_id, key, value):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO temp_data (user_id, data_key, data_value) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE data_value = %s",
                (user_id, key, value, value)
            )
        conn.commit()
    finally:
        conn.close()

def get_temp_data(user_id, key):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT data_value FROM temp_data WHERE user_id = %s AND data_key = %s", (user_id, key))
            result = cursor.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def clear_temp_data(user_id, key):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM temp_data WHERE user_id = %s AND data_key = %s", (user_id, key))
        conn.commit()
    finally:
        conn.close()

def check_channel_membership(user_id, channel_link):
    # In a real implementation, you would use Telegram's getChatMember API
    # This is a placeholder implementation
    return True

# Telegram helper functions
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    requests.post(url, data=data)

def send_message_with_keyboard(chat_id, text, keyboard):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'reply_markup': json.dumps({
            'inline_keyboard': keyboard
        })
    }
    
    requests.post(url, data=data)

def initialize_database():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    username VARCHAR(255),
                    credits INT DEFAULT 0,
                    is_new BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shortlinks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    original_url TEXT,
                    short_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id BIGINT PRIMARY KEY,
                    state VARCHAR(50),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_data (
                    user_id BIGINT,
                    data_key VARCHAR(50),
                    data_value TEXT,
                    PRIMARY KEY (user_id, data_key),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS redeem_codes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    code VARCHAR(50) UNIQUE,
                    amount INT,
                    used_by BIGINT DEFAULT NULL,
                    used_at TIMESTAMP NULL DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    finally:
        conn.close()

if __name__ == '__main__':
    import time
    # Uncomment to initialize database (run once)
    # initialize_database()
    app.run(host='0.0.0.0', port=5000)