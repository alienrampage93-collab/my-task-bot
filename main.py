import asyncio
from pyrogram import Client, filters
import db

# Configuration
API_ID = 31503264
API_HASH = "25dcea1322dcd6c14deaa2e37e277cc9"
ADV_TOKEN = "8428996482:AAH2uzUEvYCy_TqndoitK9hv2E2bKXOJ2FY"
WORK_TOKEN = "8200435758:AAHoVIjnTAXCS3JFCdmYEE2gYUHQpMu-pbE"
ADMIN_ID = 8939180157
POINTS_PER_JOIN = 50
PAYMENT_INFO = "📱 KPay / Wave Money: 09674881696"

db.init_db()

# Clients
adv_app = Client("adv_bot", api_id=API_ID, api_hash=API_HASH, bot_token=ADV_TOKEN)
work_app = Client("work_bot", api_id=API_ID, api_hash=API_HASH, bot_token=WORK_TOKEN)

# --- Advertiser Bot Logic ---
@adv_app.on_message(filters.command("start") & filters.private)
async def adv_start(client, message):
    await message.reply_text(f"👋 Advertiser Bot သို့ ကြိုဆိုပါသည်။\n\nဈေးနှုန်းများမှာ:\n- ၃၀ ရက် - ၁၀,၀၀၀ ကျပ်\n- ၆၀ ရက် - ၁၈,၀၀၀ ကျပ်\n- ၉၀ ရက် - ၂၆,၀၀၀ ကျပ်\n\n{PAYMENT_INFO}\n\nငွေလွှဲပြီးပါက SS ပို့ပြီး /post နှိပ်ပါ။")

@adv_app.on_message(filters.command("post") & filters.private)
async def adv_post(client, message):
    await message.reply_text("📢 Channel Link ကို ပို့ပေးပါ။")

@adv_app.on_message(filters.command("pay") & filters.private)
async def adv_pay(client, message):
    await message.reply_text(f"ငွေလွှဲရန် အချက်အလက်:\n{PAYMENT_INFO}\n\nလွှဲပြီးပါက Transaction ID သို့မဟုတ် SS ပုံကို ဒီမှာ ပို့ပေးပါ။")

@adv_app.on_message(filters.private & (filters.photo | filters.text) & ~filters.command(["start", "post", "pay"]))
async def adv_payment_proof(client, message):
    await client.forward_messages(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_ids=message.id)
    await message.reply_text("✅ ငွေလွှဲကြောင်း ပေးပို့ပြီးပါပြီ။ Admin စစ်ဆေးပြီး အကြောင်းကြားပါမည်။")

# --- Worker Bot Logic ---
@work_app.on_message(filters.command("start") & filters.private)
async def work_start(client, message):
    db.ensure_user(message.from_user.id)
    await message.reply_text("👋 Worker Bot! /tasks ဖြင့် Task များကြည့်ပါ။ /withdraw ဖြင့် ငွေထုတ်ပါ။")

@work_app.on_message(filters.command("tasks") & filters.private)
async def work_tasks(client, message):
    ads = db.get_active_ads()
    if not ads: return await message.reply_text("😕 Task မရှိသေးပါ။")
    for a in ads:
        await message.reply_text(f"🔗 {a['channel_title']}", reply_markup=filters.types.InlineKeyboardMarkup([[filters.types.InlineKeyboardButton("✅ Verify", callback_data=f"ver_{a['ad_id']}")]]))

@work_app.on_callback_query(filters.regex(r"^ver_(\d+)$"))
async def work_verify(client, cq):
    ad_id = int(cq.data.split("_")[1])
    try:
        await client.get_chat_member(db.get_ad(ad_id)["channel_id"], cq.from_user.id)
        db.record_verification(ad_id, cq.from_user.id, POINTS_PER_JOIN)
        await cq.answer("✅ Verified!", show_alert=True)
    except: await cq.answer("❌ မjoin ရသေးပါ", show_alert=True)

@work_app.on_message(filters.command("withdraw") & filters.private)
async def work_withdraw(client, message):
    points = db.get_user_points(message.from_user.id)
    if points < 10000: return await message.reply_text("❌ အနည်းဆုံး ၁၀,၀၀၀ ပွိုင့်မှ ထုတ်နိုင်ပါသည်။")
    await message.reply_text("✅ ဖုန်းနံပါတ်ပို့ပေးပါ။ Admin စစ်ဆေးပါမည်။")

# --- Main Running ---
async def main():
    await asyncio.gather(adv_app.start(), work_app.start())
    print("🤖 Both Bots are running!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    
