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

def log_action(action, admin_id, target_key, details):
    try:
        sb.table("bot_logs").insert({
            "action": action,
            "admin_id": admin_id,
            "target_key": target_key,
            "details": details
        }).execute()
    except Exception as e:
        print(f"Log fail: {e}")

def is_authorized(uid):
    if uid == OWNER_ID: return True
    try:
        res = sb.table("authorized_users").select("*").eq("telegram_id", uid).execute()
        if len(res.data) > 0:
            return not res.data[0].get("is_blocked", False)
        return False
    except:
        return False

async def get_main_menu(uid):
    kb_list = [
        [InlineKeyboardButton("🔑 Generate Custom Key", callback_data="gen_start")],
        [InlineKeyboardButton("📋 My Keys", callback_data="mykeys")]
    ]
    if uid == OWNER_ID:
        kb_list.append([InlineKeyboardButton("👥 User Management", callback_data="admin_users")])
        kb_list.append([InlineKeyboardButton("📊 Bot Activity Logs", callback_data="admin_logs")])
    
    kb = InlineKeyboardMarkup(kb_list)
    text = (
        "💎 <b>SUIII_CHEATS DASHBOARD</b> 💎\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to the premium key management system.\n"
        "Select an option below to proceed.\n\n"
        "🌐 <b>Channel:</b> <a href='https://t.me/rovixbyultimate'>SUIII_CHEATS</a>\n"
        "🤖 <b>Bot:</b> @Key_cr7_shopbot"
    )
    return text, kb

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_authorized(uid):
        msg = (
            f"⛔ <b>ACCESS REQUIRED</b> ⛔\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Your Telegram ID: <code>{uid}</code>\n\n"
            f"Send this ID to the owner for approval.\n"
            f"Once approved, use /start again.\n\n"
            f'<a href="https://t.me/rovixbyultimate">Join Support Channel</a>'
        )
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
        return

    text, kb = await get_main_menu(uid)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)

# ================= ADMIN COMMANDS =================
async def approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID: return
    if not ctx.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    target_id = int(ctx.args[0])
    try:
        sb.table("authorized_users").insert({"telegram_id": target_id}).execute()
        log_action("USER_APPROVED", uid, str(target_id), "User approved.")
        await update.message.reply_text(f"✅ Approved <code>{target_id}</code>\nUser can now /start", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error (already approved?): {e}")

async def block_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID: return
    if not ctx.args:
        await update.message.reply_text("Usage: /block <user_id>")
        return
    target_id = int(ctx.args[0])
    try:
        sb.table("authorized_users").update({"is_blocked": True}).eq("telegram_id", target_id).execute()
        log_action("USER_BLOCKED", uid, str(target_id), "User blocked.")
        await update.message.reply_text(f"🚫 User <code>{target_id}</code> has been blocked.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def unblock_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID: return
    if not ctx.args:
        await update.message.reply_text("Usage: /unblock <user_id>")
        return
    target_id = int(ctx.args[0])
    try:
        sb.table("authorized_users").update({"is_blocked": False}).eq("telegram_id", target_id).execute()
        log_action("USER_UNBLOCKED", uid, str(target_id), "User unblocked.")
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been unblocked.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ================= KEY GENERATOR =================
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
        log_action("KEY_GENERATED", uid, key, f"Days: {days}, Devices: {devices}")
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
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<code>{key}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Duration</b> <code>{days} days</code>\n"
        f"<b>Expiry</b> <code>{expires[:10]}</code>\n"
        f"<b>Devices</b> <code>{dev_txt}</code>\n"
        f"<b>Status</b> <code>Active</code>\n\n"
        f"<i>Tap the key to copy it.</i>\n\n"
        f'<a href="https://t.me/rovixbyultimate">SUIII_CHEATS</a> | @Key_cr7_shopbot'
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Unbind HWID", callback_data=f"unbind_{key}"), InlineKeyboardButton("🚫 Ban Key", callback_data=f"ban_{key}")],
        [InlineKeyboardButton("📄 Share Format", callback_data=f"share_{key}"), InlineKeyboardButton("🗑 Delete Key", callback_data=f"delete_{key}")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
    ])
    
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    else:
        await update_or_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)

