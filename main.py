import telebot
from telebot import types
import json
import os

# --- Configuration ---
TOKEN = '8718072729:AAHESv3pzxKAgeh_dD-9GSRGhJgm6khAfXE'
ADMIN_USERNAME = 'leniin9'
bot = telebot.TeleBot(TOKEN)

# --- Database Setup ---
DB_FILE = 'db.json'

def load_db():
    if not os.path.exists(DB_FILE):
        return {
            'users': {},
            'channels': [],
            'price_message': """💳 لشحن نقاط البوت تواصل مع الوكيل @leniin9

💡 جدول الأسعار:
 • $1 = 12,000 نقطة 💎
 • $2 = 24,000 نقطة 💎
 • $3 = 36,000 نقطة 💎
 • $4 = 48,000 نقطة 💎
 • $5 = 60,000 نقطة 💎
 • $10 = 120,000 نقطة 💎
 • $20 = 240,000 نقطة 💎
 • $50 = 600,000 نقطة 💎
 • $100 = 1,200,000 نقطة 💎""",
            'invoice_counter': 1,
            'admin_id': None,
            'admin_phone': '07702049049'
        }
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

db = load_db()

# --- Helper Functions ---
def is_subscribed(user_id):
    if not db['channels']:
        return True
    for channel in db['channels']:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            print(f"Error checking subscription for {channel}: {e}")
            # If bot is not admin in channel, skip check or handle error
    return True

def is_admin(message):
    return message.from_user.username == ADMIN_USERNAME or message.from_user.id == db['admin_id']

# --- Keyboards ---
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('💎 أسعار النقاط', callback_data='main_prices'),
        types.InlineKeyboardButton('💸 الشحن عبر التحويل', callback_data='main_transfer'),
        types.InlineKeyboardButton('💳 شحن عبر الكارت', callback_data='main_card')
    )
    return markup

def get_admin_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('إضافة قناة اشتراك', callback_data='admin_add_channel'),
               types.InlineKeyboardButton('حذف قناة اشتراك', callback_data='admin_del_channel'))
    markup.add(types.InlineKeyboardButton('تعديل أسعار الشحن', callback_data='admin_edit_prices'))
    markup.add(types.InlineKeyboardButton('البحث عن شخص', callback_data='admin_search_user'))
    return markup

# --- State Management ---
user_states = {}

