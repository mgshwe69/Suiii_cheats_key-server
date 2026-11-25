
import os
import secrets
import logging
import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# CONFIGURATION - Railway Environment Variables
# ==========================================

BOT_TOKEN = "9072241056:AAGsw9jTjnYpsE1ljkjfqpMQjzzAz8XKaOc"
OWNER_ID = 7777899827
WORKER_URL = "https://suiiicheatskey.sultanreew.workers.dev"
ADMIN_SECRET = "SUIII_Admin_7xK9pQ2mV8nL4wR6tY3aB5cD"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

admins = set()
pending_actions = {}

# ==========================================
# CLOUDFLARE API
# ==========================================

async def worker_create_key(key, expires_at, device_limit):
    payload = {
        "key": key,
        "expires_at": expires_at,
        "device_limit": device_limit,
    }

    headers = {
        "X-Admin-Secret": ADMIN_SECRET,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{WORKER_URL}/create",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


# ==========================================
# PERMISSIONS
# ==========================================

def is_owner(user_id):
    return user_id == OWNER_ID


def is_admin(user_id):
    return user_id == OWNER_ID or user_id in admins


# ==========================================
# KEY GENERATOR
# ==========================================

def generate_key():
    return "SUIII-" + secrets.token_hex(8).upper()


def format_expiry(days):
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    return int(expiry.timestamp() * 1000)


# ==========================================
# MENUS
# ==========================================

def main_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton("Generate New Key", callback_data="generate")],
        [InlineKeyboardButton("Dashboard", callback_data="dashboard")],
    ]

    if is_owner(user_id):
        buttons.append([
            InlineKeyboardButton("Admin Management", callback_data="admin_menu")
        ])

    return InlineKeyboardMarkup(buttons)


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Admin", callback_data="add_admin")],
        [InlineKeyboardButton("Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("View Admins", callback_data="view_admins")],
        [InlineKeyboardButton("Back", callback_data="home")],
    ])


# ==========================================
# START
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text(
            f"Access denied.\nYour Telegram ID: {user_id}"
        )
        return

    text = (
        "<b>SUIII KEY MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Welcome to your license dashboard.\n\n"
        "Select an option:"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard(user_id),
    )


