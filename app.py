from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import os
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Debug environment variables
print("API_ID:", os.getenv("API_ID"))
print("API_HASH:", os.getenv("API_HASH"))
print("BOT_TOKEN:", os.getenv("BOT_TOKEN"))
print("MONGO_URI:", os.getenv("MONGO_URI"))
print("CHANNEL_USERNAME:", os.getenv("CHANNEL_USERNAME"))

# Parse environment variables
API_ID = int(os.getenv("API_ID")) if os.getenv("API_ID") else None
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# Check if required variables are missing
if not API_ID or not API_HASH or not BOT_TOKEN or not MONGO_URI or not CHANNEL_USERNAME:
    print("Error: One or more required environment variables are missing!")
    exit(1)

# Initialize bot and MongoDB
bot = Client("channel_referral_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["channel_referral_bot"]
users_collection = db["users"]

# Messages
invite_message = "Laden Sie Ihre Freunde ein, um mehr Freispiele zu erhalten! 🗣️\n💕1 Freund 50 Freispiele\n💕2 Freunde 100 Freispiele"
reward_1_message = "🎉 Herzlichen Glückwunsch! Sie haben 50 Freispiele für das Einladen von 1 Freund verdient! 🎊"
reward_2_message = "🎉 Unglaublich! Sie haben 100 Freispiele verdient, weil Sie 2 Freunde eingeladen haben 🎊"
invite_limit_message = "Du hast bereits alle möglichen Belohnungen in Anspruch genommen. Gute Arbeit beim Einladen von Freunden 🚀"

# Command to send invite message to the channel
@bot.on_message(filters.command("channel") & filters.user([12345678]))  # Replace with your user ID
async def send_invite_message(_, message):
    invite_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Jetzt einladen 🚀", url=f"https://t.me/{bot.username}?start=start")]]
    )
    await bot.send_message(
        chat_id=CHANNEL_USERNAME,
        text=invite_message,
        reply_markup=invite_button
    )
    await message.reply("Invitation message sent to the channel.")

# Handle /start command
@bot.on_message(filters.command("start"))
async def handle_start(_, message):
    user_id = message.from_user.id

    # Check if the user is already registered
    if not users_collection.find_one({"_id": user_id}):
        # Add user to the database
        invite_link = await bot.create_chat_invite_link(CHANNEL_USERNAME, member_limit=None)
        users_collection.insert_one({
            "_id": user_id,
            "referrals": 0,
            "reward_given": 0,
            "invite_link": invite_link.invite_link
        })

    user_data = users_collection.find_one({"_id": user_id})
    invite_link = user_data["invite_link"]

    await message.reply(
        f"Willkommen! Verwenden Sie Ihren Einladungslink, um Freunde zu werben:\n\n{invite_link}\n\n"
        "Rewards:\n💕 1 Freund = 50 Freispiele\n💕 2 Freunde = 100 Freispiele",
    )

# Track new users joining the channel
@bot.on_chat_member_updated(filters.chat(CHANNEL_USERNAME))
async def track_channel_joins(_, event):
    if event.new_chat_member:
        inviter_id = None
        try:
            inviter_id = event.invite_link.creator.id
        except AttributeError:
            return  # Ignore if the join wasn't through an invite link

        referrer = users_collection.find_one({"_id": inviter_id})
        if referrer and referrer["reward_given"] < 2:
            new_referrals = referrer["referrals"] + 1
            reward_given = referrer["reward_given"]

            # Update referrer data and send rewards
            if new_referrals == 1 and reward_given < 1:
                await bot.send_message(inviter_id, reward_1_message)
                reward_given = 1
            elif new_referrals == 2 and reward_given < 2:
                await bot.send_message(inviter_id, reward_2_message)
                reward_given = 2

            users_collection.update_one(
                {"_id": inviter_id},
                {"$set": {"referrals": new_referrals, "reward_given": reward_given}}
            )
        elif referrer and referrer["reward_given"] >= 2:
            await bot.send_message(inviter_id, invite_limit_message)

print("Bot started!")
bot.run()
