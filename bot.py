import os, secrets, datetime
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from supabase import create_client, Client

# ==========================================
# YAHAN APNI ASLI KEYS DAAL (Quotes "" hatana mat)
# ==========================================
SUPABASE_URL = "https://dlebzfhvrokhkmpqqjuy.supabase.co"
SUPABASE_SECRET = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRsZWJ6Zmh2cm9raGttcHFxanV5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5NTMzODI1MiwiZXhwIjoyMTEwOTE0MjUyfQ.Wkg7LmSw4UAHyfSmliz3_MDkmq3JSw2wuOcwsldnyNc" 
BOT_TOKEN = "9072241056:AAGsw9jTjnYpsE1ljkjfqpMQjzzAz8XKaOc"
OWNER_ID = 7777899827  # Yahan apna asli Telegram ID daalna (bina quotes ke)
# ==========================================

sb: Client = create_client(SUPABASE_URL, SUPABASE_SECRET)

# --- DUMMY WEB SERVER (Render ke liye) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()
# -----------------------------------------

def gen_key():
    return "SUIII-" + secrets.token_hex(4).upper()

def is_authorized(uid):
    if uid == OWNER_ID: return True
    try:
        res = sb.table("authorized_users").select("*").eq("telegram_id", uid).execute()
        return len(res.data) > 0
    except:
        return False

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_authorized(uid):
        msg = (
            f"<b>ACCESS REQUIRED</b>\n"
            f"───────────────\n"
            f"Your ID: <code>{uid}</code>\n\n"
            f"Send this ID to the owner.\n"
            f"Once approved, send /start\n\n"
            f'<a href="https://t.me/rovixbyultimate">SUIII_CHEATS</a>'
        )
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Generate Custom Key", callback_data="gen_start")],
        [InlineKeyboardButton("📋 My Keys", callback_data="mykeys")]
    ])
    await update.message.reply_text(
        "<b>MAIN MENU</b>\nSelect an option below:\n\n"
        'Join: <a href="https://t.me/rovixbyultimate">SUIII_CHEATS</a>\n'
        "Bot: @Key_cr7_shopbot", 
        parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True
    )

