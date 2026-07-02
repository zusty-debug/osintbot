import sqlite3
import json
import time
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import sys

# ----------------------------
# CONFIGURATION
# ----------------------------
BOT_TOKEN = '7798206205:AAFXSS_3F8sivVxAMuPrbpZq2DBvDGlDjK0'
CHANNEL_USERNAME = '@samplebyzusty'
ADMIN_USERNAME = '@xxzusty'
ADMIN_ID = 8847453162
API_KEY = 'abhigyanofficialkey'
API_URL = 'https://paid.originalapis.workers.dev/leak'

# Working APIs
VEHICLE_API = 'https://paid.originalapis.workers.dev/leak?key=abhigyanofficialkey&query='
UPI_API = 'DM @FOREVER_HIDDEN FOR API'
UPI_API_KEY = 'DM @FOREVER_HIDDEN FOR API'
AADHAR_API = 'DM @FOREVER_HIDDEN FOR API'
AADHAR_API_KEY = 'DM @FOREVER_HIDDEN FOR API'
PAK_API = 'DM @FOREVER_HIDDEN FOR API'
FAMILY_API = 'DM @FOREVER_HIDDEN FOR API'

# For username->number we will provide a link to the external bot
USERNAME_TO_BOT_LINK = 'DM @FOREVER_HIDDEN FOR API'

# Credits & daily bonus
DEFAULT_FREE_CREDITS = 36
CREDITS_PER_SEARCH = 1
DAILY_BONUS_CREDITS = 10
DAILY_BONUS_COOLDOWN = 24 * 3600  # seconds

# Database file
DB_FILE = 'ho_users.db'

# User-Agent for requests
USER_AGENT = 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36'

# Emoji map for better formatting
EMOJI_MAP = {
    # General fields
    'FullName': '👤', 'name': '👤', 'Username': '👤', 'Age': '🎂',
    'Gender': '🚻', 'Phone': '📞', 'mobile': '📞', 'email': '📧',
    'Password': '🔑', 'address': '🏠', 'City': '🏙️', 'District': '📍',
    'State': '🧭', 'PinCode': '📮', 'Zip': '📮', 'Country': '🌎',
    'IP': '🌐', 'DOB': '📅', 'fname': '👨‍👧', 'alt': '📱', 
    'circle': '📡', 'id': '🆔', 'Contact': '📞',
    
    # UPI fields
    'UPI_ID': '💳', 'Account_Holder_Name': '👤', 'VPA': '💳', 
    'IFSC_Code': '🏛️', 'Bank_Name': '🏦', 'Branch_Name': '🏢',
    
    # Vehicle specific fields
    'RC_Number': '🚗', 'Status': '📊', 'Owner_Name': '👤', 
    'Fathers_Name': '👨‍👧', 'Maker_Model': '🏭', 'Model_Name': '🚘',
    'Vehicle_Class': '🚙', 'Fuel_Type': '⛽', 'Registration_Date': '📅',
    'Registered_RTO': '🏛️', 'City_Name': '🏙️', 'Address': '🏠',
    'Insurance_Company': '🛡️', 'Insurance_Expiry': '📋', 'Fitness_Upto': '✅',
    'Financier_Name': '🏦',
    
    # Aadhaar specific fields
    'Aadhaar_Number': '🆔', 'Name': '👤', 'Father_Name': '👨‍👧', 
    'Mobile': '📞', 'Alt_Mobile': '📱', 'Circle': '📡', 'Email': '📧',
    
    # Pakistan specific fields
    'CNIC': '🆔',
    
    # Family specific fields
    'Member_Name': '👤', 'Relationship': '👨‍👩‍👧', 'Member_ID': '🆔', 
    'UID_Status': '✅', 'Home_State': '🧭', 'Home_District': '📍', 
    'Scheme_Name': '📋', 'RC_ID': '🆔', 'Allowed_ONORC': '✅', 
    'Dup_UID_Status': '⚠️'
}

# ----------------------------
# Logging setup
# ----------------------------
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def logger(message: str, level: str = 'INFO'):
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.log(log_level, message)

# ----------------------------
# Database helpers
# ----------------------------
def get_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger(f"Database connection failed: {e}", 'ERROR')
        return None

def init_db():
    db = get_db()
    if not db:
        return False
    
    try:
        cursor = db.cursor()
        
        # Create users table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                phone TEXT,
                credits INTEGER DEFAULT {DEFAULT_FREE_CREDITS},
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily_bonus INTEGER DEFAULT 0,
                last_12_digit TEXT DEFAULT NULL,
                admin_state TEXT DEFAULT NULL
            )
        """)
        
        # Create searches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query_type TEXT,
                query_value TEXT,
                result_summary TEXT,
                created_at INTEGER
            )
        """)
        
        # Create broadcast_chats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_type TEXT,
                title TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add admin user if not exists
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, credits) VALUES (?, ?, -1)", 
                      (ADMIN_ID, ADMIN_USERNAME))
        
        db.commit()
        db.close()
        logger("Database initialized successfully")
        return True
    except sqlite3.Error as e:
        logger(f"Database initialization failed: {e}", 'ERROR')
        return False

def is_new_user(user_id: int) -> bool:
    db = get_db()
    if not db:
        return True
    
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone() is None
    db.close()
    return result

def add_user(user_id: int, username: str, phone: str = None) -> bool:
    db = get_db()
    if not db:
        return False
    
    credits = -1 if user_id == ADMIN_ID else DEFAULT_FREE_CREDITS
    try:
        cursor = db.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, username, phone, credits) VALUES (?, ?, ?, ?)",
                      (user_id, username, phone, credits))
        db.commit()
        db.close()
        logger(f"User {user_id} added/updated successfully")
        return True
    except sqlite3.Error as e:
        logger(f"Add user failed: {e}", 'ERROR')
        return False

def get_user_row(user_id: int) -> Optional[Dict]:
    db = get_db()
    if not db:
        return None
    
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    db.close()
    return dict(row) if row else None

def get_user_credits(user_id: int) -> int:
    if user_id == ADMIN_ID:
        return -1
    
    row = get_user_row(user_id)
    return int(row['credits']) if row else 0

