import os
import json
import logging
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from telegram import (
    Update,
    InputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from PIL import Image, ImageDraw, ImageFont
import cv2

load_dotenv()

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", 10000))

# Owner User ID (number). Change this to your Telegram user id.
# You can also set OWNER_ID in Render Environment Variables.
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))   # <-- yahan apni real User ID daalna
DEFAULT_USERNAME = "The_Sk08"
OWNER_USERNAME = "SunilChoudhary08"   # sirf message me dikhane ke liye

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "telegram_logo.png"
FONT_PATH = ASSETS_DIR / "AlegreyaSans-Bold.ttf"
AUTH_FILE = BASE_DIR / "authorized.json"

# ==================== LOGGING ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("SK-ThumbBot")

# ==================== AUTH SYSTEM ====================
def load_authorized() -> set:
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text())
            return set(data.get("user_ids", []))
        except Exception:
            return set()
    return set()

def save_authorized(user_ids: set) -> None:
    AUTH_FILE.write_text(json.dumps({"user_ids": list(user_ids)}, indent=2))

authorized_users: set = load_authorized()
user_custom_names: dict = {}

def is_owner(user) -> bool:
    if not user:
        return False
    return user.id == OWNER_ID

def is_authorized(user) -> bool:
    if not user:
        return False
    if is_owner(user):
        return True
    return user.id in authorized_users

def require_auth(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not is_authorized(user):
            text = (
                "🚫 *Access Denied*\n\n"
                "Aap authorized nahi ho.\n"
                "Sirf Owner aur authorized users hi is bot ko use kar sakte hain.\n\n"
                f"Owner: @{OWNER_USERNAME}"
            )
            if update.callback_query:
                await update.callback_query.answer("Not Authorized", show_alert=True)
                try:
                    await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    pass
            else:
                await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return
        return await func(update, context)
    return wrapper

# ==================== THUMBNAIL ENGINE ====================
def create_stylish_thumbnail(frame_path: str, username: str, output_path: str) -> str:
    """Top black bar + Telegram logo + @username (like original @THEKMX style)"""
    im = Image.open(frame_path).convert("RGB")
    width, height = im.size

    # Keep reasonable size
    max_w = 720
    if width > max_w:
        ratio = max_w / width
        im = im.resize((max_w, int(height * ratio)), Image.LANCZOS)
        width, height = im.size

    draw = ImageDraw.Draw(im)

    # ===== TOP BLACK BAR (same style as original watermark area) =====
    cover_h = max(int(height * 0.18), 55)
    draw.rectangle([0, 0, width, cover_h], fill=(0, 0, 0))

    # Logo (small)
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo_size = int(cover_h * 0.62)
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # Font
    font_size = max(int(cover_h * 0.42), 20)
    try:
        font = ImageFont.truetype(str(FONT_PATH), size=font_size)
    except Exception:
        font = ImageFont.load_default()

    text = f"@{username.lstrip('@').strip()}"
    if not text or text == "@":
        text = f"@{DEFAULT_USERNAME}"

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Center logo + text on the top bar
    total_w = logo_size + 12 + text_w
    start_x = max((width - total_w) // 2, 8)
    y_logo = (cover_h - logo_size) // 2

    im.paste(logo, (start_x, y_logo), logo)

    text_x = start_x + logo_size + 12
    text_y = (cover_h - text_h) // 2 - 2

    # Outline
    outline = 3
    for dx in range(-outline, outline + 1):
        for dy in range(-outline, outline + 1):
            if dx * dx + dy * dy <= outline * outline + 2:
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=(0, 0, 0))

    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

    im.save(output_path, "JPEG", quality=90, optimize=True)
    return output_path




def extract_frame_from_video(video_path: str, output_image: str) -> bool:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False
    for _ in range(8):
        ret, frame = cap.read()
        if ret and frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            Image.fromarray(frame_rgb).save(output_image, "JPEG", quality=92)
            cap.release()
            return True
    cap.release()
    return False


# ==================== KEYBOARDS ====================
def main_menu_keyboard(user) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("✏️ Set Name", callback_data="setname_help"),
            InlineKeyboardButton("👤 My Name", callback_data="myname"),
        ],
        [
            InlineKeyboardButton("🎬 How to Use", callback_data="howto"),
            InlineKeyboardButton("📖 Help & Commands", callback_data="help"),
        ],
    ]
    if is_owner(user):
        buttons.append([
            InlineKeyboardButton("👑 Owner Panel", callback_data="owner_panel"),
        ])
    return InlineKeyboardMarkup(buttons)


