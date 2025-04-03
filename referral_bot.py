import logging
import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
MAIN_MENU, WITHDRAWAL, ADMIN_CHANNEL_SET, ADMIN_SEARCH_USER = range(4)

# Temporary data storage
user_data = {}
daily_bonus_claimed = {}

# Bot token - directly set the token value
TOKEN = "7706992162:AAGFvTUOMaxno-xvCQowMs9dy6HxJs-MqHc"

ADMIN_IDS = [7619535371]  # Replace with your actual Telegram user ID
required_channel = {"username": "junaqk", "id": None}  # Set required channel to junaqk

async def check_channel_membership(user_id, context):
    """Check if user is a member of the required channel."""
    if not required_channel["username"]:
        return True  # No channel requirement set
    
    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=f"@{required_channel['username']}", 
            user_id=user_id
        )
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    
    # Initialize user data if not exists
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0, "referred_users": []}
    
    # Check channel membership
    is_member = await check_channel_membership(user_id, context)
    if not is_member and required_channel["username"]:
        channel_link = f"https://t.me/{required_channel['username']}"
        
        keyboard = [[InlineKeyboardButton("Join Channel", url=channel_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ You must join our channel before you can use this bot!\n\n"
            f"Please join: {channel_link}\n\n"
            f"After joining, click /start again.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    # Check if this is a referral
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        
        # Make sure user is not referring themselves and is a new user
        if referrer_id != user_id and user_id not in user_data.get(referrer_id, {}).get("referred_users", []):
            # Add referral bonus to referrer
            if referrer_id in user_data:
                user_data[referrer_id]["balance"] += 5
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 Congratulations! User {user.first_name} joined using your referral link. ₹5 has been added to your balance!"
                )
            else:
                # Create record for referrer if they don't exist
                user_data[referrer_id] = {"balance": 5, "referred_users": []}
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 Congratulations! User {user.first_name} joined using your referral link. ₹5 has been added to your balance!"
                )
                
            # Add user to referrer's referred list
            if "referred_users" in user_data[referrer_id]:
                user_data[referrer_id]["referred_users"].append(user_id)
            else:
                user_data[referrer_id]["referred_users"] = [user_id]
    
    # Create referral link
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    
    # Create keyboard
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("🔗 My Referral Link", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"),
        ],
        [
            InlineKeyboardButton("ℹ️ How to Earn", callback_data="how_to_earn"),
        ],
    ]
    
    # Add admin button if user is admin
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}!\n\n"
        f"This bot offers a referral-based earning system. Earn ₹5 for each person who joins using your referral link.\n\n"
        f"Your referral link: {referral_link}\n\n"
        f"Use the buttons below to navigate:",
        reply_markup=reply_markup,
    )
    
    return MAIN_MENU

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Ensure user exists in our database
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0, "referred_users": []}
    
    # Check channel membership for all actions except admin panel
    if query.data != "admin":
        is_member = await check_channel_membership(user_id, context)
        if not is_member and required_channel["username"]:
            channel_link = f"https://t.me/{required_channel['username']}"
            await query.edit_message_text(
                text=f"⚠️ You must join our channel before you can use this bot!\n\n"
                     f"Please join: {channel_link}\n\n"
                     f"After joining, click /start again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=channel_link)]])
            )
            return MAIN_MENU
    
    if query.data == "balance":
        balance = user_data[user_id]["balance"]
        await query.edit_message_text(
            text=f"💰 Your current balance: ₹{balance}\n\n"
                 f"You need at least ₹50 to withdraw.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
        )
        
    elif query.data == "referral":
        referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
        referred_count = len(user_data[user_id].get("referred_users", []))
        
        await query.edit_message_text(
            text=f"🔗 Your Referral Link:\n{referral_link}\n\n"
                 f"Share this link with your friends. You'll earn ₹5 for each person who joins using your link.\n\n"
                 f"Total referrals: {referred_count}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
        )
        
    elif query.data == "withdraw":
        balance = user_data[user_id]["balance"]
        
        if balance >= 50:
            await query.edit_message_text(
                text=f"💸 Withdrawal\n\n"
                     f"Your current balance: ₹{balance}\n\n"
                     f"Please enter your UPI ID to receive payment:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back")]])
            )
            return WITHDRAWAL
        else:
            await query.edit_message_text(
                text=f"❌ Insufficient balance!\n\n"
                     f"Your current balance: ₹{balance}\n"
                     f"You need at least ₹50 to withdraw.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
            )
            
    elif query.data == "daily_bonus":
        today = datetime.now().date()
        last_claimed = daily_bonus_claimed.get(user_id)
        
        if last_claimed is None or last_claimed < today:
            # User can claim bonus - random amount between 1 and 5
            import random
            bonus_amount = random.randint(1, 5)  # Random bonus between ₹1 and ₹5
            user_data[user_id]["balance"] += bonus_amount
            daily_bonus_claimed[user_id] = today
            
            await query.edit_message_text(
                text=f"🎁 Daily Bonus Claimed!\n\n"
                     f"₹{bonus_amount} has been added to your balance.\n"
                     f"Your new balance: ₹{user_data[user_id]['balance']}\n\n"
                     f"Come back tomorrow for another bonus!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
            )
        else:
            # User already claimed today
            next_claim = (datetime.combine(today, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            await query.edit_message_text(
                text=f"⏳ You've already claimed your daily bonus today.\n\n"
                     f"Next bonus available: {next_claim}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
            )
            
    elif query.data == "how_to_earn":
        await query.edit_message_text(
            text="💡 How to Earn:\n\n"
                 "1️⃣ Share your referral link with friends\n"
                 "2️⃣ Earn ₹5 for each friend who joins\n"
                 "3️⃣ Claim a daily bonus of ₹1-₹5 (random)\n"
                 "4️⃣ Withdraw when your balance reaches ₹50\n\n"
                 "The more you refer, the more you earn!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
        )
    
    elif query.data == "admin" and user_id in ADMIN_IDS:
        # Admin panel
        total_users = len(user_data)
        total_referrals = sum(len(data.get("referred_users", [])) for data in user_data.values())
        total_balance = sum(data.get("balance", 0) for data in user_data.values())
        
        # Calculate additional stats
        active_today = sum(1 for uid in daily_bonus_claimed if daily_bonus_claimed[uid] == datetime.now().date())
        
        admin_keyboard = [
            [InlineKeyboardButton("📊 User Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Modify Balance", callback_data="admin_balance")],
            [InlineKeyboardButton("🔍 Search User", callback_data="admin_search")],
            [InlineKeyboardButton("📢 Set Required Channel", callback_data="admin_channel")],
            [InlineKeyboardButton("📋 Recent Withdrawals", callback_data="admin_withdrawals")],
            [InlineKeyboardButton("📣 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back")],
        ]
        
        await query.edit_message_text(
            text=f"🔐 Admin Panel\n\n"
                 f"📈 System Statistics:\n"
                 f"• Total Users: {total_users}\n"
                 f"• Total Referrals: {total_referrals}\n"
                 f"• Total Balance: ₹{total_balance}\n"
                 f"• Active Today: {active_today} users\n\n"
                 f"📱 Channel: @{required_channel['username'] or 'Not set'}\n\n"
                 f"Select an option:",
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
    
    elif query.data == "admin_stats" and user_id in ADMIN_IDS:
        # Get top 5 users by balance
        top_users = sorted(user_data.items(), key=lambda x: x[1].get("balance", 0), reverse=True)[:5]
        
        # Get top 5 referrers
        top_referrers = sorted(user_data.items(), key=lambda x: len(x[1].get("referred_users", [])), reverse=True)[:5]
        
        stats_text = "📊 User Statistics\n\n"
        stats_text += "💰 Top 5 Users by Balance:\n"
        
        for i, (uid, data) in enumerate(top_users, 1):
            try:
                user_info = await context.bot.get_chat(uid)
                username = user_info.username or user_info.first_name
                stats_text += f"{i}. {username}: ₹{data.get('balance', 0)}\n"
            except:
                stats_text += f"{i}. User {uid}: ₹{data.get('balance', 0)}\n"
        
        stats_text += "\n🔗 Top 5 Referrers:\n"
        for i, (uid, data) in enumerate(top_referrers, 1):
            try:
                user_info = await context.bot.get_chat(uid)
                username = user_info.username or user_info.first_name
                stats_text += f"{i}. {username}: {len(data.get('referred_users', []))} referrals\n"
            except:
                stats_text += f"{i}. User {uid}: {len(data.get('referred_users', []))} referrals\n"
        
        # Add buttons for different stats views
        stats_keyboard = [
            [InlineKeyboardButton("📊 Daily Active Users", callback_data="admin_stats_daily")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]
        ]
        
        await query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(stats_keyboard)
        )
    
    elif query.data == "admin_stats_daily" and user_id in ADMIN_IDS:
        # Show users who claimed bonus today
        today = datetime.now().date()
        active_users = [uid for uid, date in daily_bonus_claimed.items() if date == today]
        
        stats_text = "📊 Daily Active Users\n\n"
        stats_text += f"Users who claimed bonus today ({today}):\n"
        
        if active_users:
            for i, uid in enumerate(active_users[:10], 1):  # Show top 10
                try:
                    user_info = await context.bot.get_chat(uid)
                    username = user_info.username or user_info.first_name
                    stats_text += f"{i}. {username} (ID: {uid})\n"
                except:
                    stats_text += f"{i}. User {uid}\n"
            
            if len(active_users) > 10:
                stats_text += f"\n...and {len(active_users) - 10} more users"
        else:
            stats_text += "No users have claimed bonus today."
        
        await query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Stats", callback_data="admin_stats")]])
        )
    
    elif query.data == "admin_channel" and user_id in ADMIN_IDS:
        await query.edit_message_text(
            text=f"📢 Set Required Channel\n\n"
                 f"Current channel: {required_channel['username'] or 'Not set'}\n\n"
                 f"Please enter the username of the channel users must join (without @):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
        return ADMIN_CHANNEL_SET
    
    elif query.data == "admin_broadcast" and user_id in ADMIN_IDS:
        await query.edit_message_text(
            text=f"📣 Broadcast Message\n\n"
                 f"To send a message to all users, use the command:\n"
                 f"/broadcast <message>\n\n"
                 f"Example: /broadcast Hello everyone! New features added!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    elif query.data == "back":
        # Return to main menu with 2x2 layout
        keyboard = [
            [
                InlineKeyboardButton("💰 Balance", callback_data="balance"),
                InlineKeyboardButton("🔗 My Referral Link", callback_data="referral"),
            ],
            [
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
                InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"),
            ],
            [
                InlineKeyboardButton("ℹ️ How to Earn", callback_data="how_to_earn"),
            ],
        ]
        
        # Add admin button if user is admin
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"👋 Welcome to the Referral Earning Bot!\n\n"
                 f"Earn ₹5 for each person who joins using your referral link.\n\n"
                 f"Use the buttons below to navigate:",
            reply_markup=reply_markup,
        )

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin setting a required channel."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    channel_username = update.message.text.strip().replace("@", "")
    
    # Validate the channel
    try:
        chat = await context.bot.get_chat(f"@{channel_username}")
        required_channel["username"] = channel_username
        required_channel["id"] = chat.id
        
        # Check if bot is admin in the channel
        bot_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=context.bot.id)
        is_admin = bot_member.status in ['administrator', 'creator']
        
        if not is_admin:
            warning = "\n\n⚠️ Warning: The bot is not an admin in this channel. Add the bot as admin for better functionality."
        else:
            warning = ""
        
        await update.message.reply_text(
            f"✅ Required channel set to @{channel_username}!{warning}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error setting channel: {str(e)}\n\nMake sure the channel exists and the bot is a member.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    return MAIN_MENU

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process withdrawal request."""
    user_id = update.effective_user.id
    upi_id = update.message.text.strip()
    
    # Check channel membership
    is_member = await check_channel_membership(user_id, context)
    if not is_member and required_channel["username"]:
        channel_link = f"https://t.me/{required_channel['username']}"
        await update.message.reply_text(
            f"⚠️ You must join our channel before you can withdraw!\n\n"
            f"Please join: {channel_link}\n\n"
            f"After joining, try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=channel_link)]])
        )
        return MAIN_MENU
    
    # Check if user has sufficient balance
    balance = user_data.get(user_id, {}).get("balance", 0)
    if balance < 50:
        await update.message.reply_text(
            f"❌ Insufficient balance for withdrawal!\n\n"
            f"Your current balance: ₹{balance}\n"
            f"You need at least ₹50 to withdraw.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Check if UPI ID format is valid (basic check)
    if "@" not in upi_id:
        await update.message.reply_text(
            "❌ Invalid UPI ID format. Please enter a valid UPI ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Process withdrawal (in a real bot, you would integrate with payment system)
    await update.message.reply_text(
        f"✅ Withdrawal request submitted!\n\n"
        f"Amount: ₹{balance}\n"
        f"UPI ID: {upi_id}\n\n"
        f"Your payment will be processed within 24 hours. Thank you for your patience!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
    )
    
    # Notify admins about withdrawal request
    for admin_id in ADMIN_IDS:
        try:
            user_info = await context.bot.get_chat(user_id)
            username = user_info.username or user_info.first_name
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"💸 New Withdrawal Request\n\n"
                     f"User: {username} (ID: {user_id})\n"
                     f"Amount: ₹{balance}\n"
                     f"UPI ID: {upi_id}\n\n"
                     f"Please process this payment manually."
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    # Reset user balance after withdrawal
    user_data[user_id]["balance"] = 0
    
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Operation cancelled. Type /start to begin again."
    )
    return ConversationHandler.END

# Admin commands
async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to add balance to a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if target_id not in user_data:
            user_data[target_id] = {"balance": 0, "referred_users": []}
        
        user_data[target_id]["balance"] += amount
        
        await update.message.reply_text(
            f"✅ Added ₹{amount} to user {target_id}.\n"
            f"New balance: ₹{user_data[target_id]['balance']}"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount. Please use numbers only.")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to broadcast a message to all users."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text("📣 Starting broadcast...")
    
    for uid in user_data.keys():
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 Announcement\n\n{message}"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {uid}: {e}")
    
    await update.message.reply_text(
        f"📣 Broadcast completed!\n\n"
        f"✅ Successfully sent: {sent_count}\n"
        f"❌ Failed: {failed_count}"
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin searching for a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    search_id = update.message.text.strip()
    
    try:
        search_id = int(search_id)
        if search_id in user_data:
            balance = user_data[search_id]["balance"]
            referred_count = len(user_data[search_id].get("referred_users", []))
            
            try:
                user_info = await context.bot.get_chat(search_id)
                username = user_info.username or user_info.first_name
                user_text = f"Username: {username}\n"
            except:
                user_text = f"Username: Unknown\n"
            
            await update.message.reply_text(
                f"🔍 User Found\n\n"
                f"User ID: {search_id}\n"
                f"{user_text}"
                f"Balance: ₹{balance}\n"
                f"Referrals: {referred_count}\n\n"
                f"To modify balance use:\n/add_balance {search_id} <amount>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
        else:
            await update.message.reply_text(
                f"❌ User not found\n\nNo user with ID {search_id} exists in the database.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please enter a numeric user ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    return MAIN_MENU

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(button_handler),
            ],
            WITHDRAWAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdrawal),
                CallbackQueryHandler(button_handler),
            ],
            ADMIN_CHANNEL_SET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_channel),
                CallbackQueryHandler(button_handler),
            ],
            ADMIN_SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_user),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    # Add admin commands
    application.add_handler(CommandHandler("add_balance", admin_add_balance))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))

    # Return to main menu with 2x2 layout
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("🔗 My Referral Link", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"),
        ],
        [
            InlineKeyboardButton("ℹ️ How to Earn", callback_data="how_to_earn"),
        ],
    ]
    
    # Add admin button if user is admin
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=f"👋 Welcome to the Referral Earning Bot!\n\n"
             f"Earn ₹5 for each person who joins using your referral link.\n\n"
             f"Use the buttons below to navigate:",
        reply_markup=reply_markup,
    )
    
    return MAIN_MENU

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin setting a required channel."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    channel_username = update.message.text.strip().replace("@", "")
    
    # Validate the channel
    try:
        chat = await context.bot.get_chat(f"@{channel_username}")
        required_channel["username"] = channel_username
        required_channel["id"] = chat.id
        
        # Check if bot is admin in the channel
        bot_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=context.bot.id)
        is_admin = bot_member.status in ['administrator', 'creator']
        
        if not is_admin:
            warning = "\n\n⚠️ Warning: The bot is not an admin in this channel. Add the bot as admin for better functionality."
        else:
            warning = ""
        
        await update.message.reply_text(
            f"✅ Required channel set to @{channel_username}!{warning}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error setting channel: {str(e)}\n\nMake sure the channel exists and the bot is a member.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    return MAIN_MENU

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process withdrawal request."""
    user_id = update.effective_user.id
    upi_id = update.message.text.strip()
    
    # Check channel membership
    is_member = await check_channel_membership(user_id, context)
    if not is_member and required_channel["username"]:
        channel_link = f"https://t.me/{required_channel['username']}"
        await update.message.reply_text(
            f"⚠️ You must join our channel before you can withdraw!\n\n"
            f"Please join: {channel_link}\n\n"
            f"After joining, try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=channel_link)]])
        )
        return MAIN_MENU
    
    # Check if user has sufficient balance
    balance = user_data.get(user_id, {}).get("balance", 0)
    if balance < 50:
        await update.message.reply_text(
            f"❌ Insufficient balance for withdrawal!\n\n"
            f"Your current balance: ₹{balance}\n"
            f"You need at least ₹50 to withdraw.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Check if UPI ID format is valid (basic check)
    if "@" not in upi_id:
        await update.message.reply_text(
            "❌ Invalid UPI ID format. Please enter a valid UPI ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Process withdrawal (in a real bot, you would integrate with payment system)
    await update.message.reply_text(
        f"✅ Withdrawal request submitted!\n\n"
        f"Amount: ₹{balance}\n"
        f"UPI ID: {upi_id}\n\n"
        f"Your payment will be processed within 24 hours. Thank you for your patience!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
    )
    
    # Notify admins about withdrawal request
    for admin_id in ADMIN_IDS:
        try:
            user_info = await context.bot.get_chat(user_id)
            username = user_info.username or user_info.first_name
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"💸 New Withdrawal Request\n\n"
                     f"User: {username} (ID: {user_id})\n"
                     f"Amount: ₹{balance}\n"
                     f"UPI ID: {upi_id}\n\n"
                     f"Please process this payment manually."
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    # Reset user balance after withdrawal
    user_data[user_id]["balance"] = 0
    
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Operation cancelled. Type /start to begin again."
    )
    return ConversationHandler.END

# Admin commands
async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to add balance to a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if target_id not in user_data:
            user_data[target_id] = {"balance": 0, "referred_users": []}
        
        user_data[target_id]["balance"] += amount
        
        await update.message.reply_text(
            f"✅ Added ₹{amount} to user {target_id}.\n"
            f"New balance: ₹{user_data[target_id]['balance']}"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount. Please use numbers only.")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to broadcast a message to all users."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text("📣 Starting broadcast...")
    
    for uid in user_data.keys():
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 Announcement\n\n{message}"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {uid}: {e}")
    
    await update.message.reply_text(
        f"📣 Broadcast completed!\n\n"
        f"✅ Successfully sent: {sent_count}\n"
        f"❌ Failed: {failed_count}"
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin searching for a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    search_id = update.message.text.strip()
    
    try:
        search_id = int(search_id)
        if search_id in user_data:
            balance = user_data[search_id]["balance"]
            referred_count = len(user_data[search_id].get("referred_users", []))
            
            try:
                user_info = await context.bot.get_chat(search_id)
                username = user_info.username or user_info.first_name
                user_text = f"Username: {username}\n"
            except:
                user_text = f"Username: Unknown\n"
            
            await update.message.reply_text(
                f"🔍 User Found\n\n"
                f"User ID: {search_id}\n"
                f"{user_text}"
                f"Balance: ₹{balance}\n"
                f"Referrals: {referred_count}\n\n"
                f"To modify balance use:\n/add_balance {search_id} <amount>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
        else:
            await update.message.reply_text(
                f"❌ User not found\n\nNo user with ID {search_id} exists in the database.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please enter a numeric user ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    return MAIN_MENU

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(button_handler),
            ],
            WITHDRAWAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdrawal),
                CallbackQueryHandler(button_handler),
            ],
            ADMIN_CHANNEL_SET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_channel),
                CallbackQueryHandler(button_handler),
            ],
            ADMIN_SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_user),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    # Add admin commands
    application.add_handler(CommandHandler("add_balance", admin_add_balance))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))

    # Return to main menu with 2x2 layout
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("🔗 My Referral Link", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"),
        ],
        [
            InlineKeyboardButton("ℹ️ How to Earn", callback_data="how_to_earn"),
        ],
    ]
    
    # Add admin button if user is admin
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=f"👋 Welcome to the Referral Earning Bot!\n\n"
             f"Earn ₹5 for each person who joins using your referral link.\n\n"
             f"Use the buttons below to navigate:",
        reply_markup=reply_markup,
    )
    
    return MAIN_MENU

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin setting a required channel."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    channel_username = update.message.text.strip().replace("@", "")
    
    # Validate the channel
    try:
        chat = await context.bot.get_chat(f"@{channel_username}")
        required_channel["username"] = channel_username
        required_channel["id"] = chat.id
        
        # Check if bot is admin in the channel
        bot_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=context.bot.id)
        is_admin = bot_member.status in ['administrator', 'creator']
        
        if not is_admin:
            warning = "\n\n⚠️ Warning: The bot is not an admin in this channel. Add the bot as admin for better functionality."
        else:
            warning = ""
        
        await update.message.reply_text(
            f"✅ Required channel set to @{channel_username}!{warning}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error setting channel: {str(e)}\n\nMake sure the channel exists and the bot is a member.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    return MAIN_MENU

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process withdrawal request."""
    user_id = update.effective_user.id
    upi_id = update.message.text.strip()
    
    # Check channel membership
    is_member = await check_channel_membership(user_id, context)
    if not is_member and required_channel["username"]:
        channel_link = f"https://t.me/{required_channel['username']}"
        await update.message.reply_text(
            f"⚠️ You must join our channel before you can withdraw!\n\n"
            f"Please join: {channel_link}\n\n"
            f"After joining, try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=channel_link)]])
        )
        return MAIN_MENU
    
    # Check if user has sufficient balance
    balance = user_data.get(user_id, {}).get("balance", 0)
    if balance < 50:
        await update.message.reply_text(
            f"❌ Insufficient balance for withdrawal!\n\n"
            f"Your current balance: ₹{balance}\n"
            f"You need at least ₹50 to withdraw.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Check if UPI ID format is valid (basic check)
    if "@" not in upi_id:
        await update.message.reply_text(
            "❌ Invalid UPI ID format. Please enter a valid UPI ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Process withdrawal (in a real bot, you would integrate with payment system)
    await update.message.reply_text(
        f"✅ Withdrawal request submitted!\n\n"
        f"Amount: ₹{balance}\n"
        f"UPI ID: {upi_id}\n\n"
        f"Your payment will be processed within 24 hours. Thank you for your patience!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
    )
    
    # Notify admins about withdrawal request
    for admin_id in ADMIN_IDS:
        try:
            user_info = await context.bot.get_chat(user_id)
            username = user_info.username or user_info.first_name
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"💸 New Withdrawal Request\n\n"
                     f"User: {username} (ID: {user_id})\n"
                     f"Amount: ₹{balance}\n"
                     f"UPI ID: {upi_id}\n\n"
                     f"Please process this payment manually."
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    # Reset user balance after withdrawal
    user_data[user_id]["balance"] = 0
    
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Operation cancelled. Type /start to begin again."
    )
    return ConversationHandler.END

# Admin commands
async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to add balance to a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if target_id not in user_data:
            user_data[target_id] = {"balance": 0, "referred_users": []}
        
        user_data[target_id]["balance"] += amount
        
        await update.message.reply_text(
            f"✅ Added ₹{amount} to user {target_id}.\n"
            f"New balance: ₹{user_data[target_id]['balance']}"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount. Please use numbers only.")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to broadcast a message to all users."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text("📣 Starting broadcast...")
    
    for uid in user_data.keys():
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 Announcement\n\n{message}"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {uid}: {e}")
    
    await update.message.reply_text(
        f"📣 Broadcast completed!\n\n"
        f"✅ Successfully sent: {sent_count}\n"
        f"❌ Failed: {failed_count}"
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin searching for a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    search_id = update.message.text.strip()
    
    try:
        search_id = int(search_id)
        if search_id in user_data:
            balance = user_data[search_id]["balance"]
            referred_count = len(user_data[search_id].get("referred_users", []))
            
            try:
                user_info = await context.bot.get_chat(search_id)
                username = user_info.username or user_info.first_name
                user_text = f"Username: {username}\n"
            except:
                user_text = f"Username: Unknown\n"
            
            await update.message.reply_text(
                f"🔍 User Found\n\n"
                f"User ID: {search_id}\n"
                f"{user_text}"
                f"Balance: ₹{balance}\n"
                f"Referrals: {referred_count}\n\n"
                f"To modify balance use:\n/add_balance {search_id} <amount>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
        else:
            await update.message.reply_text(
                f"❌ User not found\n\nNo user with ID {search_id} exists in the database.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please enter a numeric user ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    return MAIN_MENU

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(button_handler),
            ],
            WITHDRAWAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdrawal),
                CallbackQueryHandler(button_handler),
            ],
            ADMIN_CHANNEL_SET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_channel),
                CallbackQueryHandler(button_handler),
            ],
            ADMIN_SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_user),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    # Add admin commands
    application.add_handler(CommandHandler("add_balance", admin_add_balance))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))

    # Return to main menu with 2x2 layout
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("🔗 My Referral Link", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"),
        ],
        [
            InlineKeyboardButton("ℹ️ How to Earn", callback_data="how_to_earn"),
        ],
    ]
    
    # Add admin button if user is admin
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=f"👋 Welcome to the Referral Earning Bot!\n\n"
             f"Earn ₹5 for each person who joins using your referral link.\n\n"
             f"Use the buttons below to navigate:",
        reply_markup=reply_markup,
    )
    
    return MAIN_MENU

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin setting a required channel."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    channel_username = update.message.text.strip().replace("@", "")
    
    # Validate the channel
    try:
        chat = await context.bot.get_chat(f"@{channel_username}")
        required_channel["username"] = channel_username
        required_channel["id"] = chat.id
        
        # Check if bot is admin in the channel
        bot_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=context.bot.id)
        is_admin = bot_member.status in ['administrator', 'creator']
        
        if not is_admin:
            warning = "\n\n⚠️ Warning: The bot is not an admin in this channel. Add the bot as admin for better functionality."
        else:
            warning = ""
        
        await update.message.reply_text(
            f"✅ Required channel set to @{channel_username}!{warning}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error setting channel: {str(e)}\n\nMake sure the channel exists and the bot is a member.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )
    
    return MAIN_MENU

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process withdrawal request."""
    user_id = update.effective_user.id
    upi_id = update.message.text.strip()
    
    # Check channel membership
    is_member = await check_channel_membership(user_id, context)
    if not is_member and required_channel["username"]:
        channel_link = f"https://t.me/{required_channel['username']}"
        await update.message.reply_text(
            f"⚠️ You must join our channel before you can withdraw!\n\n"
            f"Please join: {channel_link}\n\n"
            f"After joining, try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=channel_link)]])
        )
        return MAIN_MENU
    
    # Check if user has sufficient balance
    balance = user_data.get(user_id, {}).get("balance", 0)
    if balance < 50:
        await update.message.reply_text(
            f"❌ Insufficient balance for withdrawal!\n\n"
            f"Your current balance: ₹{balance}\n"
            f"You need at least ₹50 to withdraw.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Check if UPI ID format is valid (basic check)
    if "@" not in upi_id:
        await update.message.reply_text(
            "❌ Invalid UPI ID format. Please enter a valid UPI ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
        )
        return MAIN_MENU
    
    # Process withdrawal (in a real bot, you would integrate with payment system)
    await update.message.reply_text(
        f"✅ Withdrawal request submitted!\n\n"
        f"Amount: ₹{balance}\n"
        f"UPI ID: {upi_id}\n\n"
        f"Your payment will be processed within 24 hours. Thank you for your patience!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])
    )
    
    # Notify admins about withdrawal request
    for admin_id in ADMIN_IDS:
        try:
            user_info = await context.bot.get_chat(user_id)
            username = user_info.username or user_info.first_name
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"💸 New Withdrawal Request\n\n"
                     f"User: {username} (ID: {user_id})\n"
                     f"Amount: ₹{balance}\n"
                     f"UPI ID: {upi_id}\n\n"
                     f"Please process this payment manually."
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    # Reset user balance after withdrawal
    user_data[user_id]["balance"] = 0
    
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Operation cancelled. Type /start to begin again."
    )
    return ConversationHandler.END

# Admin commands
async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to add balance to a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args or len(context.args) != 2:
        await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if target_id not in user_data:
            user_data[target_id] = {"balance": 0, "referred_users": []}
        
        user_data[target_id]["balance"] += amount
        
        await update.message.reply_text(
            f"✅ Added ₹{amount} to user {target_id}.\n"
            f"New balance: ₹{user_data[target_id]['balance']}"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount. Please use numbers only.")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to broadcast a message to all users."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text("📣 Starting broadcast...")
    
    for uid in user_data.keys():
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 Announcement\n\n{message}"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {uid}: {e}")
    
    await update.message.reply_text(
        f"📣 Broadcast completed!\n\n"
        f"✅ Successfully sent: {sent_count}\n"
        f"❌ Failed: {failed_count}"
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin searching for a user."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ You don't have permission to use this command.")
        return MAIN_MENU
    
    search_id = update.message.text.strip()
    
    try:
        search_id = int(search_id)
        if search_id in user_data:
            balance = user_data[search_id]["balance"]
            referred_count = len(user_data[search_id].get("referred_users", []))
            
            try:
                user_info = await context.bot.get_chat(search_id)
                username = user_info.username or user_info.first_name
                user_text = f"Username: {username}\n"
            except:
                user_text = f"Username: Unknown\n"
            
            await update.message.reply_text(
                f"🔍 User Found\n\n"
                f"User ID: {search_id}\n"
                f"{user_text}"
                f"Balance: ₹{balance}\n"
                f"Referrals: {referred_count}\n\n"
                f"To modify balance use:\n/add_balance {search_id} <amount>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
        else:
            await update.message.reply_text(
                f"❌ User not found\n\nNo user with ID {search_id} exists in the database.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please enter a numeric user ID.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]])
        )