def deduct_credits(user_id: int, amount: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    
    cur_credits = get_user_credits(user_id)
    if cur_credits < amount:
        return False
    
    db = get_db()
    if not db:
        return False
    
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET credits = credits - ? WHERE user_id = ?", (amount, user_id))
        db.commit()
        db.close()
        logger(f"Deducted {amount} credits from user {user_id}")
        return True
    except sqlite3.Error as e:
        logger(f"Deduct credits failed: {e}", 'ERROR')
        return False

def modify_credits(user_id: int, amount: int, add: bool = True) -> bool:
    db = get_db()
    if not db:
        return False
    
    row = get_user_row(user_id)
    if not row:
        return False
    
    if not add and user_id == ADMIN_ID:
        return False
    
    try:
        cursor = db.cursor()
        if add:
            cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
        else:
            cursor.execute("UPDATE users SET credits = credits - ? WHERE user_id = ?", (amount, user_id))
        db.commit()
        db.close()
        action = "added" if add else "removed"
        logger(f"{action} {amount} credits for user {user_id}")
        return True
    except sqlite3.Error as e:
        logger(f"Modify credits failed: {e}", 'ERROR')
        return False

def update_phone(user_id: int, phone: str) -> bool:
    db = get_db()
    if not db:
        return False
    
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        db.commit()
        db.close()
        return True
    except sqlite3.Error as e:
        logger(f"Update phone failed: {e}", 'ERROR')
        return False

def update_last_12_digit(user_id: int, value: str) -> bool:
    db = get_db()
    if not db:
        return False
    
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET last_12_digit = ? WHERE user_id = ?", (value, user_id))
        db.commit()
        db.close()
        return True
    except sqlite3.Error as e:
        logger(f"Update last 12 digit failed: {e}", 'ERROR')
        return False

def get_last_12_digit(user_id: int) -> Optional[str]:
    row = get_user_row(user_id)
    return row.get('last_12_digit') if row else None

def set_admin_state(key: str, value: Any) -> bool:
    db = get_db()
    if not db:
        return False
    
    state = get_admin_state()
    state[key] = value
    
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET admin_state = ? WHERE user_id = ?", (json.dumps(state), ADMIN_ID))
        db.commit()
        db.close()
        return True
    except sqlite3.Error as e:
        logger(f"Set admin state failed: {e}", 'ERROR')
        return False

def get_admin_state(key: str = None) -> Union[Dict, Any]:
    row = get_user_row(ADMIN_ID)
    if not row or not row['admin_state']:
        return {} if key is None else None
    
    try:
        state = json.loads(row['admin_state'])
        return state if key is None else state.get(key)
    except json.JSONDecodeError:
        return {} if key is None else None

def log_search(user_id: int, qtype: str, qvalue: str, result_summary: str) -> bool:
    db = get_db()
    if not db:
        return False
    
    try:
        cursor = db.cursor()
        cursor.execute("INSERT INTO searches (user_id, query_type, query_value, result_summary, created_at) VALUES (?, ?, ?, ?, ?)",
                      (user_id, qtype, qvalue, result_summary, int(time.time())))
        db.commit()
        db.close()
        logger(f"Search logged for user {user_id}: {qtype} - {qvalue}")
        return True
    except sqlite3.Error as e:
        logger(f"Log search failed: {e}", 'ERROR')
        return False

def get_recent_searches(user_id: int, limit: int = 10) -> List[Dict]:
    db = get_db()
    if not db:
        return []
    
    cursor = db.cursor()
    cursor.execute("SELECT query_type, query_value, result_summary, created_at FROM searches WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                  (user_id, limit))
    rows = cursor.fetchall()
    db.close()
    return [dict(row) for row in rows]

def get_all_users() -> List[Dict]:
    db = get_db()
    if not db:
        return []
    
    cursor = db.cursor()
    cursor.execute("SELECT user_id, username, phone, credits FROM users")
    rows = cursor.fetchall()
    db.close()
    return [dict(row) for row in rows]

def get_broadcast_groups() -> List[int]:
    db = get_db()
    if not db:
        return []
    
    cursor = db.cursor()
    cursor.execute("SELECT chat_id FROM broadcast_chats")
    rows = cursor.fetchall()
    db.close()
    return [row['chat_id'] for row in rows]

# ----------------------------
# API query functions
# ----------------------------
def make_request(url: str, params: Dict = None, timeout: int = 30) -> Optional[Dict]:
    if params is None:
        params = {}
    
    full_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    logger(f"Making API request to: {full_url}")
    
    try:
        response = requests.get(
            full_url,
            timeout=timeout,
            headers={
                'User-Agent': USER_AGENT,
                'Accept': 'application/json',
                'Connection': 'keep-alive'
            },
            verify=False
        )
        
        if response.status_code != 200:
            logger(f"HTTP error {response.status_code} for {url}", 'ERROR')
            return None
        
        return response.json()
    except requests.RequestException as e:
        logger(f"Request error for {url}: {e}", 'ERROR')
        return None
    except json.JSONDecodeError as e:
        logger(f"JSON decode error for {url}: {e}", 'ERROR')
        return None

def query_main_api(phone: str) -> Dict:
    logger(f"Querying main API for phone: {phone}")
    params = {'api_key': API_KEY, 'mobile': phone}
    data = make_request(API_URL, params)
    
    if not data:
        logger(f"No data found for phone: {phone}")
        return {'Error': 'No data found for the provided mobile number'}
    
    logger(f"Main API returned data for phone: {phone}")
    
    # API response format fix
    if isinstance(data, list) and data and isinstance(data[0], dict):
        # Response array of objects format
        formatted_data = []
        for item in data:
            formatted_data.append({
                'FullName': item.get('name', 'N/A'),
                'FatherName': item.get('father_name', 'N/A'),
                'Mobile': item.get('mobile', phone),
                'Alt_Mobile': item.get('alt_mobile', 'N/A'),
                'Address': item.get('address', 'N/A'),
                'Circle': item.get('circle', 'N/A'),
                'Aadhaar_Number': item.get('id_number', 'N/A'),
                'Email': item.get('email', 'N/A')
            })
        return {'List': {'NumberAPI': {'Data': formatted_data}}}
    else:
        # Single object format
        return {'List': {'NumberAPI': {'Data': [data] if isinstance(data, dict) else [data]}}}

def query_vehicle_api(rc_number: str) -> Dict:
    logger(f"Querying Vehicle API for RC: {rc_number}")
    clean_rc = rc_number.upper().strip()
    params = {'rc_number': clean_rc}
    data = make_request(VEHICLE_API, params, 45)
    
    if not data or data.get('status') != 'success' or 'details' not in data:
        logger(f"No vehicle data found for RC: {clean_rc}")
        return {'Error': f"No vehicle data found for {clean_rc}"}
    
    details = data['details']
    formatted = {
        'RC_Number': data.get('rc_number', clean_rc),
        'Status': data.get('status', 'N/A'),
        'Owner_Name': details.get('Owner Name', 'N/A'),
        'Fathers_Name': details.get("Father's Name", 'N/A'),
        'Maker_Model': details.get('Maker Model', 'N/A'),
        'Model_Name': details.get('Model Name', 'N/A'),
        'Vehicle_Class': details.get('Vehicle Class', 'N/A'),
        'Fuel_Type': details.get('Fuel Type', 'N/A'),
        'Registration_Date': details.get('Registration Date', 'N/A'),
        'Registered_RTO': details.get('Registered RTO', 'N/A'),
        'City_Name': details.get('City Name', 'N/A'),
        'Address': details.get('Address', 'N/A'),
        'Insurance_Company': details.get('Insurance Company', 'N/A'),
        'Insurance_Expiry': details.get('Insurance Expiry', 'N/A'),
        'Fitness_Upto': details.get('Fitness Upto', 'N/A'),
        'Financier_Name': details.get('Financier Name', 'N/A')
    }
    
    return {'List': {'VehicleAPI': {'Data': [formatted]}}}

def query_upi_api(upi_id: str) -> Dict:
    logger(f"Querying UPI API for: {upi_id}")
    clean_upi = upi_id.lower().strip()
    params = {'upi_id': clean_upi, 'key': UPI_API_KEY}
    data = make_request(UPI_API, params, 45)
    
    if not data or 'vpa_details' not in data:
        logger(f"No UPI data found for: {clean_upi}")
        return {'Error': f"No UPI data found for {clean_upi}"}
    
    vpa_info = data['vpa_details']
    formatted = {
        'UPI_ID': clean_upi,
        'Account_Holder_Name': vpa_info.get('name', 'N/A'),
        'IFSC_Code': vpa_info.get('ifsc', 'N/A'),
        'VPA': vpa_info.get('vpa', clean_upi)
    }
    
    if data.get('bank_details_raw'):
        bank_info = data['bank_details_raw']
        formatted.update({
            'Bank_Name': bank_info.get('BANK', 'N/A'),
            'Branch_Name': bank_info.get('BRANCH', 'N/A'),
            'City': bank_info.get('CITY', 'N/A'),
            'State': bank_info.get('STATE', 'N/A'),
            'Address': bank_info.get('ADDRESS', 'N/A'),
            'Contact': bank_info.get('CONTACT', 'N/A')
        })
    
    return {'List': {'UPIAPI': {'Data': [formatted]}}}

def query_aadhar_api(aadhar_number: str) -> Dict:
    logger(f"Querying Aadhaar API for: {aadhar_number}")
    clean_aadhar = aadhar_number.strip()
    params = {'key': AADHAR_API_KEY, 'type': 'id_number', 'term': clean_aadhar}
    data = make_request(AADHAR_API, params, 45)
    
    if not data or not isinstance(data, list) or len(data) == 0:
        logger(f"No Aadhaar data found for: {clean_aadhar}")
        return {'Error': f"No Aadhaar data found for {clean_aadhar}"}
    
    formatted_results = []
    for item in data:
        formatted_results.append({
            'Aadhaar_Number': item.get('id_number', clean_aadhar),
            'Name': item.get('name', 'N/A'),
            'Father_Name': item.get('father_name', 'N/A'),
            'Mobile': item.get('mobile', 'N/A'),
            'Alt_Mobile': item.get('alt_mobile', 'N/A'),
            'Address': item.get('address', 'N/A'),
            'Circle': item.get('circle', 'N/A'),
            'Email': item.get('email', 'N/A')
        })
    
    return {'List': {'AadhaarAPI': {'Data': formatted_results}}}

def query_pak_api(phone_number: str) -> Dict:
    logger(f"Querying Pakistan API for: {phone_number}")
    clean_phone = phone_number.strip()
    params = {'number': clean_phone}
    data = make_request(PAK_API, params, 45)
    
    if not data or 'results' not in data or len(data['results']) == 0:
        logger(f"No Pakistan data found for: {clean_phone}")
        return {'Error': f"No data found for {clean_phone}"}
    
    formatted_results = []
    for item in data['results']:
        formatted_results.append({
            'Mobile': item.get('Mobile', clean_phone),
            'Name': item.get('Name', 'N/A'),
            'CNIC': item.get('CNIC', 'N/A'),
            'Address': item.get('Address', 'N/A')
        })
    
    return {'List': {'PakAPI': {'Data': formatted_results}}}

def query_family_api(aadhar_number: str) -> Dict:
    logger(f"Querying Family API for Aadhaar: {aadhar_number}")
    clean_aadhar = aadhar_number.strip()
    params = {'aadhaar': clean_aadhar, 'key': 'paidchx'}
    data = make_request(FAMILY_API, params, 45)
    
    if not data or 'memberDetailsList' not in data or len(data['memberDetailsList']) == 0:
        logger(f"No family data found for Aadhaar: {clean_aadhar}")
        return {'Error': f"No family data found for Aadhaar {clean_aadhar}"}
    
    formatted_results = []
    for item in data['memberDetailsList']:
        formatted_results.append({
            'Member_Name': item.get('memberName', 'N/A'),
            'Relationship': item.get('releationship_name', 'N/A'),
            'Member_ID': item.get('memberId', 'N/A'),
            'UID_Status': item.get('uid', 'N/A')
        })
    
    general_info = {
        'Aadhaar_Number': clean_aadhar,
        'Address': data.get('address', 'N/A'),
        'Home_State': data.get('homeStateName', 'N/A'),
        'Home_District': data.get('homeDistName', 'N/A'),
        'Scheme_Name': data.get('schemeName', 'N/A'),
        'RC_ID': data.get('rcId', 'N/A'),
        'Allowed_ONORC': data.get('allowed_onorc', 'N/A'),
        'Dup_UID_Status': data.get('dup_uid_status', 'N/A')
    }
    
    return {'List': {'FamilyAPI': {'General_Info': general_info, 'Data': formatted_results}}}

def format_results(resp: Dict) -> str:
    if 'Error' in resp:
        return f"❌ API error: {resp['Error']}"
    
    text = "📊 Search Results:\n\n"
    for db, data in resp.get('List', {}).items():
        text += f"📂 Database: {db}\n"
        
        if 'General_Info' in data:
            text += "📋 General Information:\n"
            for col, val in data['General_Info'].items():
                if not val or val == 'N/A':
                    continue
                emoji = EMOJI_MAP.get(col, '🔸')
                display_val = str(val)
                if col == 'Address' and len(display_val) > 50:
                    display_val = display_val[:47] + '...'
                text += f"{emoji} {col.replace('_', ' ')}: {display_val}\n"
            text += "─" * 25 + "\n"
        
        if 'Data' not in data or not data['Data']:
            text += "⚠️ No results found for this query\n"
            continue
        
        for idx, row in enumerate(data['Data']):
            text += f"🔢 Result {idx + 1}:\n"
            if isinstance(row, dict):
                for col, val in row.items():
                    if not val or val == 'N/A':
                        continue
                    emoji = EMOJI_MAP.get(col, '🔸')
                    display_val = str(val)
                    if col == 'Address' and len(display_val) > 50:
                        display_val = display_val[:47] + '...'
                    text += f"{emoji} {col.replace('_', ' ')}: {display_val}\n"
            else:
                text += f"📄 {row}\n"
            text += "─" * 25 + "\n"
    
    return text

# ----------------------------
# Telegram API helper
# ----------------------------
def send_message(chat_id: int, text: str, reply_markup: Dict = None, parse_mode: str = 'HTML') -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            logger(f"Telegram API error: HTTP {response.status_code} for chat {chat_id}", 'ERROR')
            return False
        
        result = response.json()
        if not result.get('ok'):
            logger(f"Telegram sendMessage error: {result.get('description', 'Unknown error')}", 'ERROR')
            return False
        
        return True
    except requests.RequestException as e:
        logger(f"Telegram API request failed: {e}", 'ERROR')
        return False

def send_chat_action(chat_id: int, action: str = 'typing') -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
    data = {'chat_id': chat_id, 'action': action}
    
    try:
        response = requests.post(url, data=data, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def get_chat_member(chat_id: str, user_id: int) -> Dict:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {'chat_id': chat_id, 'user_id': user_id}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except requests.RequestException:
        return {}

def answer_callback_query(callback_id: str, text: str = None, show_alert: bool = False) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    data = {'callback_query_id': callback_id}
    
    if text:
        data['text'] = text
    if show_alert:
        data['show_alert'] = show_alert
    
    try:
        response = requests.post(url, data=data, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def edit_message(chat_id: int, message_id: int, text: str, reply_markup: Dict = None) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False

# ----------------------------
# Keyboards & UI
# ----------------------------
def main_menu_keyboard() -> Dict:
    return {
        'inline_keyboard': [
            [
                {'text': '🔍 Number Search', 'callback_data': 'menu_number'},
                {'text': '🚗 Vehicle Search', 'callback_data': 'menu_vehicle'}
            ],
            [
                {'text': '💳 UPI Search', 'callback_data': 'menu_upi'},
                {'text': '🆔 Aadhaar Search', 'callback_data': 'menu_aadhar'}
            ],
            [
                {'text': '🇵🇰 Pak Search', 'callback_data': 'menu_pak'},
                {'text': '👨‍👩‍👧 Aadhaar to Family', 'callback_data': 'menu_family'}
            ],
            [
                {'text': '🔁 Telegram Username To Number', 'callback_data': 'menu_username'}
            ],
            [
                {'text': '👤 Profile Info', 'callback_data': 'menu_profile'},
                {'text': '📞 Contact Admin', 'callback_data': 'menu_contact'}
            ],
            [
                {'text': '🕒 Recent Searches', 'callback_data': 'menu_recent'},
                {'text': '🎁 Daily Bonus', 'callback_data': 'menu_daily'}
            ]
        ]
    }

def admin_panel_keyboard() -> Dict:
    return {
        'inline_keyboard': [
            [{'text': '👥 View All Users', 'callback_data': 'view_users'}],
            [{'text': '📢 Broadcast Message', 'callback_data': 'broadcast'}],
            [{'text': '➕ Add Credits', 'callback_data': 'add_credits'}],
            [{'text': '➖ Remove Credits', 'callback_data': 'remove_credits'}],
            [{'text': '🔙 Back to Main Menu', 'callback_data': 'back_to_main'}]
        ]
    }

# ----------------------------
# Handlers logic
# ----------------------------
def handle_start(chat_id: int, user_id: int, username: str, first_name: str):
    username = username or first_name or 'User'
    
    if is_new_user(user_id):
        member = get_chat_member(CHANNEL_USERNAME, user_id)
        joined = member.get('result', {}).get('status') in ['member', 'administrator', 'creator']
        
        if not joined:
            keyboard = {
                'inline_keyboard': [
                    [{'text': '📢 Join Channel', 'url': f"https://t.me/{CHANNEL_USERNAME[1:]}"}],
                    [{'text': '✅ I Joined!', 'callback_data': 'joined'}]
                ]
            }
            
            send_message(chat_id,
                "🔰 <b>CYBER X DETAILS FINDER</b> 🔰\n\n"
                "Welcome! To use this bot you must join the channel first.\n\n"
                "Each search costs credits. New users get 36 free credits.",
                keyboard
            )
            return
        
        add_user(user_id, username)
    
    credits = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
    text = (
        "🔰 <b>CYBER X DETAILS FINDER</b> 🔰\n"
        "═══════════════════\n"
        "👾 <b>WELCOME TO THE BOT!</b> 👾\n"
        "═══════════════════\n\n"
        f"🎯 User: <code>{first_name}</code>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💎 Credits: <code>{credits}</code>\n\n"
        "You are already a member! 🎉\n"
        "Choose an option below to continue or use commands:\n"
        "• /num xxxxxxxxxx - Phone search\n"
        "• /vehicle RCNUMBER - Vehicle search\n"
        "• /upi UPI_ID - UPI search 💳\n"
        "• /aadhar xxxxxxxxxxxx - Aadhaar search 🆔\n"
        "• /pak xxxxxxxxxxxx - Pakistan number search 🇵🇰\n"
        "• /family xxxxxxxxxxxx - Aadhaar family search 👨‍👩‍👧\n"
        "• /recent - Your recent searches\n"
        "• /admcmd - Admin panel (admin only)"
    )
    
    send_message(chat_id, text, main_menu_keyboard())

def handle_callback(callback_id: str, chat_id: int, message_id: int, user_id: int, data: str):
    # Always answer callback query first
    answer_callback_query(callback_id)

    if data == 'joined':
        member = get_chat_member(CHANNEL_USERNAME, user_id)
        joined = member.get('result', {}).get('status') in ['member', 'administrator', 'creator']
        
        if joined:
            username = member.get('result', {}).get('user', {}).get('username', member.get('result', {}).get('user', {}).get('first_name', ''))
            add_user(user_id, username)
            credits = get_user_credits(user_id)
            text = ("🎊 Great! You're now registered!\n"
                   f"💎 Credits: {'Unlimited' if user_id == ADMIN_ID else credits}\n\n"
                   "Use /num xxxxxxxxxx, /vehicle UP61S6030, /upi 9038103500@ybl, /aadhar 284495408590, /pak 923362006909, or /family 202372727238 to search.\n")
            edit_message(chat_id, message_id, text, main_menu_keyboard())
        else:
            edit_message(chat_id, message_id, "❌ Oops! You haven't joined the channel yet. Please join and try again.")
        return

    if data == 'back_to_main':
        credits = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        text = f"🔰 <b>Main Menu</b> 🔰\n\n💎 Your Credits: <code>{credits}</code>\n\nChoose an option:"
        edit_message(chat_id, message_id, text, main_menu_keyboard())
        return

    # Menu callbacks
    if data == 'menu_number':
        edit_message(chat_id, message_id, "📱 Send the phone number in plain digits (10 digits). Example: 8873565662")
    elif data == 'menu_vehicle':
        edit_message(chat_id, message_id,
            "🚗 <b>Vehicle Search</b>\n\n"
            "Send RC/Registration number in format: STATE##XXXXX\n"
            "📄 Example: <code>UP61S6030</code>\n"
            "📄 Example: <code>MH04AB1234</code>\n\n"
            "💎 Cost: 1 credit per search"
        )
    elif data == 'menu_upi':
        edit_message(chat_id, message_id,
            "💳 <b>UPI Search</b>\n\n"
            "Send UPI ID in format: number@bank\n"
            "📱 Example: <code>9038103500@ybl</code>\n"
            "🏦 Example: <code>merchant@paytm</code>\n\n"
            "💎 Cost: 1 credit per search"
        )
    elif data == 'menu_aadhar':
        edit_message(chat_id, message_id,
            "🆔 <b>Aadhaar Search</b>\n\n"
            "Send 12-digit Aadhaar number\n"
            "📄 Example: <code>284495408590</code>\n\n"
            "💎 Cost: 1 credit per search"
        )
    elif data == 'menu_pak':
        edit_message(chat_id, message_id,
            "🇵🇰 <b>Pakistan Number Search</b>\n\n"
            "Send 12-digit Pakistan number starting with 92\n"
            "📄 Example: <code>923362006909</code>\n\n"
            "💎 Cost: 1 credit per search"
        )
    elif data == 'menu_family':
        edit_message(chat_id, message_id,
            "👨‍👩‍👧 <b>Aadhaar to Family Search</b>\n\n"
            "Send 12-digit Aadhaar number\n"
            "📄 Example: <code>202372727238</code>\n\n"
            "💎 Cost: 1 credit per search"
        )
    elif data == 'menu_username':
        edit_message(chat_id, message_id,
            "🔁 To search Telegram username -> number, click this link which opens the username info bot:\n"
            f"{USERNAME_TO_BOT_LINK}\n\n"
            "Or use /username <username> and I will give you the referral link."
        )
    elif data == 'menu_profile':
        row = get_user_row(user_id)
        if not row:
            edit_message(chat_id, message_id, "❌ You are not registered yet. Use /start and join channel.")
            return
        credits = 'Unlimited' if user_id == ADMIN_ID else row['credits']
        edit_message(chat_id, message_id,
            f"👤 Profile Info:\n\nUsername: @{row['username']}\nID: {row['user_id']}\nPhone: {row.get('phone', 'Not provided')}\nCredits: {credits}"
        )
    elif data == 'menu_contact':
        edit_message(chat_id, message_id, f"📞 Contact admin: {ADMIN_USERNAME}")
    elif data == 'menu_recent':
        rows = get_recent_searches(user_id)
        if not rows:
            edit_message(chat_id, message_id, "🕒 No recent searches found.")
            return
        text = "🕒 Recent Searches:\n\n"
        for r in rows:
            dt = datetime.fromtimestamp(r['created_at']).strftime("%Y-%m-%d %H:%M")
            text += f"{dt} • {r['query_type']} → {r['query_value']}\nSummary: {r['result_summary'][:200]}\n\n"
        edit_message(chat_id, message_id, text)
    elif data == 'menu_daily':
        row = get_user_row(user_id)
        if not row:
            edit_message(chat_id, message_id, "❌ Register first using /start and join the channel.")
            return
        
        last = int(row.get('last_daily_bonus', 0))
        now = int(time.time())
        
        if user_id == ADMIN_ID:
            edit_message(chat_id, message_id, "🎁 Admin has unlimited credits. No daily bonus needed.")
            return
        
        if now - last >= DAILY_BONUS_COOLDOWN:
            modify_credits(user_id, DAILY_BONUS_CREDITS, True)
            db = get_db()
            if db:
                cursor = db.cursor()
                cursor.execute("UPDATE users SET last_daily_bonus = ? WHERE user_id = ?", (now, user_id))
                db.commit()
                db.close()
            edit_message(chat_id, message_id, f"🎉 Daily Bonus: You received {DAILY_BONUS_CREDITS} credits!")
        else:
            remaining = DAILY_BONUS_COOLDOWN - (now - last)
            hrs = remaining // 3600
            mins = (remaining % 3600) // 60
            edit_message(chat_id, message_id, f"⏳ Daily Bonus cooldown. Try after {hrs}h {mins}m.")
    elif data in ['view_users', 'broadcast', 'add_credits', 'remove_credits']:
        handle_admin_callback(data, chat_id, message_id, user_id)
    elif data in ['quick_aadhar', 'quick_family']:
        handle_quick_search_callback(data, chat_id, user_id)

def handle_admin_callback(data: str, chat_id: int, message_id: int, user_id: int):
    if user_id != ADMIN_ID:
        edit_message(chat_id, message_id, "❌ Access denied!")
        return
    
    if data == 'view_users':
        users = get_all_users()
        if not users:
            edit_message(chat_id, message_id, "👥 No users yet!", admin_panel_keyboard())
            return
        
        text = f"👥 All Users ({len(users)}):\n\n"
        for u in users:
            credits = 'Unlimited' if u['user_id'] == ADMIN_ID else u['credits']
            text += f"🆔 {u['user_id']} • @{u['username']} • Credits: {credits}\n"
        
        edit_message(chat_id, message_id, text, admin_panel_keyboard())
        
    elif data == 'broadcast':
        set_admin_state('broadcast_mode', True)
        edit_message(chat_id, message_id, "📢 Send the broadcast message now (as a reply to this chat).", admin_panel_keyboard())
        
    elif data in ['add_credits', 'remove_credits']:
        set_admin_state('credit_action', 'add' if data == 'add_credits' else 'remove')
        edit_message(chat_id, message_id, "➡️ Send: @username_or_id <amount> (example: @rock 10)", admin_panel_keyboard())

def handle_quick_search_callback(data: str, chat_id: int, user_id: int):
    text = get_last_12_digit(user_id)
    if not text:
        send_message(chat_id, "❌ No recent 12-digit number found. Please send a new number.")
        return
    
    send_chat_action(chat_id)
    
    if data == 'quick_aadhar':
        results = query_aadhar_api(text)
        qtype = 'Aadhaar Search (quick)'
    else:
        results = query_family_api(text)
        qtype = 'Aadhaar Family Search (quick)'
    
    result_text = format_results(results)
    log_search(user_id, qtype, text, result_text[:400])
    
    credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
    search_type = 'Aadhaar' if data == 'quick_aadhar' else 'Aadhaar family'
    msg = f"✅ {search_type} {text} processed!\n💎 Credits left: {credits_left}\n\n{result_text}"
    send_message(chat_id, msg)

def handle_command(chat_id: int, user_id: int, command: str, args: List[str], username: str, first_name: str):
    if command == '/start':
        handle_start(chat_id, user_id, username, first_name)
        
    elif command == '/num':
        if not args:
            send_message(chat_id, "❌ Please provide a number: /num xxxxxxxxxx")
            return
        
        phone = ''.join(args).strip()
        if not phone.isdigit() or len(phone) not in [10, 11, 12, 13, 14, 15]:
            send_message(chat_id, "❌ Invalid number format. Send digits only (10-15 digits).")
            return
        
        if is_new_user(user_id):
            send_message(chat_id, "❌ Please join the channel first using /start and the 'I Joined' button.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}. Contact {ADMIN_USERNAME}")
            return
        
        send_chat_action(chat_id, 'typing')
        update_phone(user_id, phone)
        
        results = query_main_api(phone)
        result_text = format_results(results)
        log_search(user_id, 'Number Search', phone, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ Phone number {phone} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        
    elif command == '/vehicle':
        if not args:
            send_message(chat_id, "❌ Provide RC/Registration number: /vehicle UP61S6030\n\n💡 Example: /vehicle MH04AB1234")
            return
        
        rc = ''.join(args).upper().strip()
        if len(rc) < 8:
            send_message(chat_id, "❌ Invalid RC format. Should be like: UP61S6030\n\n💡 Format: STATE##XXXXX")
            return
        
        if is_new_user(user_id):
            send_message(chat_id, "❌ Please join the channel first using /start.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
            return
        
        send_chat_action(chat_id, 'typing')
        results = query_vehicle_api(rc)
        result_text = format_results(results)
        log_search(user_id, 'Vehicle Search', rc, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ Vehicle {rc} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        
    elif command == '/upi':
        if not args:
            send_message(chat_id, "❌ Provide UPI ID: /upi 9038103500@ybl\n\n💡 Example: /upi merchant@paytm")
            return
        
        upi_id = ''.join(args).strip()
        if '@' not in upi_id:
            send_message(chat_id, "❌ Invalid UPI format. Must contain '@'\n\n💡 Example: /upi 9038103500@ybl")
            return
        
        if is_new_user(user_id):
            send_message(chat_id, "❌ Please join the channel first using /start.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
            return
        
        send_chat_action(chat_id, 'typing')
        results = query_upi_api(upi_id)
        result_text = format_results(results)
        log_search(user_id, 'UPI Search', upi_id, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ UPI {upi_id} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        
    elif command == '/aadhar':
        if not args:
            send_message(chat_id, "❌ Provide Aadhaar number: /aadhar 284495408590\n\n💡 Example: /aadhar 123456789012")
            return
        
        aadhar = ''.join(args).strip()
        if not aadhar.isdigit() or len(aadhar) != 12:
            send_message(chat_id, "❌ Invalid Aadhaar format. Must be 12 digits.\n\n💡 Example: /aadhar 284495408590")
            return
        
        if is_new_user(user_id):
            send_message(chat_id, "❌ Please join the channel first using /start.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
            return
        
        send_chat_action(chat_id, 'typing')
        results = query_aadhar_api(aadhar)
        result_text = format_results(results)
        log_search(user_id, 'Aadhaar Search', aadhar, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ Aadhaar {aadhar} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        
    elif command == '/pak':
        if not args:
            send_message(chat_id, "❌ Provide Pakistan number: /pak 923362006909\n\n💡 Example: /pak 923362006909")
            return
        
        pak_number = ''.join(args).strip()
        if not pak_number.isdigit() or len(pak_number) != 12 or not pak_number.startswith('92'):
            send_message(chat_id, "❌ Invalid Pakistan number format. Must be 12 digits starting with 92.\n\n💡 Example: /pak 923362006909")
            return
        
        if is_new_user(user_id):
            send_message(chat_id, "❌ Please join the channel first using /start.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
            return
        
        send_chat_action(chat_id, 'typing')
        results = query_pak_api(pak_number)
        result_text = format_results(results)
        log_search(user_id, 'Pakistan Search', pak_number, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ Pakistan number {pak_number} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        
    elif command == '/family':
        if not args:
            send_message(chat_id, "❌ Provide Aadhaar number: /family 202372727238\n\n💡 Example: /family 202372727238")
            return
        
        aadhar = ''.join(args).strip()
        if not aadhar.isdigit() or len(aadhar) != 12:
            send_message(chat_id, "❌ Invalid Aadhaar format. Must be 12 digits.\n\n💡 Example: /family 202372727238")
            return
        
        if is_new_user(user_id):
            send_message(chat_id, "❌ Please join the channel first using /start.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
            return
        
        send_chat_action(chat_id, 'typing')
        results = query_family_api(aadhar)
        result_text = format_results(results)
        log_search(user_id, 'Aadhaar Family Search', aadhar, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ Aadhaar family {aadhar} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        
    elif command == '/username':
        if not args:
            send_message(chat_id, "❌ Use: /username <telegram_username> (without @). Example: /username rock123")
            return
        
        uname = ''.join(args).strip().lstrip('@')
        link = USERNAME_TO_BOT_LINK.format(uname)
        
        send_message(chat_id,
            f"🔁 To search username '{uname}' you can use this tool:\n{link}\n\n"
            "Note: This opens the Telegram username info bot."
        )
        
    elif command == '/recent':
        rows = get_recent_searches(user_id)
        if not rows:
            send_message(chat_id, "🕒 No recent searches found.")
            return
        
        text = "🕒 Recent Searches:\n\n"
        for r in rows:
            dt = datetime.fromtimestamp(r['created_at']).strftime("%Y-%m-%d %H:%M")
            text += f"{dt} • {r['query_type']} → {r['query_value']}\nSummary: {r['result_summary'][:200]}\n\n"
        
        send_message(chat_id, text)
        
    elif command == '/admcmd':
        if user_id != ADMIN_ID:
            send_message(chat_id, "❌ Access denied! You are not the admin.")
            return
        
        send_message(chat_id, "🔧 Admin Panel Opened! Choose an option:", admin_panel_keyboard())
        
    else:
        send_message(chat_id, "❌ Unknown command. Use /start to begin.")

def handle_message(chat_id: int, user_id: int, text: str, chat_type: str):
    # Group handler to add for broadcast
    if chat_type in ['group', 'supergroup']:
        try:
            response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
            bot_id = response.json()['result']['id']
            member = get_chat_member(chat_id, bot_id)
            
            if member.get('result', {}).get('status') == 'administrator':
                db = get_db()
                if db:
                    cursor = db.cursor()
                    cursor.execute("SELECT 1 FROM broadcast_chats WHERE chat_id = ?", (chat_id,))
                    
                    if cursor.fetchone() is None:
                        cursor.execute("INSERT OR IGNORE INTO broadcast_chats (chat_id, chat_type, title) VALUES (?, ?, ?)",
                                      (chat_id, chat_type, 'Group'))
                        db.commit()
                        logger(f"Added group {chat_id} to broadcast list")
                    db.close()
        except:
            pass
        return  # Don't process further in groups unless needed

    # Private chat only
    if chat_type != 'private':
        return

    # Admin modes
    if user_id == ADMIN_ID:
        if get_admin_state('broadcast_mode'):
            message = text
            users_success = 0
            groups_success = 0

            # Broadcast to users
            users = get_all_users()
            logger(f"Attempting broadcast to {len(users)} users")
            
            for u in users:
                if u['user_id'] == ADMIN_ID:
                    continue  # Skip admin
                
                if send_message(u['user_id'], f"📢 Broadcast from Admin:\n\n{message}"):
                    users_success += 1
                    logger(f"Broadcast sent to user {u['user_id']}")

            # Broadcast to groups
            groups = get_broadcast_groups()
            logger(f"Attempting broadcast to {len(groups)} groups")
            
            for g in groups:
                if send_message(g, f"📢 Broadcast from Admin:\n\n{message}"):
                    groups_success += 1
                    logger(f"Broadcast sent to group {g}")

            response = (f"📢 Broadcast sent!\n✅ Users: {users_success}/{len(users)}\n"
                       f"✅ Groups: {groups_success}/{len(groups)}\n")
            
            send_message(chat_id, response)
            set_admin_state('broadcast_mode', False)
            return

        credit_action = get_admin_state('credit_action')
        if credit_action:
            parts = text.split(' ', 1)
            if len(parts) != 2:
                send_message(chat_id, "❌ Invalid format. Use: @username_or_id <amount>")
                set_admin_state('credit_action', None)
                return
            
            identifier, amount_s = parts
            try:
                amount = int(amount_s)
            except ValueError:
                send_message(chat_id, "❌ Invalid amount. Must be a number.")
                set_admin_state('credit_action', None)
                return
            
            if amount <= 0:
                send_message(chat_id, "❌ Invalid amount. Must be positive number.")
                set_admin_state('credit_action', None)
                return
            
            target = None
            if identifier.startswith('@'):
                db = get_db()
                if db:
                    cursor = db.cursor()
                    cursor.execute("SELECT user_id FROM users WHERE username = ?", (identifier[1:],))
                    row = cursor.fetchone()
                    target = row['user_id'] if row else None
                    db.close()
            else:
                try:
                    target = int(identifier)
                except ValueError:
                    target = None
            
            if not target:
                send_message(chat_id, "❌ Target user not found.")
                set_admin_state('credit_action', None)
                return
            
            add = (credit_action == 'add')
            if modify_credits(target, amount, add):
                action = 'added' if add else 'removed'
                send_message(chat_id, f"✅ {amount} credits {action} for user {target}.")
                
                # Notify target user
                target_credits = get_user_credits(target)
                send_message(target, f"⚙️ Admin has {action} {amount} credits from your account.\n💎 Your current credits: {target_credits}")
            else:
                send_message(chat_id, "❌ Failed to modify credits.")
            
            set_admin_state('credit_action', None)
            return

    # Quick searches for regular users
    text = text.strip()
    
    if '@' in text and len(text) > 5:  # UPI
        if is_new_user(user_id):
            send_message(chat_id, "❌ Register first using /start and join the channel.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
            return
        
        send_chat_action(chat_id, 'typing')
        results = query_upi_api(text)
        result_text = format_results(results)
        log_search(user_id, 'UPI Search (quick)', text, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ UPI {text} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        return

    # Vehicle RC pattern
    import re
    if re.match(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$', text, re.IGNORECASE):
        if is_new_user(user_id):
            send_message(chat_id, "❌ Register first using /start and join the channel.")
            return
        
        if not deduct_credits(user_id, CREDITS_PER_SEARCH):
            send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
            return
        
        send_chat_action(chat_id, 'typing')
        results = query_vehicle_api(text)
        result_text = format_results(results)
        log_search(user_id, 'Vehicle Search (quick)', text, result_text[:400])
        
        credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
        send_chat_action(chat_id, 'typing')
        send_message(chat_id, f"✅ Vehicle {text} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
        return

    if text.isdigit():
        if len(text) == 12 and text.startswith('92'):  # Pakistan
            if is_new_user(user_id):
                send_message(chat_id, "❌ Register first using /start and join the channel.")
                return
            
            if not deduct_credits(user_id, CREDITS_PER_SEARCH):
                send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
                return
            
            send_chat_action(chat_id, 'typing')
            results = query_pak_api(text)
            result_text = format_results(results)
            log_search(user_id, 'Pakistan Search (quick)', text, result_text[:400])
            
            credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
            send_chat_action(chat_id, 'typing')
            send_message(chat_id, f"✅ Pakistan number {text} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
            return
            
        elif len(text) == 12:  # Aadhaar or Family
            if is_new_user(user_id):
                send_message(chat_id, "❌ Register first using /start and join the channel.")
                return
            
            if not deduct_credits(user_id, CREDITS_PER_SEARCH):
                send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
                return
            
            update_last_12_digit(user_id, text)
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🔍 Aadhaar Search', 'callback_data': 'quick_aadhar'},
                        {'text': '👨‍👩‍👧 Family Search', 'callback_data': 'quick_family'}
                    ]
                ]
            }
            
            send_message(chat_id, f"⚖️ 12-digit number detected: {text}\n\nPlease choose an option:", keyboard)
            return
            
        elif len(text) in [10, 11, 12, 13, 14, 15]:  # Phone
            if is_new_user(user_id):
                send_message(chat_id, "❌ Register first using /start and join the channel.")
                return
            
            if not deduct_credits(user_id, CREDITS_PER_SEARCH):
                send_message(chat_id, f"❌ Insufficient credits. Current: {get_user_credits(user_id)}")
                return
            
            update_phone(user_id, text)
            send_chat_action(chat_id, 'typing')
            
            results = query_main_api(text)
            result_text = format_results(results)
            log_search(user_id, 'Number Search (quick)', text, result_text[:400])
            
            credits_left = 'Unlimited' if user_id == ADMIN_ID else get_user_credits(user_id)
            send_chat_action(chat_id, 'typing')
            send_message(chat_id, f"✅ Phone {text} processed!\n💎 Credits left: {credits_left}\n\n{result_text}")
            return
    
    # If no pattern matched, show main menu
    send_message(chat_id, "🤔 I didn't understand that. Use /start to see available options.", main_menu_keyboard())

# ----------------------------
# POLLING MAIN LOOP
# ----------------------------
def get_updates(offset: int = None) -> List[Dict]:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return data.get('result', [])
        return []
    except requests.RequestException as e:
        logger(f"Error getting updates: {e}", 'ERROR')
        return []

def process_update(update: Dict):
    logger(f"Processing update: {update.get('update_id')}")
    
    message = update.get('message')
    callback_query = update.get('callback_query')
    
    if callback_query:
        callback_id = callback_query['id']
        user_id = callback_query['from']['id']
        chat_id = callback_query['message']['chat']['id']
        message_id = callback_query['message']['message_id']
        data = callback_query['data']
        
        logger(f"Callback received: {data} from user {user_id}")
        handle_callback(callback_id, chat_id, message_id, user_id, data)
        
    elif message:
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '')
        chat_type = message['chat']['type']
        username = message['from'].get('username', '')
        first_name = message['from'].get('first_name', '')
        
        logger(f"Message received from {user_id}: {text}")
        
        if text.startswith('/'):
            parts = text.split(' ', 1)
            command = parts[0].lower()
            args = parts[1].split() if len(parts) > 1 else []
            
            handle_command(chat_id, user_id, command, args, username, first_name)
        else:
            handle_message(chat_id, user_id, text, chat_type)

def main():
    logger("Starting Telegram Bot with polling...")
    
    # Initialize database
    if not init_db():
        logger("Failed to initialize database. Exiting.", 'ERROR')
        return
    
    logger("Bot started successfully. Press Ctrl+C to stop.")
    
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                process_update(update)
                offset = update['update_id'] + 1
            
            # Small delay to prevent excessive requests
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            logger("Bot stopped by user.")
            break
        except Exception as e:
            logger(f"Error in main loop: {e}", 'ERROR')
            time.sleep(5)  # Wait before retrying

if __name__ == '__main__':
    setup_logging()
    main()