# ==========================================
# CALLBACK HANDLER
# ==========================================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    action = query.data

    if not is_admin(user_id):
        await query.edit_message_text("Access denied.")
        return

    if action == "home":
        await query.edit_message_text(
            "SUIII KEY MANAGEMENT",
            reply_markup=main_keyboard(user_id),
        )

    elif action == "dashboard":
        await query.edit_message_text(
            "KEY MANAGEMENT DASHBOARD\n\n"
            "Use Generate New Key to create a license.",
            reply_markup=main_keyboard(user_id),
        )

    elif action == "generate":
        pending_actions[user_id] = {"step": "expiry"}

        await query.edit_message_text(
            "Select key expiry:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1 Day", callback_data="days_1")],
                [InlineKeyboardButton("7 Days", callback_data="days_7")],
                [InlineKeyboardButton("30 Days", callback_data="days_30")],
                [InlineKeyboardButton("90 Days", callback_data="days_90")],
                [InlineKeyboardButton("365 Days", callback_data="days_365")],
            ]),
        )

    elif action.startswith("days_"):
        days = int(action.split("_")[1])

        pending_actions[user_id] = {
            "step": "device_limit",
            "days": days,
        }

        await query.edit_message_text(
            f"Expiry selected: {days} days\n\nSelect device limit:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1 Device", callback_data="devices_1")],
                [InlineKeyboardButton("2 Devices", callback_data="devices_2")],
                [InlineKeyboardButton("3 Devices", callback_data="devices_3")],
                [InlineKeyboardButton("5 Devices", callback_data="devices_5")],
            ]),
        )

    elif action.startswith("devices_"):
        device_limit = int(action.split("_")[1])
        data = pending_actions.get(user_id)

        if not data or data.get("step") != "device_limit":
            await query.edit_message_text("Session expired. Use /start again.")
            return

        key = generate_key()
        days = data["days"]
        expiry = format_expiry(days)

        try:
            result = await worker_create_key(
                key,
                expiry,
                device_limit,
            )

            if not result.get("success"):
                raise RuntimeError(result.get("message", "Key creation failed"))

            pending_actions.pop(user_id, None)

            await query.edit_message_text(
                "<b>KEY CREATED SUCCESSFULLY</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"Key: <code>{key}</code>\n"
                f"Expiry: {days} days\n"
                f"Device limit: {device_limit}\n\n"
                "Key saved in Cloudflare D1.",
                parse_mode="HTML",
                reply_markup=main_keyboard(user_id),
            )

        except Exception:
            logger.exception("Key creation failed")
            await query.edit_message_text(
                "Key creation failed. Check Worker URL, database schema "
                "and Railway variables."
            )

    elif action == "admin_menu":
        if not is_owner(user_id):
            await query.edit_message_text("Owner access required.")
            return

        await query.edit_message_text(
            "ADMIN MANAGEMENT",
            reply_markup=admin_keyboard(),
        )

    elif action == "add_admin":
        if not is_owner(user_id):
            await query.edit_message_text("Owner access required.")
            return

        pending_actions[user_id] = {"step": "add_admin"}

        await query.edit_message_text(
            "Send the Telegram User ID of the new admin."
        )

    elif action == "remove_admin":
        if not is_owner(user_id):
            await query.edit_message_text("Owner access required.")
            return

        pending_actions[user_id] = {"step": "remove_admin"}

        await query.edit_message_text(
            "Send the Telegram User ID of the admin to remove."
        )

    elif action == "view_admins":
        if not is_owner(user_id):
            await query.edit_message_text("Owner access required.")
            return

        admin_list = "\n".join(str(x) for x in sorted(admins))
        if not admin_list:
            admin_list = "No additional admins."

        await query.edit_message_text(
            f"<b>ADMIN LIST</b>\n\nOwner: <code>{OWNER_ID}</code>\n"
            f"Additional admins:\n<code>{admin_list}</code>",
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )


# ==========================================
# ADMIN TEXT ACTIONS
# ==========================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = pending_actions.get(user_id)

    if not data:
        return

    if not is_owner(user_id):
        await update.message.reply_text("Owner access required.")
        return

    if data["step"] not in ("add_admin", "remove_admin"):
        return

    try:
        target_id = int(update.message.text.strip())

        if target_id <= 0 or target_id == OWNER_ID:
            raise ValueError

    except ValueError:
        await update.message.reply_text("Enter a valid Telegram User ID.")
        return

    if data["step"] == "add_admin":
        if target_id in admins:
            message = "This user is already an admin."
        else:
            admins.add(target_id)
            message = f"Admin added: {target_id}"

    else:
        if target_id in admins:
            admins.remove(target_id)
            message = f"Admin removed: {target_id}"
        else:
            message = "This user is not an admin."

    pending_actions.pop(user_id, None)

    await update.message.reply_text(
        message,
        reply_markup=admin_keyboard(),
    )


# ==========================================
# COMMANDS
# ==========================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_actions.pop(update.effective_user.id, None)
    await update.message.reply_text("Action cancelled.")


async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /addadmin USER_ID")
        return

    try:
        target_id = int(context.args[0])

        if target_id <= 0 or target_id == OWNER_ID:
            raise ValueError

        admins.add(target_id)
        await update.message.reply_text(f"Admin added: {target_id}")

    except ValueError:
        await update.message.reply_text("Invalid Telegram ID.")


async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /removeadmin USER_ID")
        return

    try:
        target_id = int(context.args[0])
        admins.discard(target_id)
        await update.message.reply_text(f"Admin removed: {target_id}")

    except ValueError:
        await update.message.reply_text("Invalid Telegram ID.")


# ==========================================
# MAIN
# ==========================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("addadmin", add_admin_command))
    app.add_handler(CommandHandler("removeadmin", remove_admin_command))

    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    logger.info("SUIII KEY BOT started")
    app.run_polling()


if __name__ == "__main__":
    main()
