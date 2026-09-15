# AHA TTS — دیپلوی روی Render (رایگان)

## مرحله ۱: آپلود کد به گیت‌هاب
1. برو به github.com و رایگان ثبت‌نام کن (اگه حساب نداری)
2. بالا سمت راست → `+` → `New repository`
3. اسمش رو بذار مثلاً `aha-tts` → `Create repository`
4. توی صفحه‌ی مخزن خالی، لینک `uploading an existing file` رو بزن
5. تمام فایل‌های این پوشه (Dockerfile، requirements.txt، پوشه aha_tts) رو بکش و ول کن
6. پایین صفحه `Commit changes` رو بزن

## مرحله ۲: ساخت سرویس روی Render
1. برو به render.com و رایگان ثبت‌نام کن (می‌تونی با همون حساب گیت‌هاب وارد بشی)
2. `New` → `Web Service`
3. مخزن گیت‌هابی که ساختی (`aha-tts`) رو انتخاب و `Connect` کن
4. تنظیمات:
   - Name: `aha-tts` (یا هر اسمی)
   - Environment: `Docker` (خودش باید تشخیص بده چون Dockerfile داریم)
   - Instance Type: `Free`
5. `Create Web Service` رو بزن

## مرحله ۳: صبر کن بیلد بشه
چند دقیقه طول می‌کشه (نصب torch + دانلود مدل در اولین اجرا). لاگ‌ها رو می‌تونی توی همون صفحه ببینی.

## مرحله ۴: آدرس رو بردار
بالای صفحه یه آدرس می‌بینی شبیه:
```
https://aha-tts.onrender.com
```
همینو به‌جای `AHA_TTS_SERVER_URL` توی Cloudflare Worker می‌ذاری.

## تست
```
curl -X POST https://aha-tts.onrender.com/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "سلام دنیا"}' \
  --output out.wav
```

⚠️ نکات مهم:
- سرویس رایگان بعد از ۱۵ دقیقه بی‌کاری می‌خوابه؛ اولین درخواست بعدش حدود ۱ دقیقه طول می‌کشه.
- اگه هنگام اجرا با خطای کمبود حافظه (OOM / Out of Memory) مواجه شدی، یعنی ۵۱۲ مگابایت رم رایگان کافی نبوده — در این صورت باید یا مدل رو سبک‌تر کنیم، یا به پلن ارزون‌قیمت Render (۷ دلار/ماه) فکر کنیم.
