import aiohttp
import logging
import asyncio
import os
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode, ChatType
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, CallbackQuery
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from colorama import init, Fore

init(autoreset=True)

# Imports for Dummy HTTP Server
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKEN")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "SERPER_API_KEY")
UPDATES_CHANNEL = "https://t.me/WorkGlows"
SUPPORT_GROUP = "https://t.me/SoulMeetsHQ"
BOT_USERNAME = "DummyPawnBot"

# Random Images for Start Command
IMAGES = [
    "https://ik.imagekit.io/asadofc/Images1.png",
    "https://ik.imagekit.io/asadofc/Images2.png",
    "https://ik.imagekit.io/asadofc/Images3.png",
    "https://ik.imagekit.io/asadofc/Images4.png",
    "https://ik.imagekit.io/asadofc/Images5.png",
    "https://ik.imagekit.io/asadofc/Images6.png",
    "https://ik.imagekit.io/asadofc/Images7.png",
    "https://ik.imagekit.io/asadofc/Images8.png",
    "https://ik.imagekit.io/asadofc/Images9.png",
    "https://ik.imagekit.io/asadofc/Images10.png",
    "https://ik.imagekit.io/asadofc/Images11.png",
    "https://ik.imagekit.io/asadofc/Images12.png",
    "https://ik.imagekit.io/asadofc/Images13.png",
    "https://ik.imagekit.io/asadofc/Images14.png",
    "https://ik.imagekit.io/asadofc/Images15.png",
    "https://ik.imagekit.io/asadofc/Images16.png",
    "https://ik.imagekit.io/asadofc/Images17.png",
    "https://ik.imagekit.io/asadofc/Images18.png",
    "https://ik.imagekit.io/asadofc/Images19.png",
    "https://ik.imagekit.io/asadofc/Images20.png",
    "https://ik.imagekit.io/asadofc/Images21.png",
    "https://ik.imagekit.io/asadofc/Images22.png",
    "https://ik.imagekit.io/asadofc/Images23.png",
    "https://ik.imagekit.io/asadofc/Images24.png",
    "https://ik.imagekit.io/asadofc/Images25.png",
    "https://ik.imagekit.io/asadofc/Images26.png",
    "https://ik.imagekit.io/asadofc/Images27.png",
    "https://ik.imagekit.io/asadofc/Images28.png",
    "https://ik.imagekit.io/asadofc/Images29.png",
    "https://ik.imagekit.io/asadofc/Images30.png",
    "https://ik.imagekit.io/asadofc/Images31.png",
    "https://ik.imagekit.io/asadofc/Images32.png",
    "https://ik.imagekit.io/asadofc/Images33.png",
    "https://ik.imagekit.io/asadofc/Images34.png",
    "https://ik.imagekit.io/asadofc/Images35.png",
    "https://ik.imagekit.io/asadofc/Images36.png",
    "https://ik.imagekit.io/asadofc/Images37.png",
    "https://ik.imagekit.io/asadofc/Images38.png",
    "https://ik.imagekit.io/asadofc/Images39.png",
    "https://ik.imagekit.io/asadofc/Images40.png"
]

SERPER_URLS = {
    "web": "https://google.serper.dev/search",
    "img": "https://google.serper.dev/images",
    "news": "https://google.serper.dev/news",
    "vid": "https://google.serper.dev/videos"
}

# Message Dictionaries - Shortened
START_MESSAGES = {
    "welcome": (
        f"<b>👋 Welcome to Dummy Pawn!</b>\n\n"
        f"<i>Your personal search assistant</i>\n\n"
        f"<b>Commands:</b>\n"
        f"• <code>/web [query]</code> - Web search\n"
        f"• <code>/img [query]</code> - Image search\n"
        f"• <code>/vid [query]</code> - Video search\n"
        f"• <code>/news [query]</code> - News search\n\n"
        f"<b>Groups:</b> Use 'dummy [query] [type]'\n"
        f"<b>Private:</b> Just type your query\n\n"
        f"Try: <code>/web python</code> or add me to groups!"
    )
}

