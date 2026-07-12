"""
Worker Bot
Lets workers browse active advertised channels, join them, and verify
membership to earn points. Reads/writes the same shared database as
advertiser_bot.py.
"""

from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

import db

API_ID = 31503264
API_HASH = "25dcea1322dcd6c14deaa2e37e277cc9"
BOT_TOKEN = "8200435758:AAHoVIjnTAXCS3JFCdmYEE2gYUHQpMu-pbE"

POINTS_PER_JOIN = 50

db.init_db()

app = Client("worker_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

START_TEXT = (
    "👋 **Welcome to the Worker Bot!**\n\n"
    "Earn points by joining advertised channels.\n\n"
    "**How it works:**\n"
    "1️⃣ Send /tasks to see available channels.\n"
    "2️⃣ Tap a channel to open and join it.\n"
    "3️⃣ Come back and tap **Verify** under that task.\n"
    f"4️⃣ Get **{POINTS_PER_JOIN} points** per verified join.\n"
    "5️⃣ Check your total anytime with /balance.\n\n"
    "⚠️ **Crucial Warning:** This bot only works if the advertised channel has added "
    "**this bot** as an **Administrator**. If it's not an admin, verification will fail."
)


def tasks_keyboard(ads):
    rows = []
    for ad in ads:
        title = ad["channel_title"] or ad["link"]
        rows.append([InlineKeyboardButton(f"🔗 Open: {title}", url=ad["link"])])
        rows.append([InlineKeyboardButton("✅ Verify", callback_data=f"verify_{ad['ad_id']}")])
    return InlineKeyboardMarkup(rows) if rows else None


@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    db.ensure_user(message.from_user.id)
    await message.reply_text(START_TEXT)


@app.on_message(filters.command("tasks") & filters.private)
async def tasks_handler(client, message: Message):
    ads = db.get_active_ads()
    if not ads:
        await message.reply_text("😕 No active tasks right now. Check back later!")
        return
    await message.reply_text(
        f"📋 **Available Tasks** ({len(ads)})\n\n"
        "Join a channel, then tap **Verify** underneath it to claim your points.",
        reply_markup=tasks_keyboard(ads),
    )


@app.on_message(filters.command("verify") & filters.private)
async def verify_command_handler(client, message: Message):
    # Verification is per-task, so point them at the task list with its Verify buttons.
    await message.reply_text(
        "Use /tasks to see channels, then tap the **Verify** button under the one you joined."
    )


@app.on_callback_query(filters.regex(r"^verify_(\d+)$"))
async def verify_callback_handler(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ad_id = int(callback_query.data.split("_")[1])
    ad = db.get_ad(ad_id)

    if not ad or ad["status"] != "active":
        await callback_query.answer("This task is no longer active.", show_alert=True)
        return

    if db.has_verified(ad_id, user_id):
        await callback_query.answer("You've already claimed points for this task.", show_alert=True)
        return

    if not ad["channel_id"]:
        await callback_query.answer("This task is misconfigured. Please contact support.", show_alert=True)
        return

    try:
        member = await client.get_chat_member(ad["channel_id"], user_id)
        if str(member.status).lower().split(".")[-1] in ("left", "banned"):
            raise errors.UserNotParticipant
    except errors.UserNotParticipant:
        await callback_query.answer(
            "❌ You haven't joined that channel yet. Join it first, then tap Verify.",
            show_alert=True,
        )
        return
    except errors.ChatAdminRequired:
        await callback_query.answer(
            "❌ Verification failed: this bot isn't an admin in that channel.",
            show_alert=True,
        )
        return
    except errors.RPCError as e:
        await callback_query.answer(
            f"❌ Verification error ({e.__class__.__name__}). Please try again shortly.",
            show_alert=True,
        )
        return

    success, reason = db.record_verification(ad_id, user_id, POINTS_PER_JOIN)
    if success:
        await callback_query.answer(f"✅ Verified! +{POINTS_PER_JOIN} points added.", show_alert=True)
    elif reason == "already_claimed":
        await callback_query.answer("You've already claimed points for this task.", show_alert=True)
    else:
        await callback_query.answer("This task is no longer available.", show_alert=True)


@app.on_message(filters.command("balance") & filters.private)
async def balance_handler(client, message: Message):
    points = db.get_user_points(message.from_user.id)
    await message.reply_text(f"💰 Your balance: **{points} points**")


if __name__ == "__main__":
    print("Worker bot starting...")
    app.run()
  
