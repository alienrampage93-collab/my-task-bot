import re
import threading
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import db

# Configuration
API_ID = 31503264
API_HASH = "25dcea1322dcd6c14deaa2e37e277cc9"
ADV_TOKEN = "8428996482:AAH2uzUEvYCy_TqndoitK9hv2E2bKXOJ2FY"
WORK_TOKEN = "8200435758:AAHoVIjnTAXCS3JFCdmYEE2gYUHQpMu-pbE"
ADMIN_ID = 8939180157
POINTS_PER_JOIN = 50

db.init_db()

# Clients
adv_app = Client("adv_bot", api_id=API_ID, api_hash=API_HASH, bot_token=ADV_TOKEN)
work_app = Client("work_bot", api_id=API_ID, api_hash=API_HASH, bot_token=WORK_TOKEN)

# --- Advertiser Logic ---
awaiting_link = set()
LINK_RE = re.compile(r"(?:https?://t\.me/|@)([A-Za-z0-9_]{5,32})/?$")

@adv_app.on_message(filters.command("start") & filters.private)
async def adv_start(client, message):
    await message.reply_text("👋 Advertiser Bot သို့ ကြိုဆိုပါသည်။ ဈေးနှုန်းများမှာ ၃၀ ရက်-၁သောင်း၊ ၆၀ ရက်-၁သောင်း၈ထောင်၊ ၉၀ ရက်-၂သောင်း၆ထောင် ဖြစ်ပါသည်။ ငွေလွှဲပြီးပါက SS ပို့ပြီး /post နှိပ်ပါ။ KBZ/Wave: 09674881696")

@adv_app.on_message(filters.command("post") & filters.private)
async def adv_post(client, message):
    awaiting_link.add(message.from_user.id)
    await message.reply_text("📢 Channel Link ကို ပို့ပေးပါ။")

@adv_app.on_message(filters.private & filters.text & ~filters.command(["start", "post"]))
async def adv_link(client, message):
    if message.from_user.id not in awaiting_link: return
    match = LINK_RE.search(message.text)
    if not match: return await message.reply_text("❌ Link ပုံစံမမှန်ပါ။")
    
    chat = await client.get_chat(match.group(1))
    ad_id = db.create_pending_ad(f"https://t.me/{chat.username}", chat.id, chat.title, message.from_user.id)
    awaiting_link.discard(message.from_user.id)
    await message.reply_text("✅ အောင်မြင်ပါသည်။ Admin အတည်ပြုပေးပါလိမ့်မည်။")
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"app_{ad_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_{ad_id}")]])
    await client.send_message(ADMIN_ID, f"🆕 ကြော်ငြာအသစ် ID: {ad_id}\nChannel: {chat.title}", reply_markup=kb)

@adv_app.on_callback_query(filters.regex(r"^(app|rej)_(\d+)$"))
async def admin_decision(client, cq):
    if cq.from_user.id != ADMIN_ID: return
    action, ad_id = cq.data.split("_")
    if action == "app": db.approve_ad(int(ad_id)); await cq.edit_message_text("✅ APPROVED")
    else: db.reject_ad(int(ad_id)); await cq.edit_message_text("❌ REJECTED")

# --- Worker Logic ---
@work_app.on_message(filters.command("start") & filters.private)
async def work_start(client, message):
    db.ensure_user(message.from_user.id)
    await message.reply_text("👋 Worker Bot! /tasks ဖြင့် Task များကြည့်ပါ။ /withdraw ဖြင့် ငွေထုတ်ပါ။")

@work_app.on_message(filters.command("tasks") & filters.private)
async def work_tasks(client, message):
    ads = db.get_active_ads()
    if not ads: return await message.reply_text("😕 Task မရှိသေးပါ။")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 "+a['channel_title'], url=a['link'])], [InlineKeyboardButton("✅ Verify", callback_data=f"ver_{a['ad_id']}")]] for a in ads)
    await message.reply_text("📋 Task များ:", reply_markup=InlineKeyboardMarkup([item for sublist in kb.inline_keyboard for item in [sublist]]))

@work_app.on_callback_query(filters.regex(r"^ver_(\d+)$"))
async def work_verify(client, cq):
    ad_id = int(cq.data.split("_")[1])
    try:
        await client.get_chat_member(db.get_ad(ad_id)["channel_id"], cq.from_user.id)
        db.record_verification(ad_id, cq.from_user.id, POINTS_PER_JOIN)
        await cq.answer("✅ Verified!", show_alert=True)
    except: await cq.answer("❌ မjoin ရသေးပါ/Admin မဖြစ်သေးပါ", show_alert=True)

@work_app.on_message(filters.command("withdraw") & filters.private)
async def work_withdraw(client, message):
    points = db.get_user_points(message.from_user.id)
    if points < 10000: return await message.reply_text("❌ အနည်းဆုံး ၁၀,၀၀၀ ပွိုင့်မှ ထုတ်နိုင်ပါသည်။")
    await message.reply_text("✅ ဖုန်းနံပါတ် (KPay/Wave) ပို့ပေးပါ။ Admin စစ်ဆေးပြီး ပေးပါမည်။")

# --- Running ---
if __name__ == "__main__":
    t1 = threading.Thread(target=adv_app.run)
    t2 = threading.Thread(target=work_app.run)
    t1.start(); t2.start(); t1.join(); t2.join()
  
