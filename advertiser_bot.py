"""
Advertiser Bot
Lets advertisers submit a public channel link. Admin reviews it via
inline Approve/Reject buttons before it becomes an active task in
the shared database (consumed by worker_bot.py).
"""

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

# In-memory "waiting for a link" state per user (fine for a single-process bot)
awaiting_link = set()

LINK_RE = re.compile(r"(?:https?://t\.me/|@)([A-Za-z0-9_]{5,32})/?$")

START_TEXT = (
    "👋 **Welcome to the Advertiser Bot!**\n\n"
    "Use this bot to advertise your Telegram channel and grow real subscribers.\n\n"
    "**How it works:**\n"
    "1️⃣ Send /post to start a submission.\n"
    "2️⃣ Send your channel link (e.g. `https://t.me/yourchannel` or `@yourchannel`).\n"
    "3️⃣ Our admin reviews it — you'll get a message once it's approved or rejected.\n"
    "4️⃣ Once approved, workers will join your channel until it hits its target.\n\n"
    "⚠️ **Crucial Warning:** Make sure your channel is **public** and you have added the "
    "**Worker Bot** as an **Administrator**, otherwise verification will fail!"
)


@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    await message.reply_text(START_TEXT)


@app.on_message(filters.command("post") & filters.private)
async def post_handler(client, message: Message):
    awaiting_link.add(message.from_user.id)
    await message.reply_text(
        "📢 Please send your **public channel link** now.\n\n"
        "Example: `https://t.me/yourchannel` or `@yourchannel`\n\n"
        "⚠️ Reminder: the channel must be public, and the Worker Bot must already be "
        "added as an Administrator, or verification will fail."
    )


@app.on_message(filters.private & filters.text & ~filters.command(["start", "post"]))
async def link_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in awaiting_link:
        return  # ignore stray text outside the submission flow

    text = message.text.strip()
    match = LINK_RE.search(text)
    if not match:
        await message.reply_text(
            "❌ That doesn't look like a valid public channel link.\n"
            "Please send something like `https://t.me/yourchannel` or `@yourchannel`, "
            "or /post to try again."
        )
        return

    username = match.group(1)

    try:
        chat = await client.get_chat(username)
    except errors.RPCError as e:
        await message.reply_text(
            f"❌ Couldn't fetch that channel ({e.__class__.__name__}).\n"
            "Make sure the link is correct, the channel is public, and this bot "
            "hasn't been blocked by it. Then try /post again."
        )
        return

    if str(chat.type).lower().split(".")[-1] != "channel":
        await message.reply_text("❌ That link doesn't point to a channel. Please send a valid channel link.")
        return

    awaiting_link.discard(user_id)

    ad_id = db.create_pending_ad(
        link=f"https://t.me/{username}",
        channel_id=chat.id,
        channel_title=chat.title or username,
        advertiser_id=user_id,
    )

    await message.reply_text(
        "✅ Your channel has been submitted for review!\n"
        "You'll get a message here once the admin approves or rejects it."
    )

    kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{ad_id}"),
        ]]
    )
    try:
        await client.send_message(
            ADMIN_ID,
            "🆕 **New Ad Submission**\n\n"
            f"Ad ID: `{ad_id}`\n"
            f"Channel: {chat.title}\n"
            f"Link: https://t.me/{username}\n"
            f"Advertiser ID: `{user_id}`",
            reply_markup=kb,
        )
    except errors.RPCError:
        # Admin may not have started the bot yet — nothing more we can do here.
        pass


@app.on_callback_query(filters.regex(r"^(approve|reject)_(\d+)$"))
async def admin_decision_handler(client, callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("Only the admin can do this.", show_alert=True)
        return

    action, ad_id_str = callback_query.data.split("_")
    ad_id = int(ad_id_str)
    ad = db.get_ad(ad_id)
    if not ad:
        await callback_query.answer("Ad not found.", show_alert=True)
        return

    if action == "approve":
        db.approve_ad(ad_id)
        await callback_query.edit_message_text(callback_query.message.text + "\n\n✅ **APPROVED**")
        try:
            await client.send_message(
                ad["advertiser_id"],
                f"🎉 Your ad (ID {ad_id}) has been approved and is now live to workers!",
            )
        except errors.RPCError:
            pass
    else:
        db.reject_ad(ad_id)
        await callback_query.edit_message_text(callback_query.message.text + "\n\n❌ **REJECTED**")
        try:
            await client.send_message(
                ad["advertiser_id"],
                f"😕 Your ad (ID {ad_id}) was rejected. Double-check the channel is public "
                "and the Worker Bot is an admin, then try again with /post.",
            )
        except errors.RPCError:
            pass

    await callback_query.answer()


if __name__ == "__main__":
    print("Advertiser bot starting...")
    app.run()
  
