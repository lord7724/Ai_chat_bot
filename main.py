import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

import db

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAPGPT_API_KEY = os.getenv("GAPGPT_API_KEY")
GAPGPT_BASE_URL = os.getenv("GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "dall-e-3")

PORT = int(os.getenv("PORT", "8080"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-app.onrender.com

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # your own telegram chat_id, as string
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000-0000-0000-0000")
USDT_WALLET = os.getenv("USDT_WALLET", "T...")

ai_client = OpenAI(api_key=GAPGPT_API_KEY, base_url=GAPGPT_BASE_URL)

# waiting_for_image[chat_id] = True  -> next text message is treated as an image prompt
waiting_for_image = {}

TEXTS = {
    "fa": {
        "welcome": "سلام {name}! 👋 به ربات هوش مصنوعی خوش اومدی.\n\n💳 اعتبار فعلی شما: {credit}\n\nهر پیام متنی = ۱ اعتبار.\nبرای ساخت عکس دستور /image رو بزن.\nبرای دیدن اعتبارت دستور /credit رو بزن.",
        "choose_lang": "لطفاً زبان خودت رو انتخاب کن:",
        "lang_set": "زبان با موفقیت روی فارسی تنظیم شد. ✅",
        "no_credit": "⛔ اعتبار شما تموم شده!\n\nبرای شارژ حساب، مبلغ دلخواه رو به شماره کارت زیر واریز کن و عکس رسید رو همینجا برام بفرست:\n\n💳 {card}\n\nیا با تتر (USDT - TRC20):\n{wallet}\n\nبعد از تایید ادمین، اعتبارت شارژ میشه.",
        "credit_status": "💳 اعتبار فعلی شما: {credit}",
        "receipt_received": "📨 رسید شما دریافت شد و برای ادمین ارسال شد. لطفاً منتظر تایید بمون.",
        "credit_added": "✅ اعتبار شما شارژ شد! اعتبار فعلی: {credit}",
        "image_prompt": "🎨 توضیح تصویری که می‌خوای بسازم رو بفرست:",
        "generating_text": "⏳ در حال فکر کردن...",
        "generating_image": "🎨 در حال ساخت تصویر...",
        "error": "❌ مشکلی پیش اومد، لطفاً دوباره امتحان کن.",
    },
    "ar": {
        "welcome": "مرحباً {name}! 👋 أهلاً بك في بوت الذكاء الاصطناعي.\n\n💳 رصيدك الحالي: {credit}\n\nكل رسالة نصية = رصيد واحد.\nلإنشاء صورة استخدم الأمر /image.\nلمعرفة رصيدك استخدم /credit.",
        "choose_lang": "الرجاء اختيار لغتك:",
        "lang_set": "تم ضبط اللغة على العربية بنجاح. ✅",
        "no_credit": "⛔ لقد نفد رصيدك!\n\nلإعادة الشحن، حوّل المبلغ الذي تريده إلى رقم البطاقة التالي وأرسل صورة الإيصال هنا:\n\n💳 {card}\n\nأو عبر USDT (TRC20):\n{wallet}\n\nسيتم شحن رصيدك بعد موافقة الأدمن.",
        "credit_status": "💳 رصيدك الحالي: {credit}",
        "receipt_received": "📨 تم استلام إيصالك وإرساله للأدمن. يرجى انتظار التأكيد.",
        "credit_added": "✅ تم شحن رصيدك! الرصيد الحالي: {credit}",
        "image_prompt": "🎨 أرسل وصف الصورة التي تريد إنشاءها:",
        "generating_text": "⏳ جارٍ التفكير...",
        "generating_image": "🎨 جارٍ إنشاء الصورة...",
        "error": "❌ حدث خطأ، الرجاء المحاولة مرة أخرى.",
    },
}


def t(lang, key, **kwargs):
    return TEXTS.get(lang, TEXTS["fa"])[key].format(**kwargs)


def ensure_user(chat_id, name):
    user = db.get_user(chat_id)
    if user is None:
        db.create_user(chat_id, name)
        user = db.get_user(chat_id)
    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_user.first_name or "دوست عزیز"
    ensure_user(chat_id, name)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa"),
                InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
            ]
        ]
    )
    await update.message.reply_text(TEXTS["fa"]["choose_lang"], reply_markup=keyboard)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = "fa" if query.data == "lang_fa" else "ar"
    db.set_language(chat_id, lang)
    user = db.get_user(chat_id)
    name = query.from_user.first_name or ""
    await query.edit_message_text(t(lang, "lang_set"))
    await context.bot.send_message(
        chat_id, t(lang, "welcome", name=name, credit=user["credit"])
    )


