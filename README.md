# ربات هوش مصنوعی تلگرام

## راه‌اندازی
۱. رمز دیتابیس رو از Supabase چک کن
۲. شماره کارت و کیف پول تتر رو توی .env بذار
۳. ADMIN_CHAT_ID رو توی .env بذار

## اجرای لوکال
pip install -r requirements.txt
python main.py

## دیپلوی روی Render
- Build Command: pip install -r requirements.txt
- Start Command: python main.py
- متغیرهای .env رو دستی توی Render وارد کن
- بعد از دیپلوی، آدرس Render رو توی WEBHOOK_URL بذار و دوباره دیپلوی کن

## قابلیت‌ها
/start = انتخاب زبان
پیام عادی = چت با هوش مصنوعی (۱ اعتبار)
/image = ساخت عکس
/credit = دیدن اعتبار
وقتی اعتبار تموم بشه، شماره کارت خودکار فرستاده میشه
