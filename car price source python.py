import logging
import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import urllib.parse
import statistics

# -------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

CATEGORY, SEARCH, SHOW_ADS = range(3)

CATEGORY_MAP = {
    "car": "🚗 خودرو",
    "mobile-phones": "📱 موبایل",
    "laptop-notebook-macbook": "💻 لپ تاپ",
    "apparel": "💼 کیف وکفش و لباس",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# -------------------------------
# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎉 **خوش آمدید!**\n\n"
        "یکی از دسته‌بندی‌ها را انتخاب کنید:"
    )

    keyboard = [
        [InlineKeyboardButton(name, callback_data=code)]
        for code, name in CATEGORY_MAP.items()
    ]
    keyboard.append([InlineKeyboardButton("👨‍💻 توسعه دهنده", callback_data="developer")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CATEGORY

# -------------------------------
# استخراج آگهی‌ها
def extract_ads(category, keyword, limit=20):  # پیش‌فرض 20 آگهی
    encoded = urllib.parse.quote(keyword)
    url = f"https://divar.ir/s/tehran/{category}?q={encoded}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        raise ConnectionError(f"❌ خطای شبکه: {e}")

    results = []
    cards = soup.select("a.kt-post-card__action")
    for card in cards[:limit]:
        title_tag = card.select_one("h2.kt-post-card__title")
        title = title_tag.text.strip() if title_tag else "عنوان نامشخص"

        descs = card.select(".kt-post-card__description")
        km_text = None
        price_text = None
        if len(descs) >= 2:
            km_text = descs[0].text.strip()
            price_text = descs[1].text.strip()
        elif len(descs) == 1:
            single = descs[0].text.strip()
            if "تومان" in single:
                price_text = single
            else:
                km_text = single

        img_tag = card.select_one("img.kt-image-block__image")
        img_url = img_tag.get("src") if img_tag else None

        href = card.get("href") or ""
        url = urllib.parse.urljoin("https://divar.ir", href)

        price_int = None
        if price_text and "توافق" not in price_text:
            nums = re.findall(r'[\d,]+', price_text.replace("٬", ","))
            if nums:
                try:
                    price_int = int(nums[-1].replace(",", ""))
                except:
                    price_int = None

        km_int = None
        if km_text and category in ["car", "mobile-phones"]:
            m = re.search(r'[\d,]+', km_text.replace("٬", ","))
            if m:
                try:
                    km_int = int(m.group().replace(",", ""))
                except:
                    km_int = None

        results.append({
            "title": title,
            "price_text": price_text or "نامشخص",
            "price": price_int,
            "km_text": km_text if category in ["car", "mobile-phones"] else None,
            "km": km_int,
            "url": url,
            "img": img_url
        })

    if not results:
        raise LookupError("❌ هیچ آگهی‌ای پیدا نشد.")
    return results

def remove_outliers(prices_list):
    nums = sorted([p for p in prices_list if isinstance(p, int)])
    if len(nums) < 4:
        return set(nums)
    q1 = nums[len(nums)//4]
    q3 = nums[(3*len(nums))//4]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return set([n for n in nums if lower <= n <= upper])

# -------------------------------
# پردازش متن جستجو و نمایش آمار
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = context.user_data.get("category")
    if not category:
        await update.message.reply_text("❌ دسته انتخاب نشده. لطفاً /start را بزنید.")
        return ConversationHandler.END

    keyword = update.message.text.strip()
    await update.message.reply_text("⏳ در حال جستجو... کمی صبر کنید.")

    try:
        ads = extract_ads(category, keyword)
        numeric_prices = [ad["price"] for ad in ads if isinstance(ad["price"], int)]
        allowed_prices = remove_outliers(numeric_prices)

        # حذف آگهی‌های با قیمت غیرمنطقی
        ads = [ad for ad in ads if isinstance(ad["price"], int) and ad["price"] in allowed_prices]
        context.user_data["ads"] = ads

        if allowed_prices:
            nums = [p for p in numeric_prices if p in allowed_prices] if allowed_prices else numeric_prices
            minp = f"{min(nums):,}".replace(",", ".")
            maxp = f"{max(nums):,}".replace(",", ".")
            meanp = f"{int(statistics.mean(nums)):,}".replace(",", ".")
            stats_msg = "📊 *آمار قیمت‌ها *\n"
            stats_msg += f"🔻 حداقل: `{minp}` تومان\n"
            stats_msg += f"🔺 حداکثر: `{maxp}` تومان\n"
            stats_msg += f"⚖️ میانگین: `{meanp}` تومان\n"
        else:
            stats_msg = "❗️ هیچ قیمت عددی برای محاسبه آمار وجود نداشت."

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 نمایش آگهی‌ها", callback_data="show_ads")],
            [InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="back_to_menu")]
        ])

        await update.message.reply_text(stats_msg, parse_mode="Markdown", reply_markup=kb)

    except ConnectionError as ce:
        await update.message.reply_text(str(ce))
    except LookupError as le:
        await update.message.reply_text(str(le))
    except Exception as e:
        await update.message.reply_text(f"❌ خطای ناشناخته: {e}")

    return SHOW_ADS

# -------------------------------
# نمایش آگهی‌ها با عکس و لینک
async def show_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ads = context.user_data.get("ads", [])
    category = context.user_data.get("category")
    if not ads:
        await query.message.reply_text(
            "❌ هیچ آگهی‌ای برای نمایش وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="back_to_menu")]])
        )
        return CATEGORY

    for i, ad in enumerate(ads, start=1):
        caption = f"🔹 *{i}. {ad['title']}*\n"
        caption += f"💰 قیمت: `{ad['price_text']}`\n" if ad['price_text'] else ""
        if ad['km_text'] and category in ["car", "mobile-phones"]:
            caption += f"🛣️ کارکرد: `{ad['km_text']}`\n"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 مشاهده آگهی", url=ad['url'])],
            [InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="back_to_menu")]
        ])

        if ad['img']:
            await query.message.reply_photo(photo=ad['img'], caption=caption, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.message.reply_text(caption, parse_mode="Markdown", reply_markup=kb)

    return CATEGORY

# -------------------------------
# هندلر دکمه‌ها
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "developer":
        await query.message.reply_text(
            "👨‍💻 *توسعه‌دهنده:*\n\n"
            "رشته: مهندسی کامپیوتر\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="back_to_menu")]])
        )
        return CATEGORY

    if data == "back_to_menu":
        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton(name, callback_data=code)]
            for code, name in CATEGORY_MAP.items()
        ]
        keyboard.append([InlineKeyboardButton("👨‍💻 توسعه دهنده", callback_data="developer")])
        await query.message.reply_text("🌟 لطفاً یک دسته‌بندی را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        return CATEGORY

    if data == "show_ads":
        return await show_ads_callback(update, context)

    if data in CATEGORY_MAP:
        context.user_data["category"] = data
        await query.message.reply_text(f"🔍 دسته‌ی انتخاب شده: {CATEGORY_MAP[data]}\nلطفاً عبارت مورد نظر را ارسال کنید:")
        return SEARCH

    await query.message.reply_text("⚠️ گزینه نامشخص بود. لطفاً /start را بزنید.")
    return CATEGORY

# -------------------------------
# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ عملیات لغو شد. برای شروع دوباره /start را بزنید.")
    return ConversationHandler.END

# -------------------------------
# main
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [CallbackQueryHandler(callback_router)],
            SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler)],
            SHOW_ADS: [CallbackQueryHandler(callback_router)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(callback_router))

    print("🤖 ربات فعال است...")
    app.run_polling()

if __name__ == "__main__":
    main()
