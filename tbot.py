import json
import random
import io
import datetime
import os
import asyncio
import aiohttp
from threading import RLock

from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
from telethon.errors.rpcerrorlist import MessageNotModifiedError

API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_TOKEN = "8741721880:AAH7Cpmc-SOCdHdSwjR3LoWM9ZUXEvbUAu0"

client = TelegramClient('bot_session', API_ID, API_HASH)

DATA_FILE = "data.json"
ADMIN_FILE = "admin.json"
ADMIN_USERNAMES = ["leniin9"]
START_TIME = datetime.datetime.now()

USER_STATE = {}  # بديل context.user_data الخاص بـ PTB

# ================= الإعدادات الافتراضية =================
DEFAULT_ADMIN_DATA = {
    "settings": {
        "required_channels": ["@Rashqkum"], 
        "maintenance_mode": False,
        "anti_spam": True,
        "transfers_enabled": True,
        "invite_reward": 50,
        "gift_reward": 20,
        "transfer_tax": 5, 
        "promo_cost": 15,    
        "sub_reward": 10,
        "points_per_dollar": 12000,
        "welcome_message": "مرحبا بك في بوت رشقكم المطور 🚀\nاكتشف أقوى خدمات الرشق وتمويل القنوات.",
        "terms_text": "شروط الاستخدام:\n1. لا نتحمل مسؤولية الطلبات الخاطئة.\n2. يمنع استخدام حسابات وهمية.\n3. النقاط غير قابلة للاسترداد المالي.",
        "charge_info": "لشحن نقاط البوت التواصل مع الوكيل 👇@Bellmen1\n\n💎 أسعار النقاط الرسمية:\n{price_list}",
        "support_text": "اكتب رسالتك وسنقوم بالرد عليك في أقرب وقت 📞:",
        "orders_completed_fake": 0,
        "users_fake": 0,
        "dynamic_admins":[],
        "promo_codes": {},
        "smm_api_url": "https://kd1s.com/api/v2", 
        "smm_api_key": "36a4feec0ba7fb6d6bb6f8a9a528c393", 
        "smm_sections": {}, 
        "smm_services": {}  
    },
    "menus": {
        "main_menu": {
            "name": "القائمة الرئيسية",
            "text": "{welcome}\n\n💡 **نظام الأسعار:**\n💵 كل 1$ دولار = {points_per_dollar} نقطة.\n\n👥] نقاطك : {coins}\n🆔] ايديك : {user_id}\n✅ طلباتك الناجحة : {my_orders}",
            "buttons": [[{"text": "📦 قسم الخدمات (الرشق)", "callback_data": "usr_smm_sections|0"}],[{"text": "🚀 تمويل قناتك للأعضاء", "callback_data": "usr_promote_channel"}],[{"text": "👤 الحساب", "callback_data": "account"}, {"text": "🪙 تجميع النقاط (Gold)", "callback_data": "collect_coins"}],[{"text": "🔄 تحويل نقاط", "callback_data": "transfer_points"}, {"text": "🎫 استخدام كود", "callback_data": "use_code"}],[{"text": "🧮 حاسبة الأسعار", "callback_data": "calc_prices"}],[{"text": "📋 طلباتي", "callback_data": "my_orders"}, {"text": "🔍 حالة الطلب", "callback_data": "order_status"}],[{"text": "📊 الاحصائيات", "callback_data": "stats"}, {"text": "💳 شحن نقاط", "callback_data": "charge"}],[{"text": "📞 الدعم الفني", "callback_data": "support"}, {"text": "⚖️ الشروط", "callback_data": "terms"}],[{"text": "🔱 قنوات البوت الرسمية 🔱", "url": "https://t.me/skyline111bot"}]
            ]
        },
        "account_menu": {
            "name": "قائمة الحساب",
            "text": "👤 حسابك\n\n💰 النقاط: {coins}\n💸 المصروف: {used_coins}\n👥 الدعوات: {invite_count}\n🎁 الهدية: {gift_text}\n👑 الرتبة: {vip_status}",
            "buttons": [[{"text": "🎁 الهدية اليومية", "callback_data": "claim_gift"}, {"text": "🔗 رابط الدعوة", "callback_data": "invite_link"}],[{"text": "⬅️ رجوع", "callback_data": "back_main"}]]
        },
        "collect_coins_menu": {
            "name": "قائمة التجميع",
            "text": "اختر طريقة تجميع النقاط 🪙:",
            "buttons": [[{"text": "🌟 قنوات الأعضاء (Gold)", "callback_data": "usr_earn_promos"}],[{"text": "🔗 دعوة الأصدقاء", "callback_data": "invite_link"}],[{"text": "⬅️ رجوع", "callback_data": "back_main"}]]
        },
        "stats_menu": {
            "name": "قائمة الاحصائيات",
            "text": "📊 إحصائيات النظام:\n\n👥 المستخدمين: {users_count}\n✅ طلبات الرشق: {orders_completed}\n\n🏆 أعلى الداعين:\n{top_inviters}",
            "buttons": [[{"text": "⬅️ رجوع", "callback_data": "back_main"}]]
        }
    }
}

""" ================= إدارة قواعد البيانات ================= """
class DBManager:
    _lock = RLock()
    @staticmethod
    def _read_json(file_path, default):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except:
            DBManager._write_json(file_path, default)
            return default
    @staticmethod
    def _write_json(file_path, data):
        with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

class AdminManager(DBManager):
    @classmethod
    def _get_data(cls):
        with cls._lock: return cls._read_json(ADMIN_FILE, DEFAULT_ADMIN_DATA)
    @classmethod
    def _save_data(cls, data):
        with cls._lock: cls._write_json(ADMIN_FILE, data)
    @classmethod
    def get_setting(cls, key, default=None): return cls._get_data().get("settings", {}).get(key, default)
    @classmethod
    def set_setting(cls, key, value):
        data = cls._get_data()
        data.setdefault("settings", {})[key] = value
        cls._save_data(data)
    @classmethod
    def get_menu(cls, menu_id): return cls._get_data().get("menus", {}).get(menu_id, {})
    @classmethod
    def get_all_menus(cls): return cls._get_data().get("menus", {})
    @classmethod
    def update_menu_text(cls, menu_id, text):
        data = cls._get_data()
        if menu_id in data["menus"]:
            data["menus"][menu_id]["text"] = text; cls._save_data(data)
    @classmethod
    def update_button(cls, menu_id, r, c, btn_data):
        data = cls._get_data()
        try: data["menus"][menu_id]["buttons"][r][c] = btn_data; cls._save_data(data)
        except IndexError: pass
    @classmethod
    def move_button(cls, menu_id, r_idx, c_idx, direction):
        data = cls._get_data()
        if menu_id not in data["menus"]: return
        buttons = data["menus"][menu_id]["buttons"]
        try:
            btn = buttons[r_idx].pop(c_idx)
            if not buttons[r_idx]: buttons.pop(r_idx); r_idx = max(0, r_idx - 1)
            if direction == "up":
                if r_idx > 0: buttons[r_idx - 1].append(btn)
                else: buttons.insert(0, [btn])
            elif direction == "down":
                if r_idx < len(buttons) - 1: buttons[r_idx + 1].append(btn)
                else: buttons.append([btn])
            elif direction == "left": buttons[r_idx].insert(max(0, c_idx - 1), btn)
            elif direction == "right": buttons[r_idx].insert(min(len(buttons[r_idx]), c_idx + 1), btn)
            data["menus"][menu_id]["buttons"] =[r for r in buttons if r]
            cls._save_data(data)
        except IndexError: pass
    @classmethod
    def add_button(cls, menu_id, btn_data, new_row=True):
        data = cls._get_data()
        if menu_id in data["menus"]:
            if new_row or not data["menus"][menu_id]["buttons"]: data["menus"][menu_id]["buttons"].append([btn_data])
            else: data["menus"][menu_id]["buttons"][-1].append(btn_data)
            cls._save_data(data)
    @classmethod
    def delete_button(cls, menu_id, r, c):
        data = cls._get_data()
        try:
            del data["menus"][menu_id]["buttons"][r][c]
            if not data["menus"][menu_id]["buttons"][r]: del data["menus"][menu_id]["buttons"][r]
            cls._save_data(data)
        except: pass
    @classmethod
    def remove_plus_channel(cls, ch):
        data = cls._get_data()
        if ch in data["settings"]["required_channels"]: data["settings"]["required_channels"].remove(ch)
        cls._save_data(data)
    @classmethod
    def add_plus_channel(cls, ch):
        data = cls._get_data()
        if ch not in data["settings"]["required_channels"]: data["settings"]["required_channels"].append(ch)
        cls._save_data(data)

