# ربات قیمت‌یاب دیوار 🤖

یک ربات تلگرام برای جستجو و مقایسه قیمت آگهی‌های دیوار در دسته‌بندی‌های مختلف.

## امکانات

- 🚗 جستجو در دسته‌بندی خودرو
- 📱 جستجو در دسته‌بندی موبایل
- 💻 جستجو در دسته‌بندی لپ‌تاپ
- 💼 جستجو در دسته‌بندی کیف، کفش و لباس
- 📊 نمایش آمار قیمت (حداقل، حداکثر، میانگین)
- 🔍 حذف خودکار قیمت‌های غیرمنطقی (outlier removal)

## نصب و راه‌اندازی

### ۱. کلون کردن پروژه

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### ۲. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### ۳. تنظیم متغیرهای محیطی

فایل `.env.example` را کپی کرده و نام آن را به `.env` تغییر دهید:

```bash
cp .env.example .env
```

سپس مقدار `BOT_TOKEN` را با توکن ربات خود از [@BotFather](https://t.me/BotFather) پر کنید:

```
BOT_TOKEN=your_actual_bot_token_here
```

### ۴. اجرای ربات

```bash
python "car price source python.py"
```

## ساختار پروژه

```
├── car price source python.py   # فایل اصلی ربات
├── requirements.txt              # وابستگی‌های پایتون
├── .env.example                  # نمونه فایل تنظیمات
├── .gitignore                    # فایل‌های نادیده‌گرفته شده توسط Git
└── README.md                     # این فایل
```

## توسعه‌دهنده

مهندسی کامپیوتر