async def approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("Only owner can approve.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    target_id = int(ctx.args[0])
    try:
        sb.table("authorized_users").insert({"telegram_id": target_id}).execute()
        await update.message.reply_text(f"✅ Approved <code>{target_id}</code>\nUser can now /start", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error (already approved?): {e}")

async def generate_key_custom(update_or_query, uid, days, devices):
    key = gen_key()
    expires = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat()
    
    try:
        sb.table("license_keys").insert({
            "key_code": key,
            "telegram_id": uid,
            "duration_days": days,
            "expires_at": expires,
            "status": "active",
            "device_limit": devices
        }).execute()
    except Exception as e:
        text = f"DB Error: {e}"
        if isinstance(update_or_query, Update):
            await update_or_query.message.reply_text(text)
        else:
            await update_or_query.edit_message_text(text)
        return

    dev_txt = "Unlimited" if devices >= 999 else str(devices)
    
    text = (
        f"<b>KEY GENERATED (Supabase)</b>\n"
        f"───────────────\n"
        f"<code>{key}</code>\n"
        f"───────────────\n"
        f"<b>Duration</b> <code>{days} days</code>\n"
        f"<b>Expiry</b> <code>{expires[:10]}</code>\n"
        f"<b>Devices</b> <code>{dev_txt}</code>\n"
        f"<b>Status</b> <code>Active</code>\n\n"
        f"<i>Tap the key to copy it.</i>\n\n"
        f'<a href="https://t.me/rovixbyultimate">SUIII_CHEATS</a> | @Key_cr7_shopbot'
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Unbind HWID", callback_data=f"unbind_{key}"), InlineKeyboardButton("Ban Key", callback_data=f"ban_{key}")],
        [InlineKeyboardButton("Share Format", callback_data=f"share_{key}"), InlineKeyboardButton("Delete Key", callback_data=f"delete_{key}")],
        [InlineKeyboardButton("< Back to Menu", callback_data="menu_main")]
    ])
    
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    else:
        await update_or_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    
    if not is_authorized(uid):
        await q.edit_message_text("Not authorized.")
        return

    if data == "menu_main":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Generate Custom Key", callback_data="gen_start")],
            [InlineKeyboardButton("📋 My Keys", callback_data="mykeys")]
        ])
        await q.edit_message_text(
            "<b>MAIN MENU</b>\nSelect an option below:\n\n"
            'Join: <a href="https://t.me/rovixbyultimate">SUIII_CHEATS</a>\n'
            "Bot: @Key_cr7_shopbot", 
            parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True
        )
        return

    # --- Custom Key Generation Flow ---
    if data == "gen_start":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="gen_d_1"), InlineKeyboardButton("7 Days", callback_data="gen_d_7")],
            [InlineKeyboardButton("30 Days", callback_data="gen_d_30"), InlineKeyboardButton("Lifetime", callback_data="gen_d_3650")],
            [InlineKeyboardButton("< Back", callback_data="menu_main")]
        ])
        await q.edit_message_text("<b>Step 1: Choose Duration (Days)</b>", parse_mode="HTML", reply_markup=kb)
        return
        
    if data.startswith("gen_d_"):
        days = int(data.split("_")[2])
        ctx.user_data['gen_days'] = days
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Device", callback_data="gen_dev_1"), InlineKeyboardButton("2 Devices", callback_data="gen_dev_2")],
            [InlineKeyboardButton("3 Devices", callback_data="gen_dev_3"), InlineKeyboardButton("Unlimited", callback_data="gen_dev_999")],
            [InlineKeyboardButton("< Back", callback_data="gen_start")]
        ])
        await q.edit_message_text(f"<b>Step 2: Choose Device Limit</b>\n(Selected: {days} Days)", parse_mode="HTML", reply_markup=kb)
        return
        
    if data.startswith("gen_dev_"):
        devices = int(data.split("_")[2])
        days = ctx.user_data.get('gen_days', 1)
        await generate_key_custom(q, uid, days, devices)
        return
    # ----------------------------------

    if data == "mykeys":
        res = sb.table("license_keys").select("*").eq("telegram_id", uid).order("created_at", desc=True).limit(10).execute()
        if not res.data:
            await q.edit_message_text("No keys found.")
            return
        lines = ["<b>Your Keys:</b>\n"]
        for k in res.data:
            hwid = "🔒" if k.get("hwid") else "🔓"
            dl = k.get('device_limit', 1) if k.get('device_limit') else 1
            dl_text = "Unlimited" if dl >= 999 else f"{dl} Dev"
            lines.append(f"<code>{k['key_code']}</code> | {k['status']} | {hwid} | {dl_text}")
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("< Back to Menu", callback_data="menu_main")]])
        await q.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
        return

    action, key = data.split("_", 1)
    
    if action == "unbind":
        sb.table("license_keys").update({"hwid": None}).eq("key_code", key).execute()
        await q.answer("HWID Unbound!", show_alert=True)
    elif action == "ban":
        sb.table("license_keys").update({"status": "banned"}).eq("key_code", key).execute()
        await q.answer("Key Banned!", show_alert=True)
        msg = q.message.text_html.replace("<b>Status</b> <code>Active</code>", "<b>Status</b> <code>Banned</code>")
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=q.message.reply_markup)
    elif action == "share":
        share_msg = f"Key: <code>{key}</code>\nBot: @Key_cr7_shopbot\nJoin: https://t.me/rovixbyultimate"
        await q.message.reply_text(share_msg, parse_mode="HTML", disable_web_page_preview=True)
        await q.answer("Share format sent!")
    elif action == "delete":
        sb.table("license_keys").delete().eq("key_code", key).execute()
        await q.edit_message_text(f"🗑 Key <code>{key}</code> deleted.", parse_mode="HTML")

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