HELP_MESSAGES = {
    "basic": (
        f"<b>🆘 Help - Dummy Pawn</b>\n\n"
        f"<b>Quick Commands:</b>\n"
        f"• <code>/web [query]</code> - Web search\n"
        f"• <code>/img [query]</code> - Images\n"
        f"• <code>/vid [query]</code> - Videos\n"
        f"• <code>/news [query]</code> - News\n\n"
        f"<b>Smart Usage:</b>\n"
        f"• <b>Private:</b> <code>cats image</code>\n"
        f"• <b>Groups:</b> <code>dummy cats image</code>\n\n"
        f"<i>Click expand for more details</i>"
    ),
    "expanded": (
        f"<b>🆘 Help - Dummy Pawn</b>\n\n"
        f"<b>All Features:</b>\n"
        f"• Navigate with Previous/Next buttons\n"
        f"• Rate limit: 3 searches per minute\n"
        f"• Individual sessions per chat\n"
        f"• Rich media display\n\n"
        f"<b>Trigger Words:</b>\n"
        f"Web: site, link, search, google\n"
        f"Image: pic, photo, wallpaper, pfp\n"
        f"Video: clip, movie, film, reel\n"
        f"News: headline, update, breaking\n\n"
        f"<i>Click minimize for basic view</i>"
    )
}

# Query Answer Messages
QUERY_ANSWERS = {
    "help_expanded": "📖 Showing detailed help",
    "help_minimized": "📋 Showing basic help",
    "help_updated": "✅ Help updated",
    "help_same": "Already showing this view",
    "help_error": "❌ Failed to update help"
}

# Trigger Words Dictionary for Easy Reference
TRIGGER_WORDS = {
    "web_triggers": ["web", "site", "website", "link", "search", "google"],
    "img_triggers": ["image", "img", "pic", "picture", "photo", "wallpaper", "pfp", "dp"],
    "vid_triggers": ["video", "vid", "clip", "movie", "film", "short", "reel"],
    "news_triggers": ["news", "headline", "update", "report", "breaking", "alert"]
}

ERROR_MESSAGES = {
    "rate_limit": "⏰ Rate limit exceeded. You can make 3 searches per minute. Please wait.",
    "empty_query": "😕 Please provide a search query.",
    "no_data": "💔 No data received from API. Please try again later.",
    "no_results": "💔 No {mode} results found for '{query}'.",
    "no_more_results": "💔 No more results available.",
    "send_failed": "🙁 Failed to send result. Please try again.",
    "invalid_callback": "🙁 Invalid callback query.",
    "invalid_data": "🙁 Invalid callback data.",
    "invalid_ids": "🙁 Invalid callback IDs.",
    "wrong_user": "😑 This button isn't for you. Fool!",
    "wrong_chat": "🙅‍♂️ This button isn't for this chat!",
    "cannot_delete": "🙁 Cannot delete message.",
    "delete_failed": "🙁 Failed to delete message.",
    "no_cache": "❗ No cached search found. Please search again.",
    "no_more": "🙌 No more results available buddy.",
    "first_result": "😖 This is the first result dumbass.",
    "cannot_edit": "🤐 Cannot edit this message.",
    "edit_failed": "🤐 Failed to update message."
}

SUCCESS_MESSAGES = {
    "updated": "❤️ Updated",
    "deleted": "❤️ Message deleted",
    "already_showing": "❤️ Already showing this result"
}

GROUP_MESSAGES = {
    "usage_error": "❗ Usage: dummy [query] [type]\nExample: dummy cats image",
    "unknown_type": "❗ Unknown search type '{search_type}'\nAvailable types: web, image, video, news"
}

BUTTON_TEXTS = {
    "previous": "Previous",
    "next": "Next",
    "close": "Close",
    "updates": "Updates",
    "support": "Support",
    "add_to_group": "Add Me To Your Group",
    "expand": "📖 Expand",
    "minimize": "📋 Minimize"
}

BOT_COMMANDS = [
    {"command": "start", "description": "🕹️ Start the bot"},
    {"command": "help", "description": "💌 Get usage instructions"},
    {"command": "web", "description": "🌐 Search the web"},
    {"command": "img", "description": "🏜️ Search for images"},
    {"command": "vid", "description": "🎬 Search for videos"},
    {"command": "news", "description": "📰 Search for news"}
]

SEARCH_TYPE_MAPPING = {
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

MODE_EMOJIS = {
    "web": "🌐",
    "news": "📰",
    "vid": "🎥",
    "img": "🖼️"
}

RESULTS_KEY_MAPPING = {
    "web": "organic",
    "img": "images",
    "vid": "videos",
    "news": "news"
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

def get_help_keyboard(user_id: int, chat_id: int, is_expanded: bool = False):
    """Generate help keyboard with expand/minimize button"""
    if is_expanded:
        callback_data = f"help_minimize_{user_id}_{chat_id}"
        button_text = BUTTON_TEXTS["minimize"]
    else:
        callback_data = f"help_expand_{user_id}_{chat_id}"
        button_text = BUTTON_TEXTS["expand"]
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=button_text, callback_data=callback_data)
        ]
    ])