# ================= CALLBACK HANDLER =================
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    
    if not is_authorized(uid):
        await q.edit_message_text("Not authorized.")
        return

    if data == "menu_main":
        text, kb = await get_main_menu(uid)
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        return

    # --- Admin Menus ---
    if data == "admin_users":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]])
        text = (
            "<b>👥 USER MANAGEMENT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Use these commands in chat:\n\n"
            "✅ <code>/approve &lt;id&gt;</code> - Allow new user\n"
            "🚫 <code>/block &lt;id&gt;</code> - Block a user\n"
            "🔓 <code>/unblock &lt;id&gt;</code> - Unblock a user"
        )
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        return

    if data == "admin_logs":
        try:
            res = sb.table("bot_logs").select("*").order("created_at", desc=True).limit(10).execute()
            if not res.data:
                await q.edit_message_text("No logs found.")
                return
            lines = ["📊 <b>RECENT ACTIVITY LOGS</b>\n━━━━━━━━━━━━━━━━━━━━"]
            for log in res.data:
                lines.append(f"🔸 <b>{log['action']}</b> | {log['created_at'][:16]}\n   By: <code>{log['admin_id']}</code> | Target: <code>{log['target_key']}</code>")
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_main")]])
            await q.edit_message_text("\n\n".join(lines), parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            await q.edit_message_text(f"Error: {e}")
        return

    # --- Custom Key Generation Flow ---
    if data == "gen_start":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Day", callback_data="gen_d_1"), InlineKeyboardButton("7 Days", callback_data="gen_d_7")],
            [InlineKeyboardButton("30 Days", callback_data="gen_d_30"), InlineKeyboardButton("Lifetime", callback_data="gen_d_3650")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
        ])
        await q.edit_message_text("<b>Step 1: Choose Duration (Days)</b>", parse_mode="HTML", reply_markup=kb)
        return
        
    if data.startswith("gen_d_"):
        days = int(data.split("_")[2])
        ctx.user_data['gen_days'] = days
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Device", callback_data="gen_dev_1"), InlineKeyboardButton("2 Devices", callback_data="gen_dev_2")],
            [InlineKeyboardButton("3 Devices", callback_data="gen_dev_3"), InlineKeyboardButton("Unlimited", callback_data="gen_dev_999")],
            [InlineKeyboardButton("🔙 Back", callback_data="gen_start")]
        ])
        await q.edit_message_text(f"<b>Step 2: Choose Device Limit</b>\n(Selected: {days} Days)", parse_mode="HTML", reply_markup=kb)
        return
        
    if data.startswith("gen_dev_"):
        devices = int(data.split("_")[2])
        days = ctx.user_data.get('gen_days', 1)
        await generate_key_custom(q, uid, days, devices)
        return

    if data == "mykeys":
        res = sb.table("license_keys").select("*").eq("telegram_id", uid).order("created_at", desc=True).limit(10).execute()
        if not res.data:
            await q.edit_message_text("No keys found.")
            return
        lines = ["<b>📋 Your Keys:</b>\n"]
        for k in res.data:
            hwid = "🔒" if k.get("hwid") else "🔓"
            dl = k.get('device_limit', 1) if k.get('device_limit') else 1
            dl_text = "Unlimited" if dl >= 999 else f"{dl} Dev"
            lines.append(f"<code>{k['key_code']}</code> | {k['status']} | {hwid} | {dl_text}")
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]])
        await q.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
        return

    # --- Key Actions (Unbind, Ban, Share, Delete) ---
    action, key = data.split("_", 1)
    
    if action == "unbind":
        sb.table("license_keys").update({"hwid": None}).eq("key_code", key).execute()
        log_action("HWID_UNBOUND", uid, key, "HWID unbound.")
        await q.answer("✅ HWID Unbound successfully!", show_alert=True)
        
    elif action == "ban":
        sb.table("license_keys").update({"status": "banned"}).eq("key_code", key).execute()
        log_action("KEY_BANNED", uid, key, "Key marked as banned.")
        await q.answer("🚫 Key Banned!", show_alert=True)
        msg = q.message.text_html.replace("<b>Status</b> <code>Active</code>", "<b>Status</b> <code>Banned</code>")
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=q.message.reply_markup)
        
    elif action == "share":
        res = sb.table("license_keys").select("*").eq("key_code", key).execute()
        if not res.data:
            await q.answer("Key not found!", show_alert=True)
            return
        
        k = res.data[0]
        hwid = k.get("hwid", "Not Bound")
        status_txt = "🟢 Active" if k.get("status") == "active" else "🔴 Banned"
        dev_limit = k.get("device_limit", 1)
        dev_txt = "Unlimited" if dev_limit >= 999 else f"{dev_limit} Device(s)"
        
        exp = datetime.datetime.fromisoformat(k["expires_at"].replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        if exp > now:
            rem = exp - now
            rem_txt = f"{rem.days}d {rem.seconds // 3600}h"
        else:
            rem_txt = "Expired ❌"

        share_msg = (
            f"🚀 <b>SUIII_CHEATS OFFICIAL</b>\n"
            f"<i>Premium VIP Access</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Product:</b> ShadowTrackerExtra (PUBGM)\n"
            f"🔑 <b>License Key:</b>\n<code>{key}</code>\n\n"
            f"👤 <b>User Details:</b>\n"
            f"├ TG ID: <code>{k.get('telegram_id')}</code>\n"
            f"├ Devices: <code>{dev_txt}</code>\n"
            f"└ HWID: <code>{hwid}</code>\n\n"
            f"⏱ <b>Time Information:</b>\n"
            f"├ Activated: <code>{k.get('created_at', '')[:10]}</code>\n"
            f"├ Expires: <code>{k.get('expires_at', '')[:10]}</code>\n"
            f"└ Remaining: <b>{rem_txt}</b>\n\n"
            f"📡 <b>Status:</b> {status_txt}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📖 <b>INSTALLATION GUIDE:</b>\n"
            f"1. Open File Manager.\n"
            f"2. Go to: <code>Android/data/com.tencent.ig/files/UE4Game/...</code>\n"
            f"3. Create <code>key.txt</code> and paste the key.\n"
            f"4. Restart Game.\n\n"
            f"✅ <b>Safe Usage:</b> Alt account, offline mode.\n"
            f"❌ <b>Not Allowed:</b> Sharing key, main ID use.\n\n"
            f"⚠️ <b>Common Errors:</b>\n"
            f"- <i>Invalid Key:</i> Check for extra spaces.\n"
            f"- <i>HWID Mismatch:</i> Contact admin.\n\n"
            f"💬 <b>Support:</b> @rovixbyultimate\n"
            f"🌐 <b>Channel:</b> https://t.me/rovixbyultimate\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Offline usage only. Online usage may result in ban.</i>"
        )
        await q.message.reply_text(share_msg, parse_mode="HTML", disable_web_page_preview=True)
        await q.answer("Professional format generated!")
        
    elif action == "delete":
        sb.table("license_keys").delete().eq("key_code", key).execute()
        log_action("KEY_DELETED", uid, key, "Key deleted from DB.")
        await q.edit_message_text(f"🗑 Key <code>{key}</code> deleted.", parse_mode="HTML")

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("block", block_user))
    app.add_handler(CommandHandler("unblock", unblock_user))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