class DataManager(DBManager):
    @classmethod
    def _get_data(cls):
        with cls._lock: return cls._read_json(DATA_FILE, {"users": {}, "global_stats": {"orders_completed": 0}, "promotions": {}})
    @classmethod
    def _save_data(cls, data):
        with cls._lock: cls._write_json(DATA_FILE, data)
    @classmethod
    def get_user(cls, uid):
        data = cls._get_data()
        suid = str(uid)
        changed = False
        if suid not in data["users"]:
            data["users"][suid] = {
                "coins": 0, "used_coins": 0, "invite_count": 0, "orders":[],
                "invite_id": f"INV{random.randint(100000, 999999)}",
                "gift_claimed": False, "is_banned": False, "is_vip": False, 
                "used_promos": [], "subscribed_promos":[],
                "subscriptions": {"plus": {}, "gold": {}}
            }
            changed = True
        else:
            if "subscriptions" not in data["users"][suid]:
                data["users"][suid]["subscriptions"] = {"plus": {}, "gold": {}}
                changed = True
        if changed:
            cls._save_data(data)
        return data["users"][suid]
    @classmethod
    def save_user(cls, uid, user_data):
        data = cls._get_data()
        data["users"][str(uid)] = user_data
        cls._save_data(data)
        
    @classmethod
    def modify_user_coins(cls, uid, amount, force=False):
        with cls._lock:
            data = cls._get_data()
            suid = str(uid)
            if suid in data["users"]:
                if amount < 0 and not force and data["users"][suid]["coins"] < abs(amount):
                    return False
                data["users"][suid]["coins"] += amount
                if amount < 0: data["users"][suid]["used_coins"] += abs(amount)
                if data["users"][suid]["coins"] < 0: data["users"][suid]["coins"] = 0
                cls._save_data(data)
                return True
            return False
            
    @classmethod
    def get_all_user_ids(cls):
        with cls._lock: return list(cls._read_json(DATA_FILE, {}).get("users", {}).keys())
    @classmethod
    def get_stats(cls):
        data = cls._get_data()
        users = len(data["users"]) + AdminManager.get_setting("users_fake", 0)
        orders = data.get("global_stats", {}).get("orders_completed", 0) + AdminManager.get_setting("orders_completed_fake", 0)
        top = sorted([(k, v.get("invite_count", 0)) for k,v in data["users"].items() if v.get("invite_count", 0)>0], key=lambda x:x[1], reverse=True)[:5]
        return users, orders, top

def is_admin(user_id, username):
    if username and username.lower() in ADMIN_USERNAMES: return True
    return str(user_id) in AdminManager.get_setting("dynamic_admins",[])

def get_state(uid):
    if uid not in USER_STATE: USER_STATE[uid] = {}
    return USER_STATE[uid]

""" ================= API الاتصال بموقع الرشق باستخدام AioHTTP ================= """
class SMMAPI:
    @staticmethod
    async def call(action, **kwargs):
        url = AdminManager.get_setting("smm_api_url", "").strip()
        key = AdminManager.get_setting("smm_api_key", "").strip()
        if not url or not key: return {"error": "API is not configured."}
        params = {"key": key, "action": action}
        params.update(kwargs)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=params, timeout=15.0) as res:
                    return await res.json()
        except Exception as e: return {"error": str(e)}

def build_kb(buttons_list):
    kb = []
    for row in buttons_list:
        kb_row =[]
        for btn in row:
            if "url" in btn: kb_row.append(Button.url(btn["text"], btn["url"]))
            else: kb_row.append(Button.inline(btn["text"], btn["callback_data"].encode('utf-8')))
        kb.append(kb_row)
    return kb

def ib(text, data): return Button.inline(text, data.encode('utf-8'))
def ub(text, url): return Button.url(text, url)

""" ================= التحقق من الاشتراك ================= """
async def is_user_subbed(channel_username, user_id):
    try:
        await client(GetParticipantRequest(channel_username, user_id))
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        return False

async def enforce_subscription(event, user_id, username):
    if is_admin(user_id, username): return True
    channels = AdminManager.get_setting("required_channels",[])
    if not channels: return True
    
    u = DataManager.get_user(user_id)
    not_subbed =[]
    changed = False
    
    for ch in channels:
        subbed = await is_user_subbed(ch, user_id)
        if u["subscriptions"]["plus"].get(ch) != subbed:
            u["subscriptions"]["plus"][ch] = subbed
            changed = True
        if not subbed: not_subbed.append(ch)
            
    if changed: DataManager.save_user(user_id, u)
            
    if not_subbed:
        txt = "⛔️ **عذراً، يجب عليك الاشتراك في قنوات البوت الأساسية (Plus) أولاً:**\n\n"
        kb = [[ub(f"اشترك في {ch}", f"https://t.me/{ch[1:]}")] for ch in not_subbed]
        kb.append([ib("✅ تحقق من الاشتراك", "check_mandatory_sub")])
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.edit(txt, buttons=kb)
            else:
                await event.reply(txt, buttons=kb)
        except Exception: pass
        return False
    return True

async def send_dynamic_menu(event, user_id, username, menu_id, edit=True, extra_vars=None):
    user = DataManager.get_user(user_id)
    if user.get("is_banned") and not is_admin(user_id, username):
        text = "❌ عذرا، حسابك محظور من النظام."
        if edit and isinstance(event, events.CallbackQuery.Event): await event.edit(text)
        else: await client.send_message(user_id, text)
        return

    users_count, orders_count, top_inviters = DataManager.get_stats()
    menu_data = AdminManager.get_menu(menu_id)
    raw_text = menu_data.get("text", "القائمة")
    
    ppd = AdminManager.get_setting("points_per_dollar", 12000)
    prices_list =[1, 2, 3, 4, 5, 10, 20, 50, 100, 150]
    price_list_text = "\n".join([f" • ${d} = {d * ppd:,} نقطة 💎" for d in prices_list])
    
    inv_txt = "".join([f"🏅 {uid} - {c} دعوة\n" for uid, c in top_inviters])
    v_map = {
        "{coins}": f"{user['coins']:,}", "{user_id}": str(user_id), "{orders_completed}": str(orders_count),
        "{used_coins}": str(user.get('used_coins', 0)), "{invite_count}": str(user.get('invite_count', 0)),
        "{gift_text}": "متاحة" if not user.get("gift_claimed") else "تم الاستلام",
        "{users_count}": str(users_count), "{top_inviters}": inv_txt,
        "{welcome}": AdminManager.get_setting("welcome_message", ""),
        "{vip_status}": "VIP 👑" if user.get("is_vip") else "عادي 👤",
        "{my_orders}": str(len(user.get('orders',[]))),
        "{points_per_dollar}": f"{ppd:,}",
        "{price_list}": price_list_text
    }
    for k, v in v_map.items(): raw_text = raw_text.replace(k, str(v))
    if extra_vars:
        for k, v in extra_vars.items(): raw_text = raw_text.replace(f"{{{k}}}", str(v))

    kb = build_kb(menu_data.get("buttons",[]))
    try:
        if edit and isinstance(event, events.CallbackQuery.Event): 
            await event.edit(raw_text, buttons=kb)
        else: 
            await client.send_message(user_id, raw_text, buttons=kb)
    except MessageNotModifiedError: pass
    except Exception: pass

async def show_next_promo(event, user_id, is_skip=False):
    d = DataManager._get_data(); u = DataManager.get_user(user_id)
    st = get_state(user_id)
    promos = d.get("promotions", {}); skipped = st.get("skipped_promos", [])
    available =[ch for ch, p in promos.items() if ch not in u.get("subscribed_promos", []) and p["remains"] > 0 and ch not in skipped]
    
    if not available and skipped:
        if is_skip:
            try: await event.answer("🔄 لا توجد قنوات أخرى، تمت إعادة القائمة.", alert=True)
            except: pass
        st["skipped_promos"] = []
        available =[ch for ch, p in promos.items() if ch not in u.get("subscribed_promos", []) and p["remains"] > 0]
        
    if available:
        ch = available[0]; sub_reward = AdminManager.get_setting("sub_reward", 10)
        txt = f"🌟 اشترك في هذه القناة (Gold) لتربح {sub_reward} نقطة:\n\n{ch}\n\nبعد الاشتراك، اضغط تحقق ✅"
        kb = [[ub("📢 اشترك الآن", f"https://t.me/{ch[1:]}")], [ib("✅ تحقق من الاشتراك", f"usr_verify_promo|{ch}")],[ib("⏭ تخطي", f"usr_skip_promo|{ch}")],[ib("⬅️ رجوع", "collect_coins")]]
        try: await event.edit(txt, buttons=kb)
        except MessageNotModifiedError: pass
    else:
        try: await event.edit("♻️ لا توجد قنوات متاحة للتجميع حالياً، يرجى العودة لاحقاً.", buttons=[[ib("⬅️ رجوع", "collect_coins")]])
        except MessageNotModifiedError: pass

