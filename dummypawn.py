import aiohttp
import logging
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode, ChatType
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, CallbackQuery
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from colorama import init, Fore

init(autoreset=True)

# ─── Imports for Dummy HTTP Server ──────────────────────────────────────────
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ─── Configuration ─────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKEN")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "SERPER_API_KEY")
UPDATES_CHANNEL = "https://t.me/WorkGlows"
SUPPORT_GROUP = "https://t.me/TheCryptoElders"
BOT_USERNAME = "DummyPawnBot"

SERPER_URLS = {
    "web": "https://google.serper.dev/search",
    "img": "https://google.serper.dev/images",
    "news": "https://google.serper.dev/news",
    "vid": "https://google.serper.dev/videos"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_info(msg):
    print(f"{Fore.CYAN}ℹ️ INFO: {msg}{Fore.RESET}")
    logging.info(msg)

def log_success(msg):
    print(f"{Fore.GREEN}✅ SUCCESS: {msg}{Fore.RESET}")
    logging.info(msg)

def log_warn(msg):
    print(f"{Fore.YELLOW}⚠️ WARNING: {msg}{Fore.RESET}")
    logging.warning(msg)

def log_error(msg):
    print(f"{Fore.RED}❌ ERROR: {msg}{Fore.RESET}")
    logging.error(msg)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Cache keyed by (user_id, chat_id) - each user has isolated sessions per chat
user_search_cache = {}
# Rate limit keyed by user_id for both private and group chats
rate_limit = {}

def get_inline_keyboard(user_id: int, chat_id: int):
    """
    Generate inline keyboard with callback_data including user_id and chat_id,
    so each user has isolated sessions per chat.
    """
    log_info(f"Generating inline keyboard for user_id={user_id}, chat_id={chat_id}")
    # callback_data format: e.g. "prev_{user_id}_{chat_id}", "next_{user_id}_{chat_id}", "close_{user_id}_{chat_id}"
    prefix_prev = f"prev_{user_id}_{chat_id}"
    prefix_next = f"next_{user_id}_{chat_id}"
    prefix_close = f"close_{user_id}_{chat_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Previous", callback_data=prefix_prev),
            InlineKeyboardButton(text="Next", callback_data=prefix_next)
        ],
        [
            InlineKeyboardButton(text="Close", callback_data=prefix_close)
        ]
    ])

async def query_serper(mode: str, query: str):
    log_info(f"Calling Serper API with mode='{mode}' and query='{query}'")
    url = SERPER_URLS.get(mode)
    if not url:
        log_error(f"Invalid mode: {mode}")
        return {}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    log_error(f"Serper API returned status {resp.status} for query '{query}'")
                    return {}
                data = await resp.json()
                log_success(f"Received data from Serper API for query '{query}'")
                return data
    except Exception as e:
        log_error(f"Exception during Serper API call: {e}")
        return {}

def check_rate_limit(user_id: int) -> bool:
    """
    Check if user has exceeded rate limit (3 searches per minute)
    Returns True if within limit, False if exceeded
    """
    now = datetime.now()
    if user_id not in rate_limit:
        rate_limit[user_id] = []
    
    # Remove old entries (older than 1 minute)
    rate_limit[user_id] = [timestamp for timestamp in rate_limit[user_id] 
                          if now - timestamp < timedelta(minutes=1)]
    
    # Check if user has exceeded limit
    if len(rate_limit[user_id]) >= 3:
        return False
    
    # Add current request
    rate_limit[user_id].append(now)
    return True