def get_inline_keyboard(user_id: int, chat_id: int):
    """Generate inline keyboard with callback_data including user_id and chat_id"""
    log_info(f"Generating inline keyboard for user_id={user_id}, chat_id={chat_id}")
    prefix_prev = f"prev_{user_id}_{chat_id}"
    prefix_next = f"next_{user_id}_{chat_id}"
    prefix_close = f"close_{user_id}_{chat_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_TEXTS["previous"], callback_data=prefix_prev),
            InlineKeyboardButton(text=BUTTON_TEXTS["next"], callback_data=prefix_next)
        ],
        [
            InlineKeyboardButton(text=BUTTON_TEXTS["close"], callback_data=prefix_close)
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
    """Check if user has exceeded rate limit (3 searches per minute)"""
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
    """Send search result with pagination"""
    chat_id = msg.chat.id
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"send_result called for chat_id={chat_id}, user_id={user_id}, mode='{mode}', index={index}")
    
    # Check rate limit
    if not check_rate_limit(user_id):
        await msg.answer(ERROR_MESSAGES["rate_limit"], reply_to_message_id=msg.message_id)
        log_warn(f"Rate limit exceeded for user {user_id}")
        return
    
    # Determine the query text
    if query_override:
        query = query_override.strip()
    else:
        text = msg.text or ""
        if text.startswith("/"):
            parts = text.split(" ", 1)
            query = parts[1].strip() if len(parts) > 1 else ""
        else:
            query = text.strip()
    
    if not query or query.lower().strip() == "dummy":
        await msg.answer(ERROR_MESSAGES["empty_query"], reply_to_message_id=msg.message_id)
        log_warn(f"Empty or invalid query from user {user_id} in chat {chat_id}")
        return

    data = await query_serper(mode, query)
    if not data:
        await msg.answer(ERROR_MESSAGES["no_data"], reply_to_message_id=msg.message_id)
        log_warn(f"No data received from API for query '{query}' user {user_id} in chat {chat_id}")
        return

    results_key = RESULTS_KEY_MAPPING[mode]
    results = data.get(results_key, [])
    if not results:
        await msg.answer(ERROR_MESSAGES["no_results"].format(mode=mode, query=query), reply_to_message_id=msg.message_id)
        log_warn(f"No {mode} results found for query '{query}' user {user_id} in chat {chat_id}")
        return

    # Cache under (user_id, chat_id)
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
        await msg.answer(ERROR_MESSAGES["no_more_results"], reply_to_message_id=msg.message_id)
        log_warn(f"Index {index} out of range for results, user {user_id} in chat {chat_id}")
        return

    result = results[index]
    keyboard = get_inline_keyboard(user_id, chat_id)

    try:
        if mode == "img":
            image_url = result.get("imageUrl", "")
            title = result.get("title", "")
            caption = f"{MODE_EMOJIS['img']} <b>{title}</b>\n\n📊 Result {index + 1} of {len(results)}\n🔍 Query: {query}\n👤 Your session: {session_timestamp}"
            await msg.answer_photo(image_url, caption=caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
            log_success(f"Sent image result to user {user_id} in chat {chat_id}")
        else:
            link = result.get("link", "")
            title = result.get("title", "No Title")
            snippet = result.get("snippet") or result.get("description") or "No description available."
            photo_url = result.get("thumbnailUrl") or result.get("imageUrl")
            
            emoji = MODE_EMOJIS.get(mode, "🔍")
            caption = f'{emoji} <a href="{link}"><b>{title}</b></a>\n\n{snippet}\n\n📊 Result {index + 1} of {len(results)}\n🔍 Query: {query}\n👤 Your session: {session_timestamp}'
            
            if photo_url:
                await msg.answer_photo(photo=photo_url, caption=caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
                log_success(f"Sent photo with caption to user {user_id} in chat {chat_id}")
            else:
                await msg.answer(caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
                log_success(f"Sent text result to user {user_id} in chat {chat_id}")
    except Exception as e:
        log_error(f"Failed to send result message for chat {chat_id}, user {user_id}: {e}")
        await msg.answer(ERROR_MESSAGES["send_failed"], reply_to_message_id=msg.message_id)

@router.callback_query(lambda c: c.data and (
    c.data.startswith("next_") or c.data.startswith("prev_") or c.data.startswith("close_") or
    c.data.startswith("help_expand_") or c.data.startswith("help_minimize_")
))
async def callback_handler(query: CallbackQuery):
    """Handle pagination and help expand/minimize callbacks"""
    data = query.data or ""
    if not query.message or not query.from_user:
        await query.answer(ERROR_MESSAGES["invalid_callback"])
        return
        
    log_info(f"Received callback: {data} from user {query.from_user.id} in chat {query.message.chat.id}")
    
    # Handle help expand/minimize callbacks
    if data.startswith("help_expand_") or data.startswith("help_minimize_"):
        parts = data.split("_")
        if len(parts) != 4:
            await query.answer(ERROR_MESSAGES["invalid_data"])
            return
            
        action, expand_minimize, user_id_str, chat_id_str = parts
        try:
            user_id = int(user_id_str)
            chat_id = int(chat_id_str)
        except ValueError:
            await query.answer(ERROR_MESSAGES["invalid_ids"])
            return
            
        # Verify correct user and chat
        if query.from_user.id != user_id:
            await query.answer(ERROR_MESSAGES["wrong_user"])
            return
        
        if query.message.chat.id != chat_id:
            await query.answer(ERROR_MESSAGES["wrong_chat"])
            return
            
        # Handle expand/minimize
        try:
            if expand_minimize == "expand":
                new_text = HELP_MESSAGES["expanded"]
                new_keyboard = get_help_keyboard(user_id, chat_id, is_expanded=True)
                answer_msg = QUERY_ANSWERS["help_expanded"]
            else:  # minimize
                new_text = HELP_MESSAGES["basic"]
                new_keyboard = get_help_keyboard(user_id, chat_id, is_expanded=False)
                answer_msg = QUERY_ANSWERS["help_minimized"]
                
            await query.message.edit_text(new_text, reply_markup=new_keyboard)
            await query.answer(answer_msg)
            log_success(f"Help {expand_minimize}d for user {user_id}")
            return
            
        except Exception as e:
            if "message is not modified" in str(e):
                await query.answer(QUERY_ANSWERS["help_same"])
            else:
                log_error(f"Failed to update help message: {e}")
                await query.answer(QUERY_ANSWERS["help_error"])
            return
    
    # Handle pagination callbacks (existing code)
    parts = data.split("_")
    if len(parts) != 3:
        log_warn(f"Unexpected callback_data format: {data}")
        await query.answer(ERROR_MESSAGES["invalid_data"])
        return

    action, user_id_str, chat_id_str = parts
    try:
        user_id = int(user_id_str)
        chat_id = int(chat_id_str)
    except ValueError:
        log_warn(f"Non-integer IDs in callback_data: {data}")
        await query.answer(ERROR_MESSAGES["invalid_ids"])
        return

    # Verify correct user and chat
    if query.from_user.id != user_id:
        await query.answer(ERROR_MESSAGES["wrong_user"])
        log_warn(f"User {query.from_user.id} tried to press button for user {user_id}")
        return
    
    if query.message.chat.id != chat_id:
        await query.answer(ERROR_MESSAGES["wrong_chat"])
        log_warn(f"Callback for chat {chat_id} used in chat {query.message.chat.id}")
        return

    # Handle close
    if action == "close":
        try:
            if hasattr(query.message, 'delete'):
                await query.message.delete()
                await query.answer(SUCCESS_MESSAGES["deleted"])
                log_success(f"Message deleted by user {user_id}")
            else:
                await query.answer(ERROR_MESSAGES["cannot_delete"])
        except Exception as e:
            log_error(f"Failed to delete message for user {user_id}: {e}")
            await query.answer(ERROR_MESSAGES["delete_failed"])
        return

    # Retrieve cache for this specific user and chat
    cache_key = (user_id, chat_id)
    cache = user_search_cache.get(cache_key)
    if not cache:
        await query.answer(ERROR_MESSAGES["no_cache"])
        log_warn(f"No cached search for user {user_id} in chat {chat_id} on callback {data}")
        return

    mode = cache["mode"]
    data_full = cache["data"]
    index = cache["index"]
    results_key = RESULTS_KEY_MAPPING[mode]
    results = data_full.get(results_key, [])

    # Compute new index
    if action == "next":
        new_index = index + 1
        if new_index >= len(results):
            await query.answer(ERROR_MESSAGES["no_more"])
            log_warn(f"User {user_id} reached end of results")
            return
    elif action == "prev":
        new_index = index - 1
        if new_index < 0:
            await query.answer(ERROR_MESSAGES["first_result"])
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
                caption = f"{MODE_EMOJIS['img']} <b>{title}</b>\n\n📊 Result {new_index + 1} of {len(results)}\n🔍 Query: {query_info}\n👤 Your session: {session_info}"
                try:
                    await query.message.edit_media(
                        types.InputMediaPhoto(media=image_url, caption=caption),
                        reply_markup=keyboard
                    )
                    log_success(f"Edited image media for user {user_id}")
                    await query.answer(SUCCESS_MESSAGES["updated"])
                except Exception as edit_e:
                    if "message is not modified" in str(edit_e):
                        await query.answer(SUCCESS_MESSAGES["already_showing"])
                        log_info(f"Duplicate content for user {user_id}, index {new_index}")
                    else:
                        raise edit_e
            else:
                link = result.get("link", "")
                title = result.get("title", "No Title")
                snippet = result.get("snippet") or result.get("description") or "No description available."
                photo_url = result.get("thumbnailUrl") or result.get("imageUrl")
                
                emoji = MODE_EMOJIS.get(mode, "🔍")
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
                    await query.answer(SUCCESS_MESSAGES["updated"])
                except Exception as edit_e:
                    if "message is not modified" in str(edit_e):
                        await query.answer(SUCCESS_MESSAGES["already_showing"])
                        log_info(f"Duplicate content for user {user_id}, index {new_index}")
                    else:
                        raise edit_e
        else:
            await query.answer(ERROR_MESSAGES["cannot_edit"])
    except Exception as e:
        log_error(f"Failed to edit message for user {user_id}: {e}")
        await query.answer(ERROR_MESSAGES["edit_failed"])

@router.message(Command("start"))
async def cmd_start(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Start command invoked by user {user_id}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTON_TEXTS["updates"], url=UPDATES_CHANNEL),
            InlineKeyboardButton(text=BUTTON_TEXTS["support"], url=SUPPORT_GROUP)
        ],
        [
            InlineKeyboardButton(text=BUTTON_TEXTS["add_to_group"], url=f"https://t.me/{BOT_USERNAME}?startgroup=true")
        ]
    ])
    
    # Select random image from the list
    random_image = random.choice(IMAGES)
    
    try:
        await msg.answer_photo(
            photo=random_image,
            caption=START_MESSAGES["welcome"], 
            reply_markup=keyboard
        )
        log_success(f"Start message with random image sent to user {user_id}")
    except Exception as e:
        log_error(f"Failed to send start message with image: {e}")
        # Fallback to text message if image fails
        try:
            await msg.answer(START_MESSAGES["welcome"], reply_markup=keyboard)
            log_success(f"Start message (text fallback) sent to user {user_id}")
        except Exception as e2:
            log_error(f"Failed to send start message fallback: {e2}")