def owner_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Authorize User", callback_data="auth_help"),
            InlineKeyboardButton("➖ Remove User", callback_data="unauth_help"),
        ],
        [InlineKeyboardButton("📋 List Authorized", callback_data="listauth")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")],
    ])


def back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])


# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user):
        await update.message.reply_text(
            "🚫 *Access Denied*\n\n"
            "Aap is bot ko use nahi kar sakte.\n"
            f"Sirf Owner (@{OWNER_USERNAME}) aur unke authorized users hi allowed hain.\n\n"
            "Agar access chahiye to Owner se contact karo.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if is_owner(user) and user.id not in authorized_users:
        authorized_users.add(user.id)
        save_authorized(authorized_users)

    name = user_custom_names.get(user.id, DEFAULT_USERNAME)

    text = (
        f"✨ *SK Thumbnail Changer*\n"
        f"────────────────────\n"
        f"Namaste *{user.first_name}*!\n\n"
        f"Ye bot aapke video ke thumbnail me\n"
        f"stylish text + Telegram logo lagata hai.\n\n"
        f"🎯 *Current Name:* `@{name}`\n\n"
        f"Neeche se button dabao ya command use karo."
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_authorized(user):
        await update.effective_message.reply_text("🚫 Not Authorized.")
        return

    text = (
        "📖 *SK Thumbnail Changer — Commands*\n"
        "────────────────────────────\n\n"
        "*🔹 For All Authorized Users:*\n"
        "`/start` — Bot start + main menu\n"
        "`/help` — Ye help message\n"
        "`/setname <name>` — Apna stylish naam set karo\n"
        "     Example: `/setname The_Sk08`\n"
        "`/myname` — Abhi ka set naam dekho\n"
        "`/cancel` — Current action cancel\n\n"
        "*👑 Owner Only Commands:*\n"
        "`/authorize <user_id>` — User ko allow karo\n"
        "`/unauthorize <user_id>` — Access hatao\n"
        "`/listauth` — Authorized users ki list\n\n"
        "*📌 Video kaise process karein:*\n"
        "1. Pehle `/setname` se naam set karo\n"
        "2. Phir koi bhi video bhej do\n"
        "3. Bot automatically naya thumbnail laga dega\n\n"
        "⚡ Badi videos (100MB+) bhi support (file_id method)\n"
        "Default naam: `@The_Sk08`"
    )
    kb = back_menu_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


@require_auth
async def setname_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "✏️ *Naam set karne ke liye:*\n"
            "`/setname YourName`\n\n"
            "Example:\n`/setname The_Sk08`\n`/setname SPARK`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_menu_keyboard(),
        )
        return

    name = " ".join(context.args).strip().lstrip("@")
    if len(name) < 2 or len(name) > 28:
        await update.message.reply_text("Naam 2 se 28 characters ke beech hona chahiye.")
        return

    user_custom_names[update.effective_user.id] = name
    await update.message.reply_text(
        f"✅ Naam set ho gaya!\n\n🎯 Ab se thumbnail me ye dikhega:\n`@{name}`\n\n"
        "Ab koi bhi video bhej do.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Video Bhejo", callback_data="send_video_hint")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
        ]),
    )


@require_auth
async def myname_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = user_custom_names.get(update.effective_user.id, DEFAULT_USERNAME)
    await update.message.reply_text(
        f"👤 *Aapka current naam:*\n`@{name}`\n\n"
        "Change karna ho to `/setname NayaNaam`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_menu_keyboard(),
    )