async def send_result(msg: types.Message, mode: str, index: int = 0, query_override: str = ""):
    """
    msg: the original message object
    mode: "web", "img", "vid", "news"
    index: result index for pagination
    query_override: if provided, use this string as the search query instead of msg.text
    """
    chat_id = msg.chat.id
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"send_result called for chat_id={chat_id}, user_id={user_id}, mode='{mode}', index={index}")
    
    # Check rate limit
    if not check_rate_limit(user_id):
        await msg.answer("⏰ Rate limit exceeded. You can make 3 searches per minute. Please wait.", 
                        reply_to_message_id=msg.message_id)
        log_warn(f"Rate limit exceeded for user {user_id}")
        return
    
    # Determine the query text:
    if query_override:
        query = query_override.strip()
    else:
        text = msg.text or ""
        # In group, msg.text might be like "dummy naruto image": but for send_result, query_override should strip "dummy"
        # In private or command, msg.text might be "/img naruto"
        # A robust way: if msg.text starts with a slash command, split by space:
        if text.startswith("/"):
            parts = text.split(" ", 1)
            query = parts[1].strip() if len(parts) > 1 else ""
        else:
            # For private smart trigger, text is full, e.g. "naruto image"
            query = text.strip()
    
    if not query or query.lower().strip() == "dummy":
        await msg.answer("😕 Please provide a search query.", reply_to_message_id=msg.message_id)
        log_warn(f"Empty or invalid query from user {user_id} in chat {chat_id}")
        return

    data = await query_serper(mode, query)
    if not data:
        await msg.answer("💔 No data received from API. Please try again later.", reply_to_message_id=msg.message_id)
        log_warn(f"No data received from API for query '{query}' user {user_id} in chat {chat_id}")
        return

    results_key = {
        "web": "organic",
        "img": "images",
        "vid": "videos",
        "news": "news"
    }[mode]

    results = data.get(results_key, [])
    if not results:
        await msg.answer(f"💔 No {mode} results found for '{query}'.", reply_to_message_id=msg.message_id)
        log_warn(f"No {mode} results found for query '{query}' user {user_id} in chat {chat_id}")
        return

    # Cache under (user_id, chat_id) - each user gets isolated sessions per chat
    # Include timestamp to make sessions unique per search
    session_timestamp = datetime.now().strftime("%H%M%S")
    cache_key = (user_id, chat_id)
    user_search_cache[cache_key] = {
        "mode": mode,
        "query": query,
        "data": data,
        "index": index,
        "timestamp": session_timestamp,
        "chat_id": chat_id
    }
    log_info(f"Cached search for user {user_id} in chat {chat_id}, mode '{mode}', query '{query}', total results {len(results)}")

    if index >= len(results):
        await msg.answer("💔 No more results available.", reply_to_message_id=msg.message_id)
        log_warn(f"Index {index} out of range for results, user {user_id} in chat {chat_id}")
        return

    result = results[index]
    keyboard = get_inline_keyboard(user_id, chat_id)

    try:
        if mode == "img":
            # result["imageUrl"], result["title"]
            image_url = result.get("imageUrl", "")
            title = result.get("title", "")
            caption = f"🖼️ <b>{title}</b>\n\n📊 Result {index + 1} of {len(results)}\n🔍 Query: {query}\n👤 Your session: {session_timestamp}"
            await msg.answer_photo(image_url, caption=caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
            log_success(f"Sent image result to user {user_id} in chat {chat_id}")
        else:
            link = result.get("link", "")
            title = result.get("title", "No Title")
            snippet = result.get("snippet") or result.get("description") or "No description available."
            photo_url = result.get("thumbnailUrl") or result.get("imageUrl")
            
            # Emoji mapping for different modes
            mode_emojis = {
                "web": "🌐",
                "news": "📰",
                "vid": "🎥"
            }
            emoji = mode_emojis.get(mode, "🔍")
            
            caption = f'{emoji} <a href="{link}"><b>{title}</b></a>\n\n{snippet}\n\n📊 Result {index + 1} of {len(results)}\n🔍 Query: {query}\n👤 Your session: {session_timestamp}'
            
            if photo_url:
                await msg.answer_photo(photo=photo_url, caption=caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
                log_success(f"Sent photo with caption to user {user_id} in chat {chat_id}")
            else:
                await msg.answer(caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
                log_success(f"Sent text result to user {user_id} in chat {chat_id}")
    except Exception as e:
        log_error(f"Failed to send result message for chat {chat_id}, user {user_id}: {e}")
        await msg.answer("🙁 Failed to send result. Please try again.", reply_to_message_id=msg.message_id)

@router.callback_query(lambda c: c.data and (
    c.data.startswith("next_") or c.data.startswith("prev_") or c.data.startswith("close_")
))
async def callback_handler(query: CallbackQuery):
    """
    Callback data format: "next_{user_id}_{chat_id}", "prev_{user_id}_{chat_id}", "close_{user_id}_{chat_id}"
    """
    data = query.data or ""
    if not query.message or not query.from_user:
        await query.answer("🙁 Invalid callback query.", show_alert=True)
        return
        
    log_info(f"Received callback: {data} from user {query.from_user.id} in chat {query.message.chat.id}")
    parts = data.split("_")
    # Expect ["next", user_id_str, chat_id_str] or ["prev", user_id_str, chat_id_str] or ["close", user_id_str, chat_id_str]
    if len(parts) != 3:
        log_warn(f"Unexpected callback_data format: {data}")
        await query.answer("🙁 Invalid callback data.", show_alert=True)
        return

    action, user_id_str, chat_id_str = parts
    try:
        user_id = int(user_id_str)
        chat_id = int(chat_id_str)
    except ValueError:
        log_warn(f"Non-integer IDs in callback_data: {data}")
        await query.answer("🙁 Invalid callback IDs.", show_alert=True)
        return

    # Verify correct user and chat
    if query.from_user.id != user_id:
        await query.answer("😑 This button isn't for you. Fool!", show_alert=True)
        log_warn(f"User {query.from_user.id} tried to press button for user {user_id}")
        return
    
    if query.message.chat.id != chat_id:
        await query.answer("🙅‍♂️ This button isn't for this chat!", show_alert=True)
        log_warn(f"Callback for chat {chat_id} used in chat {query.message.chat.id}")
        return

    # Handle close
    if action == "close":
        try:
            if hasattr(query.message, 'delete'):
                await query.message.delete()
                await query.answer("❤️ Message deleted")
                log_success(f"Message deleted by user {user_id}")
            else:
                await query.answer("🙁 Cannot delete message.")
        except Exception as e:
            log_error(f"Failed to delete message for user {user_id}: {e}")
            await query.answer("🙁 Failed to delete message.")
        return

    # Retrieve cache for this specific user and chat
    cache_key = (user_id, chat_id)
    cache = user_search_cache.get(cache_key)
    if not cache:
        await query.answer("❗ No cached search found. Please search again.", show_alert=True)
        log_warn(f"No cached search for user {user_id} in chat {chat_id} on callback {data}")
        return

    mode = cache["mode"]
    data_full = cache["data"]
    index = cache["index"]
    results_key = {
        "web": "organic",
        "img": "images",
        "vid": "videos",
        "news": "news"
    }[mode]
    results = data_full.get(results_key, [])

    # Compute new index
    if action == "next":
        new_index = index + 1
        if new_index >= len(results):
            await query.answer("🙌 No more results available buddy.", show_alert=True)
            log_warn(f"User {user_id} reached end of results")
            return
    elif action == "prev":
        new_index = index - 1
        if new_index < 0:
            await query.answer("😖 This is the first result dumbass.", show_alert=True)
            log_warn(f"User {user_id} tried to go before first result")
            return
    else:
        await query.answer()
        return

    # Update cache index for this specific user and chat
    user_search_cache[cache_key]["index"] = new_index
    result = results[new_index]
    keyboard = get_inline_keyboard(user_id, chat_id)

    try:
        if hasattr(query.message, 'edit_media') and hasattr(query.message, 'edit_text'):
            if mode == "img":
                image_url = result.get("imageUrl", "")
                title = result.get("title", "")
                session_info = cache.get("timestamp", "")
                query_info = cache.get("query", "")
                caption = f"🖼️ <b>{title}</b>\n\n📊 Result {new_index + 1} of {len(results)}\n🔍 Query: {query_info}\n👤 Your session: {session_info}"
                try:
                    await query.message.edit_media(
                        types.InputMediaPhoto(media=image_url, caption=caption),
                        reply_markup=keyboard
                    )
                    log_success(f"Edited image media for user {user_id}")
                    await query.answer("❤️ Updated")
                except Exception as edit_e:
                    if "message is not modified" in str(edit_e):
                        await query.answer("❤️ Already showing this result")
                        log_info(f"Duplicate content for user {user_id}, index {new_index}")
                    else:
                        raise edit_e
            else:
                link = result.get("link", "")
                title = result.get("title", "No Title")
                snippet = result.get("snippet") or result.get("description") or "No description available."
                photo_url = result.get("thumbnailUrl") or result.get("imageUrl")
                
                # Emoji mapping for different modes
                mode_emojis = {
                    "web": "🌐",
                    "news": "📰",
                    "vid": "🎥"
                }
                emoji = mode_emojis.get(mode, "🔍")
                
                session_info = cache.get("timestamp", "")
                query_info = cache.get("query", "")
                caption = f'{emoji} <a href="{link}"><b>{title}</b></a>\n\n{snippet}\n\n📊 Result {new_index + 1} of {len(results)}\n🔍 Query: {query_info}\n👤 Your session: {session_info}'
                
                try:
                    if photo_url:
                        await query.message.edit_media(
                            types.InputMediaPhoto(media=photo_url, caption=caption),
                            reply_markup=keyboard
                        )
                        log_success(f"Edited media with photo for user {user_id}")
                    else:
                        await query.message.edit_text(caption, reply_markup=keyboard)
                        log_success(f"Edited text media for user {user_id}")
                    await query.answer("❤️ Updated")
                except Exception as edit_e:
                    if "message is not modified" in str(edit_e):
                        await query.answer("❤️ Already showing this result")
                        log_info(f"Duplicate content for user {user_id}, index {new_index}")
                    else:
                        raise edit_e
        else:
            await query.answer("🤐 Cannot edit this message.")
    except Exception as e:
        log_error(f"Failed to edit message for user {user_id}: {e}")
        await query.answer("🤐 Failed to update message.")

@router.message(Command("start"))
async def cmd_start(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Start command invoked by user {user_id}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Updates", url=UPDATES_CHANNEL),
            InlineKeyboardButton(text="Support", url=SUPPORT_GROUP)
        ],
        [
            InlineKeyboardButton(text="Add Me To Your Group", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")
        ]
    ])
    try:
        await msg.answer(
            f"<b>👋 Welcome to <u>Dummy Pawn</u>!</b>\n\n"
            f"<i>I'm your personal assistant for quick and accurate searches.</i>\n\n"
            f"<b>🔍 Available Commands:</b>\n"
            f"• <code>/web [query]</code> - Web search\n"
            f"• <code>/img [query]</code> - Image search\n"
            f"• <code>/vid [query]</code> - Video search\n"
            f"• <code>/news [query]</code> - News search\n\n"
            f"<b>💡 Smart Features:</b>\n"
            f"• In groups, use 'dummy [query] [type]' (e.g., 'dummy cats image')\n"
            f"• Pagination with Previous/Next buttons\n"
            f"• Rate limiting: 3 searches per minute\n"
            f"• Individual session management per user per chat\n\n"
            f"<b>📱 Get Started:</b>\n"
            f"Try <code>/web python programming</code> or add me to your group!",
            reply_markup=keyboard
        )
        log_success(f"Start message sent to user {user_id}")
    except Exception as e:
        log_error(f"Failed to send start message: {e}")

@router.message(Command("help"))
async def cmd_help(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Help command invoked by user {user_id}")
    help_text = (
        f"<b>🆘 Help - Dummy Pawn Bot</b>\n\n"
        f"<b>🔍 Search Commands:</b>\n"
        f"• <code>/web [query]</code> - Search the web\n"
        f"• <code>/img [query]</code> - Search for images\n"
        f"• <code>/vid [query]</code> - Search for videos\n"
        f"• <code>/news [query]</code> - Search for news\n\n"
        f"<b>🤖 Smart Triggers:</b>\n"
        f"• <b>Private chats:</b> Just type your query + search type\n"
        f"  Example: <code>cats image</code> or <code>python programming</code>\n\n"
        f"• <b>Group chats:</b> Use 'dummy' prefix\n"
        f"  Example: <code>dummy cats image</code> or <code>dummy bitcoin news</code>\n\n"
        f"<b>🎯 Features:</b>\n"
        f"• Navigate results with Previous/Next buttons\n"
        f"• Each user has separate search sessions per chat\n"
        f"• Rate limiting: 3 searches per minute\n"
        f"• Rich media display with thumbnails"
    )
    try:
        await msg.answer(help_text)
        log_success(f"Help message sent to user {user_id}")
    except Exception as e:
        log_error(f"Failed to send help message: {e}")

@router.message(Command("web"))
async def cmd_web(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Web search command from user {user_id}")
    await send_result(msg, "web")

@router.message(Command("img"))
async def cmd_img(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Image search command from user {user_id}")
    await send_result(msg, "img")

@router.message(Command("vid"))
async def cmd_vid(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Video search command from user {user_id}")
    await send_result(msg, "vid")

@router.message(Command("news"))
async def cmd_news(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"News search command from user {user_id}")
    await send_result(msg, "news")

# Smart trigger for groups (responds to "dummy" keyword)
@router.message(lambda msg: msg.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP])
async def handle_group_message(msg: types.Message):
    """Handle smart triggers in group chats"""
    text = (msg.text or "").strip().lower()
    if not text.startswith("dummy "):
        return

    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Smart trigger detected in group {msg.chat.id} by user {user_id}: {text}")

    # Parse: "dummy [query] [type]"
    parts = text.split()
    if len(parts) < 3:
        await msg.answer("❗ Usage: dummy [query] [type]\nExample: dummy cats image", 
                         reply_to_message_id=msg.message_id)
        return

    # Last word is the search type, everything in between is the query
    search_type = parts[-1]
    query = " ".join(parts[1:-1])

    # Map search types
    type_mapping = {
        "web": "web",
        "site": "web",
        "website": "web",
        "link": "web",
        "search": "web",
        "google": "web",

        "image": "img",
        "img": "img",
        "pic": "img",
        "pics": "img",
        "picture": "img",
        "pictures": "img",
        "photo": "img",
        "photos": "img",
        "wallpaper": "img",
        "snapshot": "img",
        "pfp": "img",
        "dp": "img",

        "video": "vid",
        "vid": "vid",
        "clip": "vid",
        "movie": "vid",
        "film": "vid",
        "short": "vid",
        "reel": "vid",
        "scene": "vid",

        "news": "news",
        "headline": "news",
        "headlines": "news",
        "update": "news",
        "updates": "news",
        "report": "news",
        "breaking": "news",
        "alert": "news"
    }

    mode = type_mapping.get(search_type)
    if not mode:
        await msg.answer(
            f"❗ Unknown search type '{search_type}'\n"
            f"Available types: web, image, video, news",
            reply_to_message_id=msg.message_id
        )
        return

    await send_result(msg, mode, query_override=query)


@router.message(lambda msg: msg.chat.type == ChatType.PRIVATE)
async def handle_private_message(msg: types.Message):
    """Handle smart triggers in private chats"""
    text = (msg.text or "").strip().lower()

    # Skip if it's a command
    if text.startswith("/"):
        return

    if not text:
        return

    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Smart trigger detected in private chat by user {user_id}: {text}")

    # Check if message ends with a search type
    parts = text.split()
    if len(parts) < 2:
        # Default to web search
        await send_result(msg, "web", query_override=text)
        return

    # Check if last word is a search type
    last_word = parts[-1]
    type_mapping = {
        "web": "web",
        "site": "web",
        "website": "web",
        "link": "web",
        "search": "web",
        "google": "web",

        "image": "img",
        "img": "img",
        "pic": "img",
        "pics": "img",
        "picture": "img",
        "pictures": "img",
        "photo": "img",
        "photos": "img",
        "wallpaper": "img",
        "snapshot": "img",
        "pfp": "img",
        "dp": "img",

        "video": "vid",
        "vid": "vid",
        "clip": "vid",
        "movie": "vid",
        "film": "vid",
        "short": "vid",
        "reel": "vid",
        "scene": "vid",

        "news": "news",
        "headline": "news",
        "headlines": "news",
        "update": "news",
        "updates": "news",
        "report": "news",
        "breaking": "news",
        "alert": "news"
    }

    mode = type_mapping.get(last_word)
    if mode:
        # Query is everything except the last word
        query = " ".join(parts[:-1])
        await send_result(msg, mode, query_override=query)
    else:
        # Default to web search with full text
        await send_result(msg, "web", query_override=text)

async def set_bot_commands():
    """Set bot commands for the menu"""
    commands = [
        BotCommand(command="start", description="🕹️ Start the bot"),
        BotCommand(command="help", description="💌 Get usage instructions"),
        BotCommand(command="web", description="🌐 Search the web"),
        BotCommand(command="img", description="🏜️ Search for images"),
        BotCommand(command="vid", description="🎬 Search for videos"),
        BotCommand(command="news", description="📰 Search for news"),
    ]
    await bot.set_my_commands(commands)
    log_success("Bot commands set successfully")

# ─── Dummy HTTP Server for Deployment Compatibility ────────────────────────
class DummyHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks and deployment compatibility"""

    def do_GET(self):
        """Handle GET requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Telegram bot is running and healthy!")

    def do_HEAD(self):
        """Handle HEAD requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress HTTP server logs"""
        pass

def start_dummy_server():
    """Start HTTP server for deployment platform compatibility"""
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    print(f"🌐 HTTP server listening on port {port}")
    server.serve_forever()

async def main():
    """Main function to start the bot"""
    log_info("Starting Dummy Pawn Bot...")
    
    try:
        # Set bot commands
        await set_bot_commands()
        
        # Start polling
        log_info("Bot is starting polling...")
        await dp.start_polling(bot)
    except Exception as e:
        log_error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    # Start dummy HTTP server in background thread for deployment compatibility
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    asyncio.run(main())