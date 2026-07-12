import re
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

import db

API_ID = 31503264
API_HASH = "25dcea1322dcd6c14deaa2e37e277cc9"
BOT_TOKEN = "8428996482:AAH2uzUEvYCy_TqndoitK9hv2E2bKXOJ2FY"
ADMIN_ID = 8939180157

db.init_db()

app = Client("advertiser_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

awaiting_link = set()
LINK_RE = re.compile(r"(?:https?://t\.me/|@)([A-Za-z0-9_]{5,32})/?$")

START_TEXT = (
    "👋 **မင်္ဂလာပါ! Advertiser Bot မှ ကြိုဆိုပါတယ်။**\n\n"
    "သင့် Channel ကို လူဝင်ရောက်မှုများစေဖို့ ကြော်ငြာလိုပါက အောက်ပါအတိုင်း လုပ်ဆောင်ပါ။\n\n"
    "**ဝန်ဆောင်ခ ဈေးနှုန်းများ:**\n"
    "• ၃၀ ရက် - ၁၀,၀၀၀ ကျပ်\n"
    "• ၆၀ ရက် - ၁၈,၀၀၀ ကျပ်\n"
    "• ၉၀ ရက် - ၂၆,၀၀၀ ကျပ်\n\n"
    "**ဘယ်လိုလုပ်ရမလဲ:**\n"
    "၁။ ငွေလွှဲပြီးပါက ပြေစာ (Screenshot) ကို ဒီ Bot ထဲ ပို့ပေးပါ။\n"
    "၂။ ပြေစာပို့ပြီးပါက /post ကို နှိပ်ပြီး Channel Link ကို ပို့ပေးပါ။\n"
    "၃။ Admin မှ စစ်ဆေးပြီး အတည်ပြုပေးလျှင် ကြော်ငြာချက်သည် Worker Bot ထဲတွင် အလိုအလျောက် တက်လာပါမည်။\n\n"
    "💰 **ငွေပေးချေမှု:** KBZPay / WavePay: `09674881696`"
)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    await message.reply_text(START_TEXT)

@app.on_message(filters.command("post") & filters.private)
async def post_handler(client, message: Message):
    awaiting_link.add(message.from_user.id)
    await message.reply_text("📢 Channel Link ကို ပို့ပေးပါ။ (ဥပမာ - `https://t.me/yourchannel`)")

@app.on_message(filters.private & filters.text & ~filters.command(["start", "post"]))
async def link_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in awaiting_link:
        return 

    text = message.text.strip()
    match = LINK_RE.search(text)
    if not match:
        await message.reply_text("❌ Link ပုံစံမမှန်ပါ။ /post ကို ပြန်နှိပ်ပြီးမှ ပို့ပေးပါ။")
        return

    username = match.group(1)
    try:
        chat = await client.get_chat(username)
    except errors.RPCError:
        await message.reply_text("❌ Channel ကို ရှာမတွေ့ပါ။ Public ဖြစ်မဖြစ် ပြန်စစ်ပါ။")
        return

    awaiting_link.discard(user_id)
    ad_id = db.create_pending_ad(
        link=f"https://t.me/{username}",
        channel_id=chat.id,
        channel_title=chat.title or username,
        advertiser_id=user_id,
    )

    await message.reply_text("✅ အောင်မြင်ပါသည်။ Admin စစ်ဆေးပြီးပါက အကြောင်းကြားပေးပါမည်။")

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{ad_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{ad_id}"),
    ]])
    await client.send_message(ADMIN_ID, f"🆕 **ကြော်ငြာအသစ်:**\nID: `{ad_id}`\nChannel: {chat.title}\nLink: https://t.me/{username}\nUser: {user_id}", reply_markup=kb)

@app.on_callback_query(filters.regex(r"^(approve|reject)_(\d+)$"))
async def admin_decision_handler(client, callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID: return
    action, ad_id_str = callback_query.data.split("_")
    ad_id = int(ad_id_str)
    
    if action == "approve":
        db.approve_ad(ad_id)
        await callback_query.edit_message_text(callback_query.message.text + "\n\n✅ **APPROVED**")
        await client.send_message(db.get_ad(ad_id)["advertiser_id"], "🎉 သင်၏ ကြော်ငြာကို အတည်ပြုလိုက်ပါပြီ။")
    else:
        db.reject_ad(ad_id)
        await callback_query.edit_message_text(callback_query.message.text + "\n\n❌ **REJECTED**")
        await client.send_message(db.get_ad(ad_id)["advertiser_id"], "😕 သင်၏ ကြော်ငြာကို ငြင်းပယ်လိုက်ပါသည်။")

if __name__ == "__main__":
    app.run()
    