async def authorize_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user):
        await update.message.reply_text("🚫 Sirf Owner ye command use kar sakta hai.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n`/authorize <user_id>`\n\n"
            "User ID kaise pata kare:\n"
            "• User se bolo bot ko `/start` kare\n"
            "• Ya @userinfobot se ID le lo",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user_id. Number hona chahiye.")
        return

    authorized_users.add(uid)
    save_authorized(authorized_users)
    await update.message.reply_text(f"✅ User `{uid}` ab authorized hai.", parse_mode=ParseMode.MARKDOWN)


async def unauthorize_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user):
        await update.message.reply_text("🚫 Sirf Owner ye command use kar sakta hai.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/unauthorize <user_id>`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user_id.")
        return

    if uid in authorized_users:
        authorized_users.discard(uid)
        save_authorized(authorized_users)
        await update.message.reply_text(f"✅ User `{uid}` ka access hata diya.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Ye user authorized list me nahi tha.")


async def listauth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user):
        await update.message.reply_text("🚫 Sirf Owner ye command use kar sakta hai.")
        return

    if not authorized_users:
        text = "Abhi koi extra authorized user nahi hai.\n(Owner hamesha allowed hai)"
    else:
        lines = [f"• `{uid}`" for uid in sorted(authorized_users)]
        text = "📋 *Authorized Users:*\n" + "\n".join(lines)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@require_auth
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    username = user_custom_names.get(user.id, DEFAULT_USERNAME)

    message = update.message
    video = message.video
    if not video and message.document and message.document.mime_type and "video" in message.document.mime_type:
        video = message.document

    if not video:
        await message.reply_text("Video nahi mili.")
        return

    status = await message.reply_text("⏳ Stylish thumbnail bana raha hoon...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            frame_path = os.path.join(tmpdir, "frame.jpg")
            thumb_path = os.path.join(tmpdir, "thumb.jpg")
            got_frame = False

            # Method 1: existing thumbnail (works for ANY size including 2GB)
            thumb_obj = getattr(video, "thumbnail", None)
            if thumb_obj:
                try:
                    thumb_file = await context.bot.get_file(thumb_obj.file_id)
                    await thumb_file.download_to_drive(frame_path)
                    got_frame = True
                    logger.info("Used existing video.thumbnail")
                except Exception as e:
                    logger.warning(f"video.thumbnail failed: {e}")

            # Method 2: small video → extract real frame
            if not got_frame:
                file_size = getattr(video, "file_size", 0) or 0
                if 0 < file_size < 18 * 1024 * 1024:
                    try:
                        tg_file = await context.bot.get_file(video.file_id)
                        video_path = os.path.join(tmpdir, "input.mp4")
                        await tg_file.download_to_drive(video_path)
                        if extract_frame_from_video(video_path, frame_path):
                            got_frame = True
                            logger.info("Extracted frame from small video")
                    except Exception as e:
                        logger.warning(f"Frame extract failed: {e}")

            if not got_frame:
                await status.edit_text(
                    "❌ Thumbnail nahi bana paya.\n"
                    "Video me ready thumbnail nahi hai aur file bhi badi hai.\n"
                    "Video ko Telegram me ek baar forward/compress karke dubara bhejo."
                )
                return

            create_stylish_thumbnail(frame_path, username, thumb_path)

            thumb_size = os.path.getsize(thumb_path)
            logger.info(f"New thumbnail created: {thumb_size} bytes")

            # Only send the new thumbnail IMAGE (not the video)
            with open(thumb_path, "rb") as thumb_f:
                await message.reply_photo(
                    photo=InputFile(thumb_f, filename="sk_thumb.jpg"),
                    caption=f"✅ New Thumbnail Ready\n👤 `@{username}`",
                    parse_mode=ParseMode.MARKDOWN,
                )

            await status.delete()

    except Exception as e:
        logger.exception("Video process error")
        await status.edit_text(f"❌ Error: `{str(e)[:180]}`", parse_mode=ParseMode.MARKDOWN)


# ==================== CALLBACKS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if not is_authorized(user) and data not in ("main_menu",):
        await query.message.reply_text("🚫 Not Authorized.")
        return

    if data == "main_menu":
        name = user_custom_names.get(user.id, DEFAULT_USERNAME)
        text = (
            f"✨ *SK Thumbnail Changer*\n"
            f"────────────────────\n"
            f"Current Name: `@{name}`\n\n"
            f"Button se choose karo:"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard(user))

    elif data == "help":
        await help_command(update, context)

    elif data == "myname":
        name = user_custom_names.get(user.id, DEFAULT_USERNAME)
        await query.edit_message_text(
            f"👤 *Aapka current naam:*\n`@{name}`\n\nChange karna ho to `/setname NayaNaam` likho.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_menu_keyboard(),
        )

    elif data == "setname_help":
        await query.edit_message_text(
            "✏️ *Naam kaise set karein:*\n\n"
            "Command bhejo:\n`/setname The_Sk08`\n\n"
            "Ya koi bhi naam:\n`/setname SPARK_XD`\n\n"
            "Set hone ke baad video bhej dena.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_menu_keyboard(),
        )

    elif data == "howto":
        await query.edit_message_text(
            "🎬 *Kaise Use Karein (Simple)*\n\n"
            "1️⃣ `/setname ApnaNaam` bhejo\n"
            "2️⃣ Koi bhi video bot ko bhej do\n"
            "3️⃣ Bot 1-2 second me naya stylish thumbnail laga ke wapas bhej dega\n\n"
            "✅ 20MB se leke 2GB tak sab size support\n"
            "✅ Default naam: `@The_Sk08`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_menu_keyboard(),
        )

    elif data == "send_video_hint":
        await query.edit_message_text(
            "📤 Ab seedha koi bhi video is chat me bhej do.\n\nBot automatically process kar lega!",
            reply_markup=back_menu_keyboard(),
        )

    elif data == "owner_panel":
        if not is_owner(user):
            await query.answer("Only Owner", show_alert=True)
            return
        await query.edit_message_text(
            "👑 *Owner Panel*\n\nYahan se users ko authorize / remove kar sakte ho.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_panel_keyboard(),
        )

    elif data == "auth_help":
        if not is_owner(user):
            return
        await query.edit_message_text(
            "➕ *User Authorize karne ke liye:*\n\n"
            "`/authorize 123456789`\n\n"
            "User ID kaise mile:\n• User ko bolo bot pe `/start` kare\n• Ya @userinfobot use karo",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="owner_panel")]]),
        )

    elif data == "unauth_help":
        if not is_owner(user):
            return
        await query.edit_message_text(
            "➖ *Access hatane ke liye:*\n\n`/unauthorize 123456789`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="owner_panel")]]),
        )

    elif data == "listauth":
        if not is_owner(user):
            return
        if not authorized_users:
            text = "Abhi koi extra authorized user nahi.\n(Owner hamesha allowed hai)"
        else:
            lines = [f"• `{uid}`" for uid in sorted(authorized_users)]
            text = "📋 *Authorized Users:*\n" + "\n".join(lines)
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="owner_panel")]]),
        )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())


