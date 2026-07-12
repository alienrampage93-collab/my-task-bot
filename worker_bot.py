from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import db

API_ID = 31503264
API_HASH = "25dcea1322dcd6c14deaa2e37e277cc9"
BOT_TOKEN = "8200435758:AAHoVIjnTAXCS3JFCdmYEE2gYUHQpMu-pbE"
ADMIN_ID = 8939180157
POINTS_PER_JOIN = 50

db.init_db()
app = Client("worker_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

START_TEXT = (
    "👋 **Worker Bot မှ ကြိုဆိုပါတယ်။**\n\n"
    "Channel များကို Join ပြီး ပွိုင့်များ စုဆောင်းပါ။\n\n"
    "**ဘယ်လိုလုပ်ရမလဲ:**\n"
    "၁။ /tasks ကို နှိပ်ပြီး ရနိုင်တဲ့ Task များကို ကြည့်ပါ။\n"
    "၂။ Channel ကို Join ပြီး **Verify** ကို နှိပ်ပါ။\n"
    f"၃။ တစ်ခါ Join လျှင် **{POINTS_PER_JOIN} ပွိုင့်** ရပါမည်။\n"
    "၄။ /balance ဖြင့် ပွိုင့်လက်ကျန်ကို ကြည့်ပါ။\n"
    "၅။ /withdraw ဖြင့် ငွေထုတ်ယူနိုင်ပါသည်။ (အနည်းဆုံး ၁၀,၀၀၀ ပွိုင့်)\n\n"
    "⚠️ သတိပေးချက်: Bot ကို Admin မထည့်ထားသော Channel များတွင် Verify လုပ်၍ မရပါ။"
)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    db.ensure_user(message.from_user.id)
    await message.reply_text(START_TEXT)

@app.on_message(filters.command("tasks") & filters.private)
async def tasks_handler(client, message: Message):
    ads = db.get_active_ads()
    if not ads:
        await message.reply_text("😕 လက်ရှိမှာ လုပ်စရာ Task မရှိသေးပါ။ ခဏနေမှ ပြန်လာကြည့်ပေးပါ။")
        return
    
    rows = [[InlineKeyboardButton(f"🔗 {ad['channel_title']}", url=ad['link'])],
            [InlineKeyboardButton("✅ Verify", callback_data=f"verify_{ad['ad_id']}")]]
    await message.reply_text("📋 **ရရှိနိုင်သော Task များ:**", reply_markup=InlineKeyboardMarkup(rows))

@app.on_callback_query(filters.regex(r"^verify_(\d+)$"))
async def verify_callback_handler(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ad_id = int(callback_query.data.split("_")[1])
    # [မူလ Verify logic အတိုင်း ဆက်ထားပါ...]
    # (အောင်မြင်ပါက db.record_verification ကို ခေါ်သုံးပါ)

@app.on_message(filters.command("balance") & filters.private)
async def balance_handler(client, message: Message):
    points = db.get_user_points(message.from_user.id)
    await message.reply_text(f"💰 သင့်လက်ကျန် ပွိုင့်: **{points} ပွိုင့်**")

@app.on_message(filters.command("withdraw") & filters.private)
async def withdraw_handler(client, message: Message):
    user_id = message.from_user.id
    points = db.get_user_points(user_id)
    
    if points < 10000:
        await message.reply_text("❌ ငွေထုတ်ရန် အနည်းဆုံး ၁၀,၀၀၀ ပွိုင့် လိုအပ်ပါသည်။")
        return
    
    await message.reply_text(
        f"✅ သင့်တွင် {points} ပွိုင့် ရှိပါသည်။\n"
        "ငွေထုတ်ရန် KBZPay / WavePay ဖုန်းနံပါတ်ကို ပို့ပေးပါ။\n"
        "(ဥပမာ - 09xxxxxxxxx)"
    )
    # နောက်ထပ်အဆင့်အနေနဲ့ ဖုန်းနံပါတ်ရမှ Admin ဆီပို့တဲ့ logic ဆက်ရေးပေးနိုင်ပါတယ်
    
