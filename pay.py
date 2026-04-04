import express from 'express';
import TelegramBot from 'node-telegram-bot-api';
import { Low } from 'lowdb';
import { JSONFile } from 'lowdb/node';
import path from 'path';
import { createServer as createViteServer } from 'vite';

// --- Types ---
interface UserData {
  id: number;
  username?: string;
  phone?: string;
  points: number;
  invoices: any[];
}

interface AppData {
  users: Record<number, UserData>;
  channels: string[];
  priceMessage: string;
  invoiceCounter: number;
  adminUsername: string;
  adminId?: number;
}

// --- Database Setup ---
const adapter = new JSONFile<AppData>(path.join(process.cwd(), 'db.json'));
const defaultData: AppData = {
  users: {},
  channels: [],
  priceMessage: `💳 لشحن نقاط البوت تواصل مع الوكيل @leniin9

💡 جدول الأسعار:
 • $1 = 12,000 نقطة 💎
 • $2 = 24,000 نقطة 💎
 • $3 = 36,000 نقطة 💎
 • $4 = 48,000 نقطة 💎
 • $5 = 60,000 نقطة 💎
 • $10 = 120,000 نقطة 💎
 • $20 = 240,000 نقطة 💎
 • $50 = 600,000 نقطة 💎
 • $100 = 1,200,000 نقطة 💎`,
  invoiceCounter: 1,
  adminUsername: 'leniin9',
  adminPhone: '07700000000', // اكتب رقمك هنا ليظهر للمستخدمين عند التحويل
};

const db = new Low<AppData>(adapter, defaultData);
await db.read();

// --- Bot Setup ---
const token = '8718072729:AAHESv3pzxKAgeh_dD-9GSRGhJgm6khAfXE';
const bot = new TelegramBot(token, { polling: true });

// --- Helper Functions ---
async function isSubscribed(chatId: number) {
  if (db.data.channels.length === 0) return true;
  for (const channel of db.data.channels) {
    try {
      const member = await bot.getChatMember(channel, chatId);
      if (member.status === 'left' || member.status === 'kicked') return false;
    } catch (e) {
      console.error(`Error checking subscription for ${channel}:`, e);
      // If bot is not admin in channel, skip check or handle error
    }
  }
  return true;
}

function isAdmin(msg: TelegramBot.Message) {
  return msg.from?.username === db.data.adminUsername || msg.from?.id === db.data.adminId;
}

// --- Bot Logic ---

// State management for multi-step flows
const userStates: Record<number, { step: string; data: any }> = {};

bot.on('message', async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;
  const userId = msg.from?.id;

  if (!userId) return;

  // Initialize user in DB
  if (!db.data.users[userId]) {
    db.data.users[userId] = {
      id: userId,
      username: msg.from?.username,
      points: 0,
      invoices: [],
    };
    await db.write();
  }

  // Admin ID capture
  if (msg.from?.username === db.data.adminUsername && !db.data.adminId) {
    db.data.adminId = userId;
    await db.write();
  }

  // Check subscription
  const subscribed = await isSubscribed(chatId);
  if (!subscribed) {
    const channelButtons: TelegramBot.InlineKeyboardButton[][] = db.data.channels.map(ch => [{ text: `انضم هنا: ${ch}`, url: `https://t.me/${ch.replace('@', '')}` }]);
    channelButtons.push([{ text: 'تحقق من الانضمام', callback_data: 'check_sub' }]);
    return bot.sendMessage(chatId, '⚠️ يجب عليك الاشتراك في القنوات الإجبارية أولاً لتتمكن من استخدام البوت.', {
      reply_markup: { inline_keyboard: channelButtons }
    });
  }

  // Check if phone is registered
  if (!db.data.users[userId].phone && text !== '/start') {
    if (text?.match(/^\d+$/)) {
      db.data.users[userId].phone = text;
      await db.write();
      return bot.sendMessage(chatId, '✅ تم تسجيل رقمك بنجاح. يمكنك الآن استخدام البوت.', {
        reply_markup: {
          keyboard: [
            [{ text: 'أسعار النقاط' }],
            [{ text: 'الشحن عبر التحويل' }, { text: 'شحن عبر الكارت' }]
          ],
          resize_keyboard: true
        }
      });
    } else {
      return bot.sendMessage(chatId, '📱 يرجى إرسال رقمك الآسيا سيل لتسجيل الدخول:');
    }
  }

  // Handle Start
  if (text === '/start') {
    if (!db.data.users[userId].phone) {
      return bot.sendMessage(chatId, '👋 أهلاً بك في بوت شحن النقاط.\n📱 يرجى إرسال رقمك الآسيا سيل لتسجيل الدخول:');
    } else {
      return bot.sendMessage(chatId, '👋 أهلاً بك مجدداً. اختر من القائمة أدناه:', {
        reply_markup: {
          keyboard: [
            [{ text: 'أسعار النقاط' }],
            [{ text: 'الشحن عبر التحويل' }, { text: 'شحن عبر الكارت' }]
          ],
          resize_keyboard: true
        }
      });
    }
  }

  // Handle Buttons
  if (text === 'أسعار النقاط') {
    return bot.sendMessage(chatId, db.data.priceMessage);
  }

  if (text === 'الشحن عبر التحويل') {
    userStates[userId] = { step: 'transfer_amount', data: {} };
    return bot.sendMessage(chatId, '💰 اكتب المبلغ المراد تحويله ($):');
  }

  if (text === 'شحن عبر الكارت') {
    userStates[userId] = { step: 'card_amount', data: {} };
    return bot.sendMessage(chatId, '💰 اكتب المبلغ المراد تحويله ($):');
  }

  // Handle Admin Commands
  if (isAdmin(msg)) {
    if (text === '/admin') {
      return bot.sendMessage(chatId, '🛠️ لوحة تحكم الأدمن:', {
        reply_markup: {
          inline_keyboard: [
            [{ text: 'إضافة قناة اشتراك', callback_data: 'admin_add_channel' }, { text: 'حذف قناة اشتراك', callback_data: 'admin_del_channel' }],
            [{ text: 'تعديل أسعار الشحن', callback_data: 'admin_edit_prices' }],
            [{ text: 'البحث عن شخص', callback_data: 'admin_search_user' }]
          ]
        }
      });
    }
  }

  // Handle multi-step flows
  const state = userStates[userId];
  if (state) {
    if (state.step === 'transfer_amount') {
      state.data.amount = text;
      state.step = 'transfer_wait_screenshot';
      return bot.sendMessage(chatId, `✅ المبلغ: ${text}\n📞 يرجى تحويل الرصيد إلى هذا الرقم: ${db.data.adminPhone}\n📸 بعد التحويل، أرسل سكرين (صورة) إثبات للحوالة:`);
    }

    if (state.step === 'card_amount') {
      state.data.amount = text;
      state.step = 'card_wait_screenshot';
      return bot.sendMessage(chatId, `✅ المبلغ: ${text}\n📸 أرسل سكرين للكارت والرقم السري موضح أو مشخوط:`);
    }

    if (state.step === 'admin_add_channel_input') {
      db.data.channels.push(text!);
      await db.write();
      delete userStates[userId];
      return bot.sendMessage(chatId, `✅ تم إضافة القناة: ${text}`);
    }

    if (state.step === 'admin_del_channel_input') {
      db.data.channels = db.data.channels.filter(c => c !== text);
      await db.write();
      delete userStates[userId];
      return bot.sendMessage(chatId, `✅ تم حذف القناة: ${text}`);
    }

    if (state.step === 'admin_edit_prices_input') {
      db.data.priceMessage = text!;
      await db.write();
      delete userStates[userId];
      return bot.sendMessage(chatId, '✅ تم تحديث رسالة الأسعار.');
    }

    if (state.step === 'admin_search_user_input') {
      const searchId = parseInt(text!);
      const user = db.data.users[searchId];
      if (user) {
        return bot.sendMessage(chatId, `👤 معلومات المستخدم:\n🆔 الايدي: ${user.id}\n📞 الرقم: ${user.phone || 'غير مسجل'}\n💎 النقاط: ${user.points}\n📊 عدد التحويلات: ${user.invoices.length}`);
      } else {
        return bot.sendMessage(chatId, '❌ لم يتم العثور على هذا الشخص.');
      }
    }
  }
});