# --- Bot Handlers ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    if user_id not in db['users']:
        db['users'][user_id] = {
            'id': user_id,
            'username': message.from_user.username,
            'phone': None,
            'points': 0,
            'invoices': []
        }
        save_db(db)

    # Admin ID capture
    if message.from_user.username == ADMIN_USERNAME and not db['admin_id']:
        db['admin_id'] = message.from_user.id
        save_db(db)

    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in db['channels']:
            markup.add(types.InlineKeyboardButton(f"انضم هنا: {ch}", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton('تحقق من الانضمام', callback_data='check_sub'))
        bot.send_message(message.chat.id, '⚠️ يجب عليك الاشتراك في القنوات الإجبارية أولاً لتتمكن من استخدام البوت.', reply_markup=markup)
        return

    if not db['users'][user_id]['phone']:
        bot.send_message(message.chat.id, '👋 أهلاً بك في بوت شحن النقاط.\n📱 يرجى إرسال رقمك الآسيا سيل لتسجيل الدخول:', reply_markup=types.ReplyKeyboardRemove())
        user_states[user_id] = {'step': 'wait_phone'}
    else:
        user_data = db['users'][user_id]
        welcome_text = f"""👋 أهلاً بك مجدداً في بوت الشحن!
        
🆔 الايدي الخاص بك: `{user_id}`
💎 رصيدك الحالي: {user_data['points']} نقطة

اختر من القائمة أدناه 👇"""
        bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if is_admin(message):
        bot.send_message(message.chat.id, '🛠️ لوحة تحكم الأدمن:', reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = str(message.from_user.id)
    text = message.text

    # Check subscription first
    if not is_subscribed(message.from_user.id):
        return start(message)

    # Handle Phone Registration
    if user_id in user_states and user_states[user_id].get('step') == 'wait_phone':
        if text.isdigit():
            db['users'][user_id]['phone'] = text
            save_db(db)
            del user_states[user_id]
            bot.send_message(message.chat.id, '✅ تم تسجيل رقمك بنجاح. يمكنك الآن استخدام البوت.', reply_markup=get_main_keyboard())
        else:
            bot.send_message(message.chat.id, '📱 يرجى إرسال رقمك الآسيا سيل (أرقام فقط):')
        return

    # Main Buttons (Handled by callback now)
    # Admin Steps
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['step'] == 'transfer_amount':
            state['amount'] = text
            state['step'] = 'transfer_wait_screenshot'
            bot.send_message(message.chat.id, f"✅ المبلغ: {text}\n📞 يرجى تحويل الرصيد إلى هذا الرقم: {db['admin_phone']}\n📸 بعد التحويل، أرسل سكرين (صورة) إثبات للحوالة:")
        
        elif state['step'] == 'card_amount':
            state['amount'] = text
            state['step'] = 'card_wait_screenshot'
            bot.send_message(message.chat.id, f"✅ المبلغ: {text}\n📸 أرسل سكرين للكارت والرقم السري موضح أو مشخوط:")

        elif state['step'] == 'admin_add_channel_input':
            db['channels'].append(text)
            save_db(db)
            del user_states[user_id]
            bot.send_message(message.chat.id, f"✅ تم إضافة القناة: {text}")

        elif state['step'] == 'admin_del_channel_input':
            db['channels'] = [c for c in db['channels'] if c != text]
            save_db(db)
            del user_states[user_id]
            bot.send_message(message.chat.id, f"✅ تم حذف القناة: {text}")

        elif state['step'] == 'admin_edit_prices_input':
            db['price_message'] = text
            save_db(db)
            del user_states[user_id]
            bot.send_message(message.chat.id, '✅ تم تحديث رسالة الأسعار.')

        elif state['step'] == 'admin_search_user_input':
            search_id = text
            user = db['users'].get(search_id)
            if user:
                bot.send_message(message.chat.id, f"👤 معلومات المستخدم:\n🆔 الايدي: {user['id']}\n📞 الرقم: {user['phone'] or 'غير مسجل'}\n💎 النقاط: {user['points']}\n📊 عدد التحويلات: {len(user['invoices'])}")
            else:
                bot.send_message(message.chat.id, '❌ لم يتم العثور على هذا الشخص.')
            del user_states[user_id]

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = str(message.from_user.id)
    if user_id not in user_states:
        return

    state = user_states[user_id]
    if state['step'] in ['transfer_wait_screenshot', 'card_wait_screenshot']:
        photo_id = message.photo[-1].file_id
        invoice_id = db['invoice_counter']
        db['invoice_counter'] += 1
        type_name = 'تحويل' if state['step'] == 'transfer_wait_screenshot' else 'كارت'
        
        invoice = {
            'id': invoice_id,
            'user_id': user_id,
            'amount': state.get('amount'),
            'type': type_name,
            'photo': photo_id
        }
        
        db['users'][user_id]['invoices'].append(invoice)
        save_db(db)

        # Send to Admin
        if db['admin_id']:
            bot.send_photo(db['admin_id'], photo_id, caption=f"🧾 فاتورة جديدة #{invoice_id}\n👤 ايدي الشخص: {user_id}\n📞 رقم الشخص: {db['users'][user_id]['phone']}\n💰 المبلغ: {state.get('amount')}\n🛠️ النوع: {type_name}")

        del user_states[user_id]
        bot.send_message(message.chat.id, '✅ تم إرسال الفاتورة للأدمن بنجاح. سيتم التحقق منها قريباً.')

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id

    if call.data == 'check_sub':
        if is_subscribed(call.from_user.id):
            bot.answer_callback_query(call.id, '✅ شكراً لانضمامك!')
            bot.send_message(chat_id, '✅ تم التحقق. يمكنك الآن استخدام البوت /start')
        else:
            bot.answer_callback_query(call.id, '❌ لم تنضم لجميع القنوات بعد.', show_alert=True)

    elif call.data == 'main_prices':
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, db['price_message'])

    elif call.data == 'main_transfer':
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'step': 'transfer_amount'}
        bot.send_message(chat_id, '💰 اكتب المبلغ المراد تحويله ($):')

    elif call.data == 'main_card':
        bot.answer_callback_query(call.id)
        user_states[user_id] = {'step': 'card_amount'}
        bot.send_message(chat_id, '💰 اكتب المبلغ المراد تحويله ($):')

    elif call.data == 'admin_add_channel':
        user_states[user_id] = {'step': 'admin_add_channel_input'}
        bot.send_message(chat_id, '🔗 أرسل معرف القناة (مثال: @channel):')

    elif call.data == 'admin_del_channel':
        user_states[user_id] = {'step': 'admin_del_channel_input'}
        bot.send_message(chat_id, '🔗 أرسل معرف القناة المراد حذفها:')

    elif call.data == 'admin_edit_prices':
        user_states[user_id] = {'step': 'admin_edit_prices_input'}
        bot.send_message(chat_id, '📝 أرسل رسالة الأسعار الجديدة:')

    elif call.data == 'admin_search_user':
        user_states[user_id] = {'step': 'admin_search_user_input'}
        bot.send_message(chat_id, '🆔 أرسل ايدي الشخص المراد البحث عنه:')

if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