@router.message(Command("help"))
async def cmd_help(msg: types.Message):
    user_id = msg.from_user.id if msg.from_user else 0
    chat_id = msg.chat.id
    log_info(f"Help command invoked by user {user_id}")
    
    keyboard = get_help_keyboard(user_id, chat_id, is_expanded=False)
    
    try:
        await msg.answer(HELP_MESSAGES["basic"], reply_markup=keyboard)
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
    
@router.message(Command("ping"))
async def cmd_ping(msg: types.Message):
    """Handle /ping command - shows latency with hyperlinked Pong!"""
    user_id = msg.from_user.id if msg.from_user else 0
    log_info(f"Ping command from user {user_id}")
    
    try:
        # Record start time
        start_time = datetime.now()
        
        # Send initial "Pinging..." message
        ping_msg = await msg.answer("🛰️ Pinging...", reply_to_message_id=msg.message_id)
        
        # Calculate response time
        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds() * 1000
        
        # Edit the message to show Pong! with hyperlink
        pong_text = f'🏓 <a href="{SUPPORT_GROUP}">Pong!</a> {latency:.2f}ms'
        
        await ping_msg.edit_text(
            pong_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        
        log_success(f"Ping response sent to user {user_id} with latency {latency:.2f}ms")
        
    except Exception as e:
        log_error(f"Failed to send ping response to user {user_id}: {e}")
        # Fallback response if edit fails
        try:
            await msg.answer(f"🏓 Pong! Error measuring latency", reply_to_message_id=msg.message_id)
        except Exception as e2:
            log_error(f"Failed to send ping fallback to user {user_id}: {e2}")

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
        await msg.answer(GROUP_MESSAGES["usage_error"], reply_to_message_id=msg.message_id)
        return

    # Last word is the search type, everything in between is the query
    search_type = parts[-1]
    query = " ".join(parts[1:-1])

    mode = SEARCH_TYPE_MAPPING.get(search_type)
    if not mode:
        await msg.answer(
            GROUP_MESSAGES["unknown_type"].format(search_type=search_type),
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
    mode = SEARCH_TYPE_MAPPING.get(last_word)
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
        BotCommand(command=cmd["command"], description=cmd["description"])
        for cmd in BOT_COMMANDS
    ]
    await bot.set_my_commands(commands)
    log_success("Bot commands set successfully")

# Dummy HTTP Server for Deployment Compatibility
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