async def credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = ensure_user(chat_id, update.effective_user.first_name or "")
    lang = user["language"] or "fa"
    await update.message.reply_text(t(lang, "credit_status", credit=user["credit"]))


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = ensure_user(chat_id, update.effective_user.first_name or "")
    lang = user["language"] or "fa"
    waiting_for_image[chat_id] = True
    await update.message.reply_text(t(lang, "image_prompt"))


async def send_no_credit(update, lang):
    await update.message.reply_text(
        t(lang, "no_credit", card=CARD_NUMBER, wallet=USDT_WALLET)
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = ensure_user(chat_id, update.effective_user.first_name or "")
    lang = user["language"] or "fa"
    text = update.message.text

    is_image_request = waiting_for_image.pop(chat_id, False)

    new_balance = db.deduct_credit(chat_id, 1)
    if new_balance < 0:
        await send_no_credit(update, lang)
        return

    if is_image_request:
        await update.message.reply_text(t(lang, "generating_image"))
        try:
            result = ai_client.images.generate(
                model=IMAGE_MODEL, prompt=text, n=1, size="1024x1024"
            )
            image_url = result.data[0].url
            await update.message.reply_photo(image_url)
        except Exception:
            logger.exception("Image generation failed")
            db.add_credit(chat_id, 1)  # refund
            await update.message.reply_text(t(lang, "error"))
        return

    await update.message.reply_chat_action("typing")
    try:
        response = ai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": text}],
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception:
        logger.exception("Chat completion failed")
        db.add_credit(chat_id, 1)  # refund
        await update.message.reply_text(t(lang, "error"))


async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User sends a payment receipt screenshot -> forward to admin for manual approval."""
    chat_id = update.effective_chat.id
    user = ensure_user(chat_id, update.effective_user.first_name or "")
    lang = user["language"] or "fa"

    if ADMIN_CHAT_ID:
        caption = (
            f"📨 رسید پرداخت جدید\n"
            f"از: {update.effective_user.full_name} (chat_id: {chat_id})\n\n"
            f"برای شارژ اعتبار به این کاربر بزن:\n/addcredit {chat_id} <تعداد>"
        )
        photo = update.message.photo[-1]
        await context.bot.send_photo(ADMIN_CHAT_ID, photo.file_id, caption=caption)

    await update.message.reply_text(t(lang, "receipt_received"))


async def add_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: /addcredit <chat_id> <amount>"""
    requester_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and requester_id != str(ADMIN_CHAT_ID):
        return

    try:
        target_chat_id = int(context.args[0])
        amount = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("استفاده درست: /addcredit <chat_id> <مقدار>")
        return

    new_balance = db.add_credit(target_chat_id, amount)
    user = db.get_user(target_chat_id)
    lang = (user or {}).get("language", "fa")

    await update.message.reply_text(f"✅ اعتبار کاربر {target_chat_id} شد: {new_balance}")
    try:
        await context.bot.send_message(
            target_chat_id, t(lang, "credit_added", credit=new_balance)
        )
    except Exception:
        logger.exception("Could not notify user about credit top-up")


def main():
    db.init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("credit", credit_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CommandHandler("addcredit", add_credit_command))
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    application.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    if WEBHOOK_URL:
        logger.info("Starting bot with webhook on port %s", PORT)
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        )
    else:
        logger.info("WEBHOOK_URL not set — starting bot with polling (local/dev mode)")
        application.run_polling()


if __name__ == "__main__":
    main()