// Handle Photos (Screenshots)
bot.on('photo', async (msg) => {
  const userId = msg.from?.id;
  if (!userId) return;
  const state = userStates[userId];

  if (state && (state.step === 'transfer_wait_screenshot' || state.step === 'card_wait_screenshot')) {
    const photo = msg.photo![msg.photo!.length - 1].file_id;
    const invoiceId = db.data.invoiceCounter++;
    const type = state.step === 'transfer_wait_screenshot' ? 'تحويل' : 'كارت';
    
    const invoice = {
      id: invoiceId,
      userId: userId,
      amount: state.data.amount,
      type: type,
      photo: photo,
      timestamp: new Date().toISOString()
    };

    db.data.users[userId].invoices.push(invoice);
    await db.write();

    // Send to Admin
    if (db.data.adminId) {
      bot.sendPhoto(db.data.adminId, photo, {
        caption: `🧾 فاتورة جديدة #${invoiceId}\n👤 ايدي الشخص: ${userId}\n📞 رقم الشخص: ${db.data.users[userId].phone}\n💰 المبلغ: ${state.data.amount}\n🛠️ النوع: ${type}`
      });
    }

    delete userStates[userId];
    return bot.sendMessage(msg.chat.id, '✅ تم إرسال الفاتورة للأدمن بنجاح. سيتم التحقق منها قريباً.');
  }
});

// Handle Callbacks
bot.on('callback_query', async (query) => {
  const chatId = query.message?.chat.id;
  const userId = query.from.id;
  if (!chatId) return;

  if (query.data === 'check_sub') {
    const subscribed = await isSubscribed(userId);
    if (subscribed) {
      bot.answerCallbackQuery(query.id, { text: '✅ شكراً لانضمامك!' });
      return bot.sendMessage(chatId, '✅ تم التحقق. يمكنك الآن استخدام البوت /start');
    } else {
      return bot.answerCallbackQuery(query.id, { text: '❌ لم تنضم لجميع القنوات بعد.', show_alert: true });
    }
  }

  if (query.data === 'admin_add_channel') {
    userStates[userId] = { step: 'admin_add_channel_input', data: {} };
    return bot.sendMessage(chatId, '🔗 أرسل معرف القناة (مثال: @channel):');
  }

  if (query.data === 'admin_del_channel') {
    userStates[userId] = { step: 'admin_del_channel_input', data: {} };
    return bot.sendMessage(chatId, '🔗 أرسل معرف القناة المراد حذفها:');
  }

  if (query.data === 'admin_edit_prices') {
    userStates[userId] = { step: 'admin_edit_prices_input', data: {} };
    return bot.sendMessage(chatId, '📝 أرسل رسالة الأسعار الجديدة:');
  }

  if (query.data === 'admin_search_user') {
    userStates[userId] = { step: 'admin_search_user_input', data: {} };
    return bot.sendMessage(chatId, '🆔 أرسل ايدي الشخص المراد البحث عنه:');
  }
});

// --- Express Server ---
async function startServer() {
  const app = express();
  const PORT = 3000;

  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', bot: 'running' });
  });

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
