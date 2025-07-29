import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, WEBAPP_URL
from urllib.parse import quote_plus
import httpx

logging.basicConfig(level=logging.INFO)

API_BASE_URL = "http://127.0.0.1:5000"  # или замени на свой деплой: https://your-backend.onrender.com

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not hasattr(user, 'id'):
        return

    user_id = int(user.id)
    first_name = getattr(user, 'first_name', '') or ''
    last_name = getattr(user, 'last_name', '') or ''
    photo_url = ''

    # Получение фото пользователя
    try:
        photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][0].file_id
            file = await context.bot.get_file(file_id)
            photo_url = file.file_path or f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file.file_id}"
            prefix = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/"
            if photo_url.startswith(prefix):
                photo_url = photo_url[len(prefix):]
    except Exception as e:
        logging.warning(f"Error getting photo: {e}")
        photo_url = ''

    # Получение реферального кода из команды
    message_text = update.message.text or ""
    args = message_text.split()[1:] if " " in message_text else []
    ref_code = args[0] if args else None

    # Проверка профиля в API и регистрация при необходимости
    profile_data = None
    try:
        async with httpx.AsyncClient() as client:
            profile_resp = await client.get(f"{API_BASE_URL}/api/profile?telegram_id={user_id}")
            profile_data = profile_resp.json() if profile_resp.status_code == 200 else None
            if not profile_data or not profile_data.get("ok"):
                reg_payload = {
                    "telegram_id": str(user_id),
                    "first_name": first_name,
                    "last_name": last_name,
                    "photo_url": photo_url,
                    "ref_code": ref_code
                }
                reg_resp = await client.post(f"{API_BASE_URL}/api/register", json=reg_payload)
                logging.info(f"[BOT] Registered user {user_id}, result: {reg_resp.json()}")
            else:
                logging.info(f"[BOT] User {user_id} already exists")
    except httpx.RequestError as e:
        logging.error(f"[BOT] API error: {e}")

    # Формируем URL для WebApp
    webapp_url = f"{WEBAPP_URL}?user_id={user_id}&first_name={quote_plus(first_name)}&last_name={quote_plus(last_name)}&photo_url={quote_plus(photo_url)}"

    keyboard = [[KeyboardButton(
        text="Открыть веб-приложение",
        web_app=WebAppInfo(url=webapp_url)
    )]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # Отправляем сообщение с кнопкой
    if update.message:
        await update.message.reply_text("Нажмите кнопку, чтобы открыть веб-приложение:", reply_markup=reply_markup)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text("Нажмите кнопку, чтобы открыть веб-приложение:", reply_markup=reply_markup)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
