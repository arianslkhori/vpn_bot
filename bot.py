import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = "8835052703:AAHm6ryVBA81mxWQTASypKeQyQjR_4fENjA"
ADMIN_ID = 7874295466
CARD_NUMBER = "6219861993107506"
CARD_NAME = "رویا محبی شیخلری"
CHANNEL_ID = "@thaudsosj"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

conn = sqlite3.connect('shop.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, receipt_photo_id TEXT, status TEXT DEFAULT 'pending')''')
conn.commit()

PRODUCTS = {5: 50000, 10: 90000, 20: 150000, 30: 200000}

async def is_member(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def get_user(user_id, username=""):
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        return (user_id, username, 0)
    return user

async def main_menu(user_id):
    user = get_user(user_id)
    text = f"🛍 فروشگاه VPN\n💰 موجودی: {user[2]:,} تومان\n💳 شماره کارت: {CARD_NUMBER}\n👤 به نام: {CARD_NAME}"
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("📦 خرید اشتراک حجمی", callback_data="buy"))
    keyboard.add(InlineKeyboardButton("💰 افزایش موجودی", callback_data="charge"))
    keyboard.add(InlineKeyboardButton("👤 وضعیت من", callback_data="status"))
    if user_id == ADMIN_ID:
        keyboard.add(InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin"))
    return text, keyboard

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    if not await is_member(user_id):
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        keyboard.add(InlineKeyboardButton("✅ عضویت رو تأیید کن", callback_data="check_join"))
        await message.reply("❌ برای استفاده از ربات ابتدا باید عضو کانال ما بشی:", reply_markup=keyboard)
        return
    get_user(user_id, username)
    text, keyboard = await main_menu(user_id)
    await message.reply(text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: True)
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if not await is_member(user_id) and data not in ["check_join"]:
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        keyboard.add(InlineKeyboardButton("✅ عضویت رو تأیید کن", callback_data="check_join"))
        await bot.edit_message_text("❌ برای استفاده از ربات ابتدا باید عضو کانال ما بشی:", callback.message.chat.id, callback.message.message_id, reply_markup=keyboard)
        return

    if data == "check_join":
        if await is_member(user_id):
            text, keyboard = await main_menu(user_id)
            await bot.edit_message_text(text, callback.message.chat.id, callback.message.message_id, reply_markup=keyboard)
        else:
            await callback.answer("❌ هنوز عضو کانال نشدی!", show_alert=True)
        return

    if data == "buy":
        text = "📦 حجم مورد نظر رو انتخاب کن:\n\n"
        keyboard = InlineKeyboardMarkup(row_width=1)
        for volume, price in PRODUCTS.items():
            text += f"📀 {volume} گیگ = {price:,} تومان\n"
            keyboard.add(InlineKeyboardButton(f"{volume} گیگ - {price:,} تومان", callback_data=f"buyvol_{volume}"))
        keyboard.add(InlineKeyboardButton("🔙 برگشت", callback_data="back"))
        await bot.edit_message_text(text, callback.message.chat.id, callback.message.message_id, reply_markup=keyboard)

    elif data.startswith("buyvol_"):
        volume = int(data.split("_")[1])
        price = PRODUCTS[volume]
        user = get_user(user_id)
        if user[2] < price:
            await callback.answer("❌ موجودی کافی نیست! ابتدا کیف پولت رو شارژ کن.", show_alert=True)
            return
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        conn.commit()
        await bot.edit_message_text(f"✅ خرید {volume} گیگ با موفقیت انجام شد.\nموجودی جدید: {user[2] - price:,} تومان", callback.message.chat.id, callback.message.message_id)
        await bot.send_message(ADMIN_ID, f"📢 کاربر {user_id} خرید {volume} گیگ انجام داد.")

    elif data == "charge":
        text = f"💰 افزایش موجودی\n\n💳 شماره کارت:\n{CARD_NUMBER}\n👤 به نام: {CARD_NAME}\n\nمبلغ رو واریز کن، بعد عکس رسید رو بفرست:"
        await bot.edit_message_text(text, callback.message.chat.id, callback.message.message_id)

    elif data == "status":
        user = get_user(user_id)
        text = f"👤 وضعیت شما:\n💰 موجودی: {user[2]:,} تومان"
        keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 برگشت", callback_data="back"))
        await bot.edit_message_text(text, callback.message.chat.id, callback.message.message_id, reply_markup=keyboard)

    elif data == "admin" and user_id == ADMIN_ID:
        pendings = c.execute("SELECT id, user_id, amount FROM pending WHERE status='pending'").fetchall()
        if not pendings:
            await bot.edit_message_text("✅ درخواستی نیست.", callback.message.chat.id, callback.message.message_id)
            return
        text = "درخواست‌های تایید نشده:\n"
        keyboard = InlineKeyboardMarkup(row_width=1)
        for p in pendings:
            text += f"\n🆔 {p[1]} - {p[2]:,} تومان"
            keyboard.add(InlineKeyboardButton(f"✅ تایید {p[1]}", callback_data=f"verify_{p[0]}"))
        keyboard.add(InlineKeyboardButton("🔙 برگشت", callback_data="back"))
        await bot.edit_message_text(text, callback.message.chat.id, callback.message.message_id, reply_markup=keyboard)

    elif data.startswith("verify_") and user_id == ADMIN_ID:
        pending_id = int(data.split("_")[1])
        req = c.execute("SELECT user_id, amount FROM pending WHERE id=?", (pending_id,)).fetchone()
        if req:
            target_id, amount = req
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            c.execute("UPDATE pending SET status='approved' WHERE id=?", (pending_id,))
            conn.commit()
            await bot.send_message(target_id, f"✅ {amount:,} تومان به موجودیت اضافه شد.")
            await bot.edit_message_text("✅ تایید شد.", callback.message.chat.id, callback.message.message_id)
        else:
            await callback.answer("❌ خطا", show_alert=True)

    elif data == "back":
        text, keyboard = await main_menu(user_id)
        await bot.edit_message_text(text, callback.message.chat.id, callback.message.message_id, reply_markup=keyboard)

    await callback.answer()

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    photo_id = message.photo[-1].file_id
    c.execute("INSERT INTO pending (user_id, amount, receipt_photo_id) VALUES (?, ?, ?)", (message.from_user.id, 0, photo_id))
    conn.commit()
    await message.answer("✅ رسید دریافت شد. درخواست شما ثبت و به ادمین ارسال شد.")
    await bot.send_message(ADMIN_ID, f"📢 درخواست جدید از {message.from_user.username or message.from_user.id}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