# ==================== FASTAPI + WEBHOOK ====================
app = FastAPI(title="SK Thumbnail Changer")
application: Optional[Application] = None


@app.on_event("startup")
async def on_startup():
    global application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .updater(None)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setname", setname_cmd))
    application.add_handler(CommandHandler("myname", myname_cmd))
    application.add_handler(CommandHandler("authorize", authorize_cmd))
    application.add_handler(CommandHandler("unauthorize", unauthorize_cmd))
    application.add_handler(CommandHandler("listauth", listauth_cmd))
    application.add_handler(CommandHandler("cancel", cancel_cmd))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    application.add_handler(CallbackQueryHandler(button_handler))

    await application.initialize()
    await application.start()

    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        await application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
        logger.info(f"Webhook set → {webhook_url}")
    else:
        logger.warning("WEBHOOK_URL not set. Set it after deploy.")


@app.on_event("shutdown")
async def on_shutdown():
    if application:
        await application.stop()
        await application.shutdown()


@app.post("/webhook")
async def webhook(request: Request):
    if application is None:
        return Response(status_code=503)
    data = await request.json()
    update = Update.de_json(data=data, bot=application.bot)
    await application.process_update(update)
    return Response(status_code=200)


@app.get("/")
async def root():
    return {
        "bot": "SK Thumbnail Changer",
        "status": "running",
        "owner_id": OWNER_ID,
        "owner": f"@{OWNER_USERNAME}",
        "default_name": f"@{DEFAULT_USERNAME}",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