@client.on(events.NewMessage(pattern=r'^/start(?:\s+(.*))?$'))
async def start_command(event):
    user_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    
    if not await enforce_subscription(event, user_id, username): return
    if AdminManager.get_setting("maintenance_mode") and not is_admin(user_id, username):
        await event.reply("🛠 البوت في وضع الصيانة للتطوير. يرجى المحاولة لاحقاً.")
        return

    args = event.pattern_match.group(1)
    get_state(user_id).clear()
    
    data = DataManager._get_data()
    is_new = str(user_id) not in data["users"]
    user = DataManager.get_user(user_id)
    
    if is_new and args and args.startswith("INV"):
        reward = AdminManager.get_setting("invite_reward", 50)
        for ref_id, udata in data["users"].items():
            if udata.get("invite_id") == args:
                udata["coins"] += reward
                udata["invite_count"] += 1
                DataManager._save_data(data)
                try: await client.send_message(int(ref_id), f"🎉 دخل شخص عبر رابطك! حصلت على {reward} نقطة.")
                except: pass
                break

    await send_dynamic_menu(event, user_id, username, "main_menu", edit=False)

@client.on(events.NewMessage(pattern=r'^/admin$'))
async def admin_command(event):
    user_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    if is_admin(user_id, username): await show_admin_panel(event)

async def show_admin_panel(event):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"👑 **لوحة التحكم (Ultimate V9 - MTProto / Telethon)** 👑\n\n🕒 السيرفر: `{now}`\nاختر القسم المطلوب:"
    kb = [[ib("📢 قنوات الدخول (Plus)", "adm_plus_ch"), ib("🌟 قنوات التجميع (Gold)", "adm_gold_ch")],
        [ib("💰 تحكم الأسعار الشامل", "adm_prices_ctrl")],[ib("📂 أقسام الرشق", "adm_smm_sec"), ib("🛍️ الخدمات", "adm_smm_srv|0")],[ib("🎛 التعديل اللانهائي للقوائم", "adm_menus")],[ib("👥 المستخدمين (شحن نقاط)", "adm_users"), ib("🏦 بنك النقاط", "adm_eco")],[ib("🎁 الهدايا والأكواد", "adm_promo"), ib("⚙️ إعدادات البوت", "adm_settings")],[ib("🌐 إعدادات API", "adm_smm_api"), ib("📣 الإذاعة", "adm_broadcast")],[ib("🛡 حماية البوت", "adm_security"), ib("📊 الإحصائيات", "adm_adv_stats")],[ib("💾 النسخ الاحتياطي", "adm_system"), ib("💸 فحص الاسترجاع", "adm_refund")],[ib("❌ إغلاق اللوحة", "adm_close")]
    ]
    try:
        if isinstance(event, events.CallbackQuery.Event): await event.edit(text, buttons=kb)
        else: await event.reply(text, buttons=kb)
    except MessageNotModifiedError: pass

async def handle_admin_callbacks(event, inner_data=None):
    user_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    
    if not is_admin(user_id, username): 
        return await event.answer("لا تملك صلاحية.", alert=True)

    data = inner_data or event.data.decode('utf-8')
    parts = data.split("|")
    action = parts[0]
    st = get_state(user_id)

    if action == "adm_close":
        await event.edit("✅ تم إغلاق لوحة الإدارة."); st.clear()
    elif action == "adm_panel": await show_admin_panel(event)

    elif action == "adm_plus_ch":
        chs = AdminManager.get_setting("required_channels",[])
        txt = "📢 قنوات الاشتراك الإجباري (Plus):\nيجب على العضو الاشتراك بها ليدخل البوت.\n\n" + "\n".join([f"🔹 {c}" for c in chs])
        kb = [[ib("➕ إضافة قناة", "adm_plus_add"), ib("🗑 حذف قناة", "adm_plus_del")], [ib("⬅️ رجوع", "adm_panel")]]
        await event.edit(txt, buttons=kb)
    elif action == "adm_plus_add":
        st['state'] = 'wait_plus_add'
        await event.edit("أرسل معرف القناة (مثال @channel):")
    elif action == "adm_plus_del":
        st['state'] = 'wait_plus_del'
        await event.edit("أرسل معرف القناة المراد حذفها بدقة:")

    elif action == "adm_gold_ch":
        promos = DataManager._get_data().get("promotions", {})
        txt = "🌟 قنوات تجميع النقاط (Gold):\n(القنوات التي يربح الأعضاء نقاط بالاشتراك بها)\n\n"
        for ch, p in promos.items(): txt += f"🔸 {ch} | المتبقي: {p['remains']}\n"
        if not promos: txt += "لا توجد قنوات حالياً."
        kb = [[ib("➕ إضافة قناة تجميع", "adm_gold_add"), ib("🗑 حذف قناة", "adm_gold_del")], [ib("⬅️ رجوع", "adm_panel")]]
        await event.edit(txt, buttons=kb)
    elif action == "adm_gold_add":
        st['state'] = 'wait_gold_add'
        await event.edit("أرسل معرف القناة (مثال @channel):")
    elif action == "adm_gold_del":
        st['state'] = 'wait_gold_del'
        await event.edit("أرسل معرف القناة المراد حذفها بدقة:")

    elif action == "adm_prices_ctrl":
        get_st = AdminManager.get_setting
        txt = f"💰 **مركز التحكم بالأسعار**:\n\n💵 النقاط لكل دولار: {get_st('points_per_dollar', 12000):,}\n🎁 مكافأة الهدية: {get_st('gift_reward', 20)}\n🔗 مكافأة الدعوة: {get_st('invite_reward', 50)}\n💸 ضريبة التحويل: {get_st('transfer_tax', 5)}%\n🚀 تكلفة التمويل للعضو (Gold): {get_st('promo_cost', 15)}\n🔔 مكافأة الاشتراك (Gold): {get_st('sub_reward', 10)}"
        kb = [[ib("سعر الدولار 💵", "adm_prc_ppd"), ib("تعديل الهدية 🎁", "adm_prc_gift")],[ib("تعديل الدعوة 🔗", "adm_prc_inv"), ib("تعديل الضريبة 💸", "adm_prc_tax")],[ib("تعديل التمويل 🚀", "adm_prc_promo"), ib("مكافأة الاشتراك 🔔", "adm_prc_sub")], [ib("⬅️ رجوع", "adm_panel")]]
        await event.edit(txt, buttons=kb)
    elif action in["adm_prc_gift", "adm_prc_inv", "adm_prc_tax", "adm_prc_promo", "adm_prc_sub", "adm_prc_ppd"]:
        st['state'] = action
        await event.edit("أرسل القيمة الجديدة (أرقام فقط):")

    elif action == "adm_smm_sec":
        secs = AdminManager.get_setting("smm_sections", {})
        txt = "📂 أقسام الرشق المتوفرة:\n\n"
        for code, info in secs.items(): txt += f"📁 {info['name']}  (الكود: `{code}`)\n"
        kb = [[ib("➕ إضافة قسم", "adm_sec_add"), ib("🗑 حذف قسم", "adm_sec_del")],[ib("⬅️ رجوع", "adm_panel")]]
        await event.edit(txt or "لا توجد أقسام حالياً.", buttons=kb)
    elif action == "adm_sec_add":
        st['state'] = 'wait_sec_name'
        await event.edit("أرسل اسم القسم (مثال: انستغرام):")
    elif action == "adm_sec_del":
        st['state'] = 'wait_sec_del'
        await event.edit("أرسل كود القسم لحذفه:")

    elif action == "adm_smm_srv":
        page = int(parts[1]) if len(parts) > 1 else 0
        srvs_items = list(AdminManager.get_setting("smm_services", {}).items())
        secs = AdminManager.get_setting("smm_sections", {})
        
        chunk_size = 10
        total_pages = max(1, (len(srvs_items) + chunk_size - 1) // chunk_size)
        page = max(0, min(page, total_pages - 1))
        chunk = srvs_items[page * chunk_size : (page + 1) * chunk_size]

        txt = f"🛍️ خدمات الرشق (صفحة {page + 1} من {total_pages}):\n\n"
        for code, info in chunk:
            sec_name = secs.get(info.get('sec_id'), {}).get('name', 'بدون قسم')
            txt += f"🔹[{sec_name}] {info['name']} (ID:{info['api_id']})\n   سعر: {info['price']:,} | أدنى: {info['min']} | أقصى: {info['max']}\n   كود الحذف: `{code}`\n\n"
            
        nav_row =[]
        if page > 0: nav_row.append(ib("⬅️ السابق", f"adm_smm_srv|{page-1}"))
        if page < total_pages - 1: nav_row.append(ib("التالي ➡️", f"adm_smm_srv|{page+1}"))

        kb =[]
        if nav_row: kb.append(nav_row)
        kb.append([ib("➕ إضافة خدمة", "adm_srv_preadd"), ib("🗑 حذف خدمة", "adm_srv_del")])
        kb.append([ib("🔄 سحب الخدمات تلقائياً من API", "adm_srv_sync")])
        kb.append([ib("⬅️ رجوع", "adm_panel")])
        
        await event.edit(txt if srvs_items else "لا توجد خدمات مضافة.", buttons=kb)

    elif action == "adm_srv_sync":
        await event.edit("⏳ جاري الاتصال بالـ API وسحب الخدمات...")
        res = await SMMAPI.call("services")
        
        if isinstance(res, dict) and "error" in res:
            return await event.edit(f"❌ خطأ من الـ API: {res['error']}", buttons=[[ib("⬅️ رجوع", "adm_smm_srv|0")]])
        if not isinstance(res, list):
            return await event.edit("❌ لم يتم استلام قائمة صحيحة من API. يرجى التأكد من الرابط والمفتاح.", buttons=[[ib("⬅️ رجوع", "adm_smm_srv|0")]])

        target_cats =["انستقرام", "تيك توك | متابعين جديدة", "تليجرام | أعضاء ثابت مدى الحياة"]
        def clean_s(s): return " ".join(str(s).strip().split())
        target_cats_clean = [clean_s(c) for c in target_cats]

        secs = AdminManager.get_setting("smm_sections", {})
        srvs = AdminManager.get_setting("smm_services", {})
        cat_to_sec = {clean_s(v["name"]): k for k, v in secs.items()}
        ppd = AdminManager.get_setting("points_per_dollar", 12000)
        
        added = 0
        for item in res:
            cat_name = clean_s(item.get("category", ""))
            if cat_name in target_cats_clean:
                if cat_name not in cat_to_sec:
                    sec_id = f"sec_{random.randint(1000, 9999)}"
                    secs[sec_id] = {"name": cat_name}
                    cat_to_sec[cat_name] = sec_id
                else: sec_id = cat_to_sec[cat_name]
                    
                srv_id = str(item.get("service"))
                code = f"srv_{srv_id}"
                
                try: price = max(1, int((float(item.get("rate", 0)) + 1.0) * ppd))
                except: price = int(2.0 * ppd)
                
                srvs[code] = {"sec_id": sec_id, "name": item.get("name", "بدون اسم"), "api_id": int(srv_id), "price": price, "min": int(item.get("min", 10)), "max": int(item.get("max", 10000)), "desc": str(item.get("desc", "")) or "بدون وصف"}
                added += 1

        AdminManager.set_setting("smm_sections", secs)
        AdminManager.set_setting("smm_services", srvs)
        await event.edit(f"✅ **تم السحب بنجاح!**\n\nتم استيراد/تحديث **{added}** خدمة من الفئات المحددة.\n\n⚠️ تم إضافة **1$ دولار إضافية** تلقائياً على كل خدمة.", buttons=[[ib("⬅️ رجوع", "adm_smm_srv|0")]])

    elif action == "adm_srv_preadd":
        secs = AdminManager.get_setting("smm_sections", {})
        if not secs: return await event.answer("❌ يجب إضافة قسم أولاً!", alert=True)
        kb = [[ib(info["name"], f"adm_srv_addsec|{code}")] for code, info in secs.items()]
        kb.append([ib("⬅️ إلغاء", "adm_smm_srv|0")])
        await event.edit("📂 اختر القسم لإضافة الخدمة داخله:", buttons=kb)
    elif action == "adm_srv_addsec":
        st['target_sec'] = parts[1]; st['state'] = 'wait_srv_name'
        await event.edit("أرسل اسم الخدمة:")
    elif action == "adm_srv_del":
        st['state'] = 'wait_srv_del'
        await event.edit("أرسل كود الخدمة لحذفها:")

    elif action == "adm_menus":
        menus = AdminManager.get_all_menus()
        kb = [[ib(m_data.get("name", m_id), f"adm_em|{m_id}")] for m_id, m_data in menus.items()]
        kb.append([ib("⬅️ رجوع", "adm_panel")])
        await event.edit("اختر القائمة للتعديل الشامل:", buttons=kb)
    elif action == "adm_em":
        m_id = parts[1]; m = AdminManager.get_menu(m_id)
        kb = [[ib("📝 تعديل نص القائمة", f"adm_em_txt|{m_id}"), ib("🎛 تعديل الأزرار", f"adm_em_btns|{m_id}")],[ib("⬅️ رجوع", "adm_menus")]]
        await event.edit(f"قائمة: {m.get('name', m_id)}\nاختر الإجراء:", buttons=kb)
    elif action == "adm_em_txt":
        st['state'] = 'wait_menu_txt'; st['edit_menu_id'] = parts[1]
        await event.edit("أرسل النص الجديد للقائمة:")
    elif action == "adm_em_btns":
        m_id = parts[1]; m = AdminManager.get_menu(m_id); kb =[]
        for r, row in enumerate(m.get("buttons", [])):
            for c, btn in enumerate(row): kb.append([ib(f"تعديل: {btn['text']}", f"adm_eb|{m_id}|{r}|{c}")])
        kb.append([ib("➕ إضافة زر (صف جديد)", f"adm_addbtn_new|{m_id}")])
        kb.append([ib("➕ إضافة زر (بجانب السابق)", f"adm_addbtn_row|{m_id}")])
        kb.append([ib("⬅️ رجوع", f"adm_em|{m_id}")])
        await event.edit("اختر الزر للتعديل أو أضف جديداً:", buttons=kb)
    elif action == "adm_eb":
        m_id, r, c = parts[1], int(parts[2]), int(parts[3])
        btn = AdminManager.get_menu(m_id)["buttons"][r][c]
        kb = [[ib("📝 النص", f"adm_eb_txt|{m_id}|{r}|{c}"), ib("🔗 الرابط/الداتا", f"adm_eb_dat|{m_id}|{r}|{c}")],[ib("⬆️", f"adm_eb_m|{m_id}|{r}|{c}|up"), ib("⬇️", f"adm_eb_m|{m_id}|{r}|{c}|down")],[ib("➡️", f"adm_eb_m|{m_id}|{r}|{c}|right"), ib("⬅️", f"adm_eb_m|{m_id}|{r}|{c}|left")],[ib("🗑 حذف", f"adm_eb_del|{m_id}|{r}|{c}"), ib("⬅️ رجوع", f"adm_em_btns|{m_id}")]]
        await event.edit(f"الزر: {btn['text']}\nالداتا: {btn.get('url', btn.get('callback_data'))}", buttons=kb)
    elif action in["adm_eb_txt", "adm_eb_dat"]:
        st['state'] = f'wait_btn_{action.split("_")[2]}'; st['edit_btn_info'] = parts
        await event.edit("أرسل القيمة الجديدة:\n(إلغاء للعودة)")
    elif action == "adm_eb_del":
        AdminManager.delete_button(parts[1], int(parts[2]), int(parts[3]))
        await handle_admin_callbacks(event, f"adm_em_btns|{parts[1]}")
    elif action == "adm_eb_m":
        AdminManager.move_button(parts[1], int(parts[2]), int(parts[3]), parts[4])
        await handle_admin_callbacks(event, f"adm_em_btns|{parts[1]}")
    elif action in ["adm_addbtn_new", "adm_addbtn_row"]:
        st['state'] = 'wait_new_btn_txt'; st['edit_menu_id'] = parts[1]; st['new_btn_type'] = action
        await event.edit("أرسل نص الزر الجديد:")

    elif action == "adm_users":
        st['state'] = 'wait_user_search'
        await event.edit("أرسل آيدي (ID) المستخدم للبحث عنه وتعديل رصيده:")
    elif action == "adm_user_panel":
        uid = parts[1]; u = DataManager.get_user(uid)
        txt = f"👤 مستخدم: `{uid}`\n💰 نقاطه: {u['coins']}\nرتبة VIP: {u.get('is_vip')}\nحالة: {'محظور 🔴' if u.get('is_banned') else 'نشط 🟢'}"
        kb = [[ib("➕ إضافة نقاط", f"adm_u_add|{uid}"), ib("➖ خصم نقاط", f"adm_u_sub|{uid}")],[ib("حظر 🔴", f"adm_u_ban|{uid}"), ib("فك حظر 🟢", f"adm_u_unban|{uid}")],[ib("تصفير 🧽", f"adm_u_zero|{uid}"), ib("تبديل VIP 👑", f"adm_u_vip|{uid}")],[ib("إرسال رسالة ✉️", f"adm_u_msg|{uid}")],[ib("⬅️ بحث جديد", "adm_users")]]
        await event.edit(txt, buttons=kb)
    elif action in["adm_u_add", "adm_u_sub", "adm_u_msg"]:
        st['state'] = action; st['target_user'] = parts[1]
        await event.edit("أرسل القيمة المطلوبة:")
    elif action in["adm_u_zero", "adm_u_ban", "adm_u_unban", "adm_u_vip"]:
        u = DataManager.get_user(parts[1])
        if "zero" in action: u['coins'] = 0
        if "ban" in action: u['is_banned'] = ("unban" not in action)
        if "vip" in action: u['is_vip'] = not u.get('is_vip')
        DataManager.save_user(parts[1], u)
        await handle_admin_callbacks(event, f"adm_user_panel|{parts[1]}")

    elif action == "adm_settings":
        kb = [[ib("رسالة الترحيب", "adm_set_welc"), ib("الشروط", "adm_set_terms")],[ib("معلومات الشحن", "adm_set_charge"), ib("نص الدعم", "adm_set_sup")],[ib("وضع الصيانة 🔧", "adm_toggle_maint")], [ib("⬅️ رجوع", "adm_panel")]]
        await event.edit("إعدادات البوت:", buttons=kb)
    elif action in["adm_set_welc", "adm_set_terms", "adm_set_charge", "adm_set_sup"]:
        st['state'] = action; await event.edit("أرسل النص الجديد:")
    elif action == "adm_toggle_maint":
        AdminManager.set_setting("maintenance_mode", not AdminManager.get_setting("maintenance_mode", False))
        await handle_admin_callbacks(event, "adm_settings")

    elif action == "adm_eco":
        d = DataManager._get_data(); tot = sum(u["coins"] for u in d["users"].values())
        txt = f"🏦 البنك المركزي:\nإجمالي النقاط بالبوت: {tot:,}\nالتحويل بين الأعضاء: {'مفعل ✅' if AdminManager.get_setting('transfers_enabled', True) else 'معطل ❌'}"
        kb = [[ib("أغنى 5 أشخاص 🏆", "adm_eco_rich"), ib("تبديل التحويل 🔄", "adm_eco_tog_trans")],[ib("⬅️ رجوع", "adm_panel")]]
        await event.edit(txt, buttons=kb)
    elif action == "adm_eco_tog_trans":
        AdminManager.set_setting("transfers_enabled", not AdminManager.get_setting("transfers_enabled", True))
        await handle_admin_callbacks(event, "adm_eco")
    elif action == "adm_eco_rich":
        d = DataManager._get_data(); top = sorted(d["users"].items(), key=lambda x: x[1]["coins"], reverse=True)[:5]
        txt = "أغنى 5 مستخدمين:\n" + "\n".join([f"👤 `{k}`: {v['coins']:,} نقطة" for k, v in top])
        await event.edit(txt, buttons=[[ib("⬅️ رجوع", "adm_eco")]])

    elif action == "adm_promo":
        kb = [[ib("🎫 كود جديد", "adm_pc_add"), ib("📋 عرض الأكواد", "adm_pc_list")],[ib("تصفير الهدايا للكل 🔄", "adm_res_gift")], [ib("⬅️ رجوع", "adm_panel")]]
        await event.edit("نظام الأكواد والهدايا:", buttons=kb)
    elif action == "adm_pc_add":
        st['state'] = action; await event.edit("أرسل اسم الكود الجديد:")
    elif action == "adm_pc_list":
        promos = AdminManager.get_setting("promo_codes", {})
        txt = "الأكواد:\n" + "\n".join([f"🎟 `{k}` | 💰 {v['reward']} | ♻️ {v['uses']}/{v['max']}" for k, v in promos.items()])
        await event.edit(txt or "لا توجد أكواد", buttons=[[ib("حذف كود 🗑", "adm_pc_del")], [ib("⬅️ رجوع", "adm_promo")]])
    elif action == "adm_pc_del":
        st['state'] = action; await event.edit("أرسل كود الهدية لحذفه:")
    elif action == "adm_res_gift":
        d = DataManager._get_data()
        for u in d["users"].values(): u["gift_claimed"] = False
        DataManager._save_data(d); await event.answer("تم تصفير الهدايا!", alert=True)

    elif action == "adm_security":
        await event.edit("حماية البوت:", buttons=[[ib("تبديل Anti-Spam 🛡", "adm_tog_spam")],[ib("⬅️ رجوع", "adm_panel")]])
    elif action == "adm_tog_spam":
        AdminManager.set_setting("anti_spam", not AdminManager.get_setting("anti_spam", True))
        await event.answer("تم التبديل!", alert=True)

    elif action == "adm_smm_api":
        kb = [[ib("🔗 تعيين الرابط", "adm_smm_seturl"), ib("🔑 تعيين المفتاح", "adm_smm_setkey")],[ib("💰 فحص الرصيد", "adm_smm_bal")],[ib("⬅️ رجوع", "adm_panel")]]
        await event.edit(f"API: {AdminManager.get_setting('smm_api_url')}", buttons=kb)
    elif action in["adm_smm_seturl", "adm_smm_setkey"]:
        st['state'] = action; await event.edit("أرسل القيمة:")
    elif action == "adm_smm_bal":
        res = await SMMAPI.call("balance")
        msg = f"❌ خطأ: {res['error']}" if "error" in res else f"✅ رصيدك: {res.get('balance', 'مجهول')} {res.get('currency', '')}"
        await event.edit(msg, buttons=[[ib("⬅️ رجوع", "adm_smm_api")]])

    elif action == "adm_refund":
        await event.edit("⏳ جاري فحص جميع الطلبات للاسترجاع التلقائي (Auto-Refund)...")
        d = DataManager._get_data(); ref_c = 0
        for uid, u in d["users"].items():
            for o in u.get("orders",[]):
                if not o.get("refunded"):
                    res = await SMMAPI.call("status", order=o["id"])
                    if res.get("status") == "Canceled":
                        o["refunded"] = True; u["coins"] += o.get("cost", 0); ref_c += 1
        DataManager._save_data(d)
        await event.edit(f"✅ تم فحص واسترجاع {ref_c} طلبات ملغاة.", buttons=[[ib("⬅️ رجوع", "adm_panel")]])

    elif action == "adm_system":
        kb = [[ib("تصدير الداتا 💾", "adm_sys_d1"), ib("تصدير الإعدادات 💾", "adm_sys_d2")],[ib("⬅️ رجوع", "adm_panel")]]
        await event.edit("النسخ الاحتياطي:", buttons=kb)
    elif action in ["adm_sys_d1", "adm_sys_d2"]:
        fname = DATA_FILE if action.endswith("1") else ADMIN_FILE
        try: await client.send_file(event.chat_id, fname); await event.answer("تم!")
        except: pass

    elif action.startswith("adm_rep_"):
        uid = action.split("_")[2]; st['state'] = f'wait_rep_{uid}'
        await event.edit(f"اكتب ردك للمستخدم {uid}:")

@client.on(events.NewMessage(func=lambda e: e.is_private and not e.message.text.startswith('/')))
async def text_handler(event):
    user_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    
    if not await enforce_subscription(event, user_id, username): return
    
    st = get_state(user_id)
    state = st.get('state')
    text = event.message.text
    
    if text == "إلغاء":
        st.clear(); return await event.reply("تم إلغاء العملية.")

    if not state: return

    # ---------------- إدخالات الإدارة ----------------
    if is_admin(user_id, username) and (state.startswith("wait") or state.startswith("adm_")):
        if state == "wait_plus_add":
            if text.startswith("@"): AdminManager.add_plus_channel(text); await event.reply("✅ تمت الإضافة لقنوات الاشتراك الإجباري.")
            else: await event.reply("❌ المعرف يجب أن يبدأ بـ @.")
        elif state == "wait_plus_del":
            AdminManager.remove_plus_channel(text); await event.reply("✅ تم.")

        elif state == "wait_gold_add":
            if text.startswith("@"): st['gold_ch'] = text; st['state'] = "wait_gold_qty"; await event.reply("أرسل عدد الأعضاء المتبقي (مثال 10000):")
            else: await event.reply("❌ المعرف يجب أن يبدأ بـ @.")
            return
        elif state == "wait_gold_qty":
            if text.isdigit():
                d = DataManager._get_data(); d.setdefault("promotions", {})[st['gold_ch']] = {"owner": "admin", "remains": int(text), "total": int(text)}
                DataManager._save_data(d); await event.reply("✅ تمت إضافة قناة التجميع (Gold).")
            else: await event.reply("❌ يرجى إرسال رقم.")
        elif state == "wait_gold_del":
            d = DataManager._get_data()
            if text in d.get("promotions", {}): del d["promotions"][text]; DataManager._save_data(d); await event.reply("✅ تم الحذف.")
            else: await event.reply("❌ غير موجودة.")
            
        elif state in["adm_prc_gift", "adm_prc_inv", "adm_prc_tax", "adm_prc_promo", "adm_prc_sub", "adm_prc_ppd"]:
            keys = {"adm_prc_gift": "gift_reward", "adm_prc_inv": "invite_reward", "adm_prc_tax": "transfer_tax", "adm_prc_promo": "promo_cost", "adm_prc_sub": "sub_reward", "adm_prc_ppd": "points_per_dollar"}
            if text.isdigit(): AdminManager.set_setting(keys[state], int(text)); await event.reply("✅ تم التحديث")

        elif state == "wait_sec_name":
            secs = AdminManager.get_setting("smm_sections", {}); secs[f"sec_{random.randint(1000, 9999)}"] = {"name": text}
            AdminManager.set_setting("smm_sections", secs); await event.reply(f"✅ تم الإضافة.")
        elif state == "wait_sec_del":
            secs = AdminManager.get_setting("smm_sections", {})
            if text in secs:
                del secs[text]; AdminManager.set_setting("smm_sections", secs)
                srvs = AdminManager.get_setting("smm_services", {}); AdminManager.set_setting("smm_services", {k: v for k, v in srvs.items() if v.get("sec_id") != text})
                await event.reply("✅ تم الحذف.")

        elif state == "wait_srv_name": st['srv_name'] = text; st['state'] = "wait_srv_apiid"; await event.reply("أرسل الـ Service ID من موقع الرشق:"); return
        elif state == "wait_srv_apiid":
            if text.isdigit(): st['srv_id'] = int(text); st['state'] = "wait_srv_price"; await event.reply("أرسل السعر بالنقاط (لكل 1000):")
            return
        elif state == "wait_srv_price":
            if text.isdigit(): st['srv_price'] = int(text); st['state'] = "wait_srv_minmax"; await event.reply("أرسل الحد الأدنى والأقصى مفصولين بفاصلة (مثال: 10,10000):")
            return
        elif state == "wait_srv_minmax": st['srv_minmax'] = text; st['state'] = "wait_srv_desc"; await event.reply("أرسل تفاصيل الخدمة (الوصف) ليقرأه المستخدم قبل الطلب:"); return
        elif state == "wait_srv_desc":
            try:
                min_v, max_v = map(int, st['srv_minmax'].replace(" ", "").split(","))
                srvs = AdminManager.get_setting("smm_services", {})
                srvs[f"srv_{random.randint(1000, 9999)}"] = {"sec_id": st['target_sec'], "name": st['srv_name'], "api_id": st['srv_id'], "price": st['srv_price'], "min": min_v, "max": max_v, "desc": text}
                AdminManager.set_setting("smm_services", srvs); await event.reply(f"✅ تمت إضافة الخدمة بنجاح.")
            except: await event.reply("❌ خطأ بالبيانات المدخلة.")

        elif state == "wait_srv_del":
            srvs = AdminManager.get_setting("smm_services", {})
            if text in srvs: del srvs[text]; AdminManager.set_setting("smm_services", srvs); await event.reply("✅ تم الحذف")

        elif state == "wait_menu_txt": AdminManager.update_menu_text(st['edit_menu_id'], text); await event.reply("✅ تم التحديث")
        elif state == "wait_btn_txt":
            parts = st['edit_btn_info']; btn = AdminManager.get_menu(parts[1])["buttons"][int(parts[2])][int(parts[3])]
            btn["text"] = text; AdminManager.update_button(parts[1], int(parts[2]), int(parts[3]), btn); await event.reply("✅ تم التحديث")
        elif state == "wait_btn_dat":
            parts = st['edit_btn_info']; btn = AdminManager.get_menu(parts[1])["buttons"][int(parts[2])][int(parts[3])]
            btn.pop("callback_data", None); btn.pop("url", None)
            if text.startswith("http"): btn["url"] = text
            else: btn["callback_data"] = text
            AdminManager.update_button(parts[1], int(parts[2]), int(parts[3]), btn); await event.reply("✅ تم التحديث")
        elif state == "wait_new_btn_txt": st['new_btn_txt'] = text; st['state'] = "wait_new_btn_dat"; await event.reply("أرسل الرابط أو الداتا:"); return
        elif state == "wait_new_btn_dat":
            b = {"text": st['new_btn_txt']}
            if text.startswith("http"): b["url"] = text
            else: b["callback_data"] = text
            AdminManager.add_button(st['edit_menu_id'], b, st['new_btn_type'] == "adm_addbtn_new"); await event.reply("✅ تمت الإضافة")

        elif state.startswith("wait_rep_"):
            try: await client.send_message(int(state.split("_")[2]), f"👨‍💻 رد من الإدارة:\n\n{text}"); await event.reply("✅ تم الإرسال.")
            except: await event.reply("❌ فشل الإرسال.")

        elif state == "wait_user_search":
            u = DataManager.get_user(text)
            txt = f"👤 مستخدم: `{text}`\n💰 نقاطه: {u['coins']}\nرتبة VIP: {u.get('is_vip')}\nحالة: {'محظور 🔴' if u.get('is_banned') else 'نشط 🟢'}"
            kb = [[ib("➕ إضافة نقاط", f"adm_u_add|{text}"), ib("➖ خصم نقاط", f"adm_u_sub|{text}")],[ib("حظر 🔴", f"adm_u_ban|{text}"), ib("فك حظر 🟢", f"adm_u_unban|{text}")],[ib("تصفير 🧽", f"adm_u_zero|{text}"), ib("تبديل VIP 👑", f"adm_u_vip|{text}")],[ib("إرسال رسالة ✉️", f"adm_u_msg|{text}")],[ib("⬅️ بحث جديد", "adm_users")]]
            try: await event.reply(txt, buttons=kb)
            except: pass
            st.clear(); return
            
        elif state == "adm_u_add" and text.isdigit(): DataManager.modify_user_coins(st['target_user'], int(text)); await event.reply("✅ تمت الإضافة للمستخدم")
        elif state == "adm_u_sub" and text.isdigit(): DataManager.modify_user_coins(st['target_user'], -int(text), force=True); await event.reply("✅ تم الخصم")
        elif state == "adm_u_msg": 
            try: await client.send_message(int(st['target_user']), text); await event.reply("✅")
            except: pass
        elif state == "adm_set_welc": AdminManager.set_setting("welcome_message", text); await event.reply("✅")
        elif state == "adm_set_terms": AdminManager.set_setting("terms_text", text); await event.reply("✅")
        elif state == "adm_set_charge": AdminManager.set_setting("charge_info", text); await event.reply("✅")
        elif state == "adm_set_sup": AdminManager.set_setting("support_text", text); await event.reply("✅")
        elif state == "adm_smm_seturl": AdminManager.set_setting("smm_api_url", text); await event.reply("✅")
        elif state == "adm_smm_setkey": AdminManager.set_setting("smm_api_key", text); await event.reply("✅")
        
        elif state == "adm_pc_add": st['pc_name'] = text; st['state'] = "wait_pc_val"; await event.reply("أرسل: قيمة الهدية, عدد الاستخدام (مثال: 50, 100)"); return
        elif state == "wait_pc_val":
            try:
                v, m = map(int, text.replace(" ", "").split(","))
                p = AdminManager.get_setting("promo_codes", {})
                p[st['pc_name']] = {"reward": v, "uses": 0, "max": m}; AdminManager.set_setting("promo_codes", p); await event.reply("✅ تم.")
            except: pass
        elif state == "adm_pc_del":
            p = AdminManager.get_setting("promo_codes", {})
            if text in p: del p[text]; AdminManager.set_setting("promo_codes", p); await event.reply("✅ تم")

        st.clear(); return

    # ---------------- إدخالات المستخدم العادي ----------------
    if state == "user_wait_calc":
        text_cleaned = text.replace("$", "").strip()
        if text_cleaned.replace(".", "").isdigit():
            val = float(text_cleaned); ppd = AdminManager.get_setting("points_per_dollar", 12000)
            if "$" in text or val < 100: await event.reply(f"🧮 السعر: **{val}$** دولار يساوي **{int(val * ppd):,}** نقطة.")
            else: await event.reply(f"🧮 السعر: **{int(val):,}** نقطة تساوي **{val / ppd:,.2f}$** دولار.")
        else: await event.reply("❌ يرجى إرسال أرقام صحيحة فقط.")
        st.clear()

    elif state == "user_wait_promo_link":
        if text.startswith("@"):
            try:
                bot_me = await client.get_me()
                p = await client(GetParticipantRequest(text, bot_me.id))
                if not getattr(p.participant, 'admin_rights', None) and type(p.participant).__name__ not in['ChannelParticipantCreator', 'ChannelParticipantAdmin']:
                    return await event.reply("❌ البوت ليس مشرفاً (Admin) في هذه القناة. ارفعه أولاً.")
            except: return await event.reply("❌ لم أتمكن من العثور على القناة. تأكد من المعرف وأن البوت مشرف فيها.")
            st['promo_channel'] = text; st['state'] = 'user_wait_promo_qty'
            await event.reply(f"القناة مقبولة ✅\n\nأرسل الآن عدد الأعضاء المطلوب (تكلفة العضو {AdminManager.get_setting('promo_cost', 15)} نقطة):")
        else: await event.reply("❌ يجب أن يبدأ المعرف بـ @ (قناة عامة).")

    elif state == "user_wait_promo_qty":
        if text.isdigit() and int(text) > 0:
            qty = int(text); cost = qty * AdminManager.get_setting("promo_cost", 15); u = DataManager.get_user(user_id)
            if u['coins'] >= cost:
                DataManager.modify_user_coins(user_id, -cost)
                d = DataManager._get_data()
                d.setdefault("promotions", {})[st['promo_channel']] = {"owner": user_id, "remains": qty, "total": qty}; DataManager._save_data(d)
                await event.reply(f"🚀 تم إضافة قناتك لقائمة التجميع بنجاح!\nالعدد: {qty}\nالتكلفة: {cost:,} نقطة.")
            else: await event.reply(f"❌ نقاطك لا تكفي. التكلفة: {cost:,}، رصيدك: {u['coins']:,}.")
        else: await event.reply("❌ يرجى إرسال رقم صحيح.")
        st.clear()

    elif state == 'user_wait_code':
        code = text.strip(); promos = AdminManager.get_setting("promo_codes", {})
        if code in promos and promos[code]["uses"] < promos[code]["max"]:
            u = DataManager.get_user(user_id)
            if code not in u.get("used_promos",[]):
                u.setdefault("used_promos", []).append(code); u["coins"] += promos[code]["reward"]; promos[code]["uses"] += 1
                AdminManager.set_setting("promo_codes", promos); DataManager.save_user(user_id, u)
                await event.reply(f"🎉 تم استخدام الكود! حصلت على {promos[code]['reward']:,} نقطة.")
            else: await event.reply("❌ استخدمت هذا الكود مسبقاً.")
        else: await event.reply("❌ الكود خاطئ أو منتهي.")
        st.clear()

    elif state == "user_wait_transfer_id":
        if text.isdigit() and text != str(user_id) and str(text) in DataManager._get_data()["users"]:
            if not AdminManager.get_setting("transfers_enabled", True): return await event.reply("❌ التحويل معطل.")
            st['transfer_to'] = text; st['state'] = "user_wait_transfer_amt"
            await event.reply("أرسل عدد النقاط:")
        else: await event.reply("❌ آيدي غير صحيح.")

    elif state == "user_wait_transfer_amt":
        if text.isdigit() and int(text) > 0:
            amt = int(text); tax = AdminManager.get_setting("transfer_tax", 5); net = int(amt - (amt * tax / 100))
            if DataManager.modify_user_coins(user_id, -amt):
                DataManager.modify_user_coins(st['transfer_to'], net)
                await event.reply(f"✅ تم تحويل {net:,} نقطة (خصم {tax}%).")
                try: await client.send_message(int(st['transfer_to']), f"📥 وصلتك {net:,} نقطة من {user_id}.")
                except: pass
            else: await event.reply("❌ نقاطك لا تكفي.")
        st.clear()

    elif state == "user_wait_smm_link":
        st['smm_link'] = text; st['state'] = "user_wait_smm_qty"
        srv = AdminManager.get_setting("smm_services", {}).get(st['smm_code'])
        await event.reply(f"الرابط: {text}\nأرسل الآن الكمية (بين {srv['min']} و {srv['max']}):")

    elif state == "user_wait_smm_qty":
        if text.isdigit():
            qty = int(text); srv = AdminManager.get_setting("smm_services", {}).get(st['smm_code'])
            if srv['min'] <= qty <= srv['max']:
                cost = max(1, int((qty / 1000) * srv['price']))
                u = DataManager.get_user(user_id)
                if u.get("is_vip"): cost = int(cost * 0.9)
                
                if DataManager.modify_user_coins(user_id, -cost):
                    msg = await event.reply("⏳ جاري الإرسال للسيرفر...")
                    res = await SMMAPI.call("add", service=srv['api_id'], link=st['smm_link'], quantity=qty)
                    if "order" in res:
                        u = DataManager.get_user(user_id)
                        u["orders"].append({"id": res["order"], "details": f"{srv['name']} - {qty}", "refunded": False, "cost": cost})
                        DataManager.save_user(user_id, u)
                        d = DataManager._get_data(); d.setdefault("global_stats", {"orders_completed": 0})["orders_completed"] += 1; DataManager._save_data(d)
                        await msg.edit(f"✅ تم الاستلام!\nرقم الطلب: `{res['order']}`\nخُصم: {cost:,} نقطة.")
                    else:
                        DataManager.modify_user_coins(user_id, cost) 
                        await msg.edit(f"❌ فشل الرشق، استرجعت نقاطك.\nالسبب: {res.get('error', 'مجهول')}")
                else: await event.reply(f"❌ نقاطك لا تكفي ({cost:,} نقطة).")
            else: await event.reply("❌ الكمية خارج الحدود.")
        st.clear()

    elif state == "user_wait_order_status":
        msg = await event.reply("⏳ جاري الفحص...")
        res = await SMMAPI.call("status", order=text)
        if "error" in res: await msg.edit(f"❌ خطأ: {res['error']}")
        else: await msg.edit(f"📌 حالة الطلب:\n{res.get('status', 'Unknown')}\nالمتبقي: {res.get('remains', 0)}")
        st.clear()

    elif state == "user_wait_support":
        for a in AdminManager.get_setting("dynamic_admins",[]) + ADMIN_USERNAMES:
            try: await client.send_message(a, f"📞 تذكرة دعم من {user_id}:\n\n{text}", buttons=[[ib("رد 💬", f"adm_rep_{user_id}")]])
            except: pass
        await event.reply("✅ أُرسلت للإدارة."); st.clear()

@client.on(events.CallbackQuery)
async def button_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    parts = data.split("|")
    action = parts[0]
    st = get_state(user_id)

    if data == "check_mandatory_sub":
        if await enforce_subscription(event, user_id, username): await send_dynamic_menu(event, user_id, username, "main_menu")
        return

    if not await enforce_subscription(event, user_id, username): return
    if data.startswith("adm_"): return await handle_admin_callbacks(event)

    menu_map = {"back_main": "main_menu", "account": "account_menu", "collect_coins": "collect_coins_menu", "stats": "stats_menu"}
    if action in menu_map: return await send_dynamic_menu(event, user_id, username, menu_map[action])
        
    elif action == "usr_smm_sections":
        page = int(parts[1]) if len(parts) > 1 else 0
        secs = list(AdminManager.get_setting("smm_sections", {}).items())
        chunk_size = 10
        total_pages = max(1, (len(secs) + chunk_size - 1) // chunk_size)
        page = max(0, min(page, total_pages - 1))
        chunk = secs[page * chunk_size : (page + 1) * chunk_size]

        kb = [[ib(info["name"], f"usr_smm_sec|{code}|0")] for code, info in chunk]
        nav_row =[]
        if page > 0: nav_row.append(ib("⬅️ السابق", f"usr_smm_sections|{page-1}"))
        if page < total_pages - 1: nav_row.append(ib("التالي ➡️", f"usr_smm_sections|{page+1}"))
        if nav_row: kb.append(nav_row)
        kb.append([ib("⬅️ رجوع", "back_main")])
        await event.edit(f"📂 الأقسام (صفحة {page+1}/{total_pages}):" if chunk else "لا توجد أقسام.", buttons=kb)

    elif action == "usr_smm_sec":
        sec_id = parts[1]; page = int(parts[2]) if len(parts) > 2 else 0
        srvs =[(k, v) for k, v in AdminManager.get_setting("smm_services", {}).items() if v.get('sec_id') == sec_id]
        chunk_size = 10
        total_pages = max(1, (len(srvs) + chunk_size - 1) // chunk_size)
        page = max(0, min(page, total_pages - 1))
        chunk = srvs[page * chunk_size : (page + 1) * chunk_size]

        kb = [[ib(info["name"], f"usr_srv_info|{code}")] for code, info in chunk]
        nav_row =[]
        if page > 0: nav_row.append(ib("⬅️ السابق", f"usr_smm_sec|{sec_id}|{page-1}"))
        if page < total_pages - 1: nav_row.append(ib("التالي ➡️", f"usr_smm_sec|{sec_id}|{page+1}"))
        if nav_row: kb.append(nav_row)
        kb.append([ib("⬅️ رجوع للأقسام", "usr_smm_sections|0")])
        await event.edit(f"🛒 اختر الخدمة (صفحة {page+1}/{total_pages}):", buttons=kb)

    elif action == "usr_srv_info":
        code = parts[1]; srv = AdminManager.get_setting("smm_services", {}).get(code)
        txt = f"📦 الخدمة: {srv['name']}\n💰 السعر لـ 1000: {srv['price']:,} نقطة\n📉 الأدنى: {srv['min']} | 📈 الأقصى: {srv['max']}\n\n📝 الوصف:\n{srv.get('desc', 'لا يوجد وصف')}"
        kb = [[ib("✅ طلب الآن", f"buy_smm|{code}")],[ib("⬅️ تراجع", f"usr_smm_sec|{srv['sec_id']}|0")]]
        await event.edit(txt, buttons=kb)

    elif action == "buy_smm":
        st['smm_code'] = parts[1]; st['state'] = 'user_wait_smm_link'
        await event.edit("أرسل الرابط المطلوب للرشق:", buttons=[[ib("❌ إلغاء", "back_main")]])

    elif action == "calc_prices":
        st['state'] = 'user_wait_calc'
        await event.edit("🧮 **حاسبة الأسعار**\n\nأرسل المبلغ بالدولار لمعرفة كم يساوي بالنقاط (مثال: 5)\nأو أرسل عدد النقاط لمعرفة قيمتها بالدولار (مثال: 50000):", buttons=[[ib("❌ إلغاء", "back_main")]])

    elif action == "usr_promote_channel":
        cost = AdminManager.get_setting("promo_cost", 15)
        u = DataManager.get_user(user_id)
        if u['coins'] < cost:
            txt = f"❌ عذراً، نقاطك الحالية لا تكفي لتمويل القنوات.\n\n💰 رصيدك الحالي: {u['coins']:,} نقطة.\n📉 الحد الأدنى لتمويل عضو واحد: {cost} نقطة.\n\nيرجى تجميع النقاط أو شحن حسابك أولاً:"
            kb = [[ib("🪙 تجميع النقاط مجاناً", "collect_coins")], [ib("💳 شحن الحساب", "charge")],[ib("⬅️ رجوع", "back_main")]]
            return await event.edit(txt, buttons=kb)
            
        st['state'] = 'user_wait_promo_link'
        await event.edit(f"🚀 للتمويل أرسل معرف قناتك العام (مثال @channel)\n\n⚠️ **شرط أساسي**: يجب رفع البوت مشرفاً (Admin) في قناتك أولاً ليتم التحقق من المشتركين!\n\nالتكلفة: {cost} نقطة لكل عضو.", buttons=[[ib("❌ إلغاء", "back_main")]])

    elif action == "usr_earn_promos": await show_next_promo(event, user_id)

    elif action == "usr_skip_promo":
        st.setdefault("skipped_promos", []).append(parts[1])
        await show_next_promo(event, user_id, is_skip=True)

    elif action == "usr_verify_promo":
        ch = parts[1]
        try:
            subbed = await is_user_subbed(ch, user_id)
            u = DataManager.get_user(user_id)
            if u["subscriptions"]["gold"].get(ch) != subbed:
                u["subscriptions"]["gold"][ch] = subbed
                DataManager.save_user(user_id, u)
                
            if subbed:
                if ch in u.get("subscribed_promos",[]):
                    await event.answer("❌ لقد اشتركت وحصلت على النقاط مسبقاً!", alert=True)
                    return await show_next_promo(event, user_id)

                sub_reward = AdminManager.get_setting("sub_reward", 10)
                u.setdefault("subscribed_promos",[]).append(ch)
                DataManager.save_user(user_id, u)
                DataManager.modify_user_coins(user_id, sub_reward)

                d = DataManager._get_data()
                if ch in d.get("promotions", {}):
                    d["promotions"][ch]["remains"] -= 1
                    if d["promotions"][ch]["remains"] <= 0: del d["promotions"][ch]
                    DataManager._save_data(d)

                await event.answer(f"✅ مبروك! ربحت {sub_reward} نقطة.", alert=True)
                await show_next_promo(event, user_id)
            else: await event.answer("❌ لم تشترك في القناة بعد!", alert=True)
        except Exception: 
            await event.answer("❌ خطأ بالتحقق، يرجى التأكد من الاشتراك.", alert=True)

    elif action in["my_orders", "order_status", "transfer_points", "use_code", "support", "charge", "terms", "claim_gift", "invite_link"]:
        if action == "my_orders":
            orders = DataManager.get_user(user_id).get("orders", [])
            txt = "سجل طلباتك:\n" + "".join([f"📦 {o['details']} (ID:{o['id']})\n" for o in orders[-10:]])
            await event.edit(txt or "لا يوجد طلبات.", buttons=[[ib("⬅️ رجوع", "back_main")]])
        elif action == "order_status":
            st['state'] = 'user_wait_order_status'
            await event.edit("أرسل رقم الطلب:", buttons=[[ib("❌ إلغاء", "back_main")]])
        elif action == "transfer_points":
            st['state'] = 'user_wait_transfer_id'
            await event.edit("أرسل آيدي (ID) الشخص:", buttons=[[ib("❌ إلغاء", "back_main")]])
        elif action == "use_code":
            st['state'] = 'user_wait_code'
            await event.edit("أرسل كود الهدية:", buttons=[[ib("❌ إلغاء", "back_main")]])
        elif action == "support":
            st['state'] = 'user_wait_support'
            await event.edit(AdminManager.get_setting("support_text"), buttons=[[ib("❌ إلغاء", "back_main")]])
        elif action == "charge": 
            ppd = AdminManager.get_setting("points_per_dollar", 12000)
            prices_list =[1, 2, 3, 4, 5, 10, 20, 50, 100, 150]
            price_list_text = "\n".join([f" • ${d} = {d * ppd:,} نقطة 💎" for d in prices_list])
            raw_text = AdminManager.get_setting("charge_info").replace("{price_list}", price_list_text).replace("{points_per_dollar}", str(ppd))
            await event.edit(raw_text, buttons=[[ib("⬅️ رجوع", "back_main")]])
        elif action == "terms": 
            await event.edit(AdminManager.get_setting("terms_text"), buttons=[[ib("⬅️ رجوع", "back_main")]])
        elif action == "claim_gift":
            u = DataManager.get_user(user_id)
            if u.get("gift_claimed"): await event.answer("استلمتها مسبقاً!", alert=True)
            else:
                v = AdminManager.get_setting("gift_reward", 20)
                if u.get("is_vip"): v *= 2
                u["coins"] += v; u["gift_claimed"] = True; DataManager.save_user(user_id, u) 
                await event.answer(f"🎉 تم استلام {v} نقطة!", alert=True)
                await send_dynamic_menu(event, user_id, username, "account_menu")
        elif action == "invite_link":
            u = DataManager.get_user(user_id); bot_me = await client.get_me()
            reward = AdminManager.get_setting("invite_reward", 50)
            await event.edit(f"رابط الدعوة:\nhttps://t.me/{bot_me.username}?start={u['invite_id']}\n\nاربح {reward} نقطة لكل شخص.", buttons=[[ib("⬅️ رجوع", "collect_coins")]])

if __name__ == "__main__":
    print("🚀 DomKom Ultimate V9 (Telethon MTProto Version) is running...")
    client.start(bot_token=BOT_TOKEN)
    client.run_until_disconnected()