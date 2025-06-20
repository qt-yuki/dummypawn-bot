import aiohttp
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command, ChatTypeFilter
from aiogram.client.default import DefaultBotProperties
from colorama import init, Fore

init(autoreset=True)

# ─── Configuration ─────────────────────────────

import os  
from dotenv import load_dotenv  
  
# Load .env  
load_dotenv()  
  
# Config from .env  
BOT_TOKEN = os.getenv("BOT_TOKEN")  
SERPER_API_KEY = os.getenv("SERPER_API_KEY")  
UPDATES_CHANNEL = os.getenv("UPDATES_CHANNEL")  
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP")  
BOT_USERNAME = os.getenv("BOT_USERNAME")

SERPER_URLS = {
    "web": "https://google.serper.dev/search",
    "img": "https://google.serper.dev/images",
    "news": "https://google.serper.dev/news",
    "vid": "https://google.serper.dev/videos"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_info(msg): print(f"{Fore.CYAN}ℹ️ INFO: {msg}{Fore.RESET}"); logging.info(msg)
def log_success(msg): print(f"{Fore.GREEN}✅ SUCCESS: {msg}{Fore.RESET}"); logging.info(msg)
def log_warn(msg): print(f"{Fore.YELLOW}⚠️ WARNING: {msg}{Fore.RESET}"); logging.warning(msg)
def log_error(msg): print(f"{Fore.RED}❌ ERROR: {msg}{Fore.RESET}"); logging.error(msg)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

user_search_cache = {}
group_rate_limit = {}

def get_inline_keyboard(user_id: int):
    log_info(f"Generating inline keyboard for user_id={user_id}")
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Previous ◀️", callback_data=f"prev_{user_id}"),
            InlineKeyboardButton(text="Next ▶️", callback_data=f"next_{user_id}")
        ],
        [
            InlineKeyboardButton(text="Close ❌", callback_data=f"close_{user_id}")
        ]
    ])

async def query_serper(mode: str, query: str):
    log_info(f"Calling Serper API with mode='{mode}' and query='{query}'")
    url = SERPER_URLS.get(mode)
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

async def send_result(msg: types.Message, mode: str, index: int = 0):
    log_info(f"send_result called with mode='{mode}', index={index} for user {msg.from_user.id}")
    query = msg.text.split(" ", 1)[-1] if " " in msg.text else ""
    if not query or query.lower().strip() == "dummy":
        await msg.answer("❗ Please provide a search query.", reply_to_message_id=msg.message_id)
        log_warn(f"Empty or invalid query from user {msg.from_user.id}")
        return

    data = await query_serper(mode, query)
    if not data:
        await msg.answer("No data received from API.", reply_to_message_id=msg.message_id)
        log_warn(f"No data received from API for query '{query}' user {msg.from_user.id}")
        return

    results_key = {
        "web": "organic",
        "img": "images",
        "vid": "videos",
        "news": "news"
    }[mode]

    results = data.get(results_key, [])
    if not results:
        await msg.answer(f"No {mode} results found.", reply_to_message_id=msg.message_id)
        log_warn(f"No {mode} results found for query '{query}' user {msg.from_user.id}")
        return

    user_search_cache[msg.from_user.id] = {
        "mode": mode,
        "query": query,
        "data": data,
        "index": index
    }
    log_info(f"Cached search for user {msg.from_user.id} with mode '{mode}', query '{query}', total results {len(results)}")

    if index >= len(results):
        await msg.answer("No more results available.", reply_to_message_id=msg.message_id)
        log_warn(f"Index {index} out of range for results, user {msg.from_user.id}")
        return

    result = results[index]
    keyboard = get_inline_keyboard(msg.from_user.id)

    try:
        if mode == "img":
            await msg.answer_photo(result["imageUrl"], caption=result["title"], reply_markup=keyboard, reply_to_message_id=msg.message_id)
            log_success(f"Sent image result to user {msg.from_user.id}")
        else:
            link = result.get("link", "")
            title = result.get("title", "No Title")
            snippet = result.get("snippet") or result.get("description") or "No description available."
            photo_url = result.get("thumbnailUrl") or result.get("imageUrl")
            caption = f'<a href="{link}"><b>{title}</b></a>\n\n{snippet}'

            if photo_url:
                await msg.answer_photo(photo=photo_url, caption=caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
                log_success(f"Sent photo with caption to user {msg.from_user.id}")
            else:
                await msg.answer(caption, reply_markup=keyboard, reply_to_message_id=msg.message_id)
                log_success(f"Sent text result to user {msg.from_user.id}")
    except Exception as e:
        log_error(f"Failed to send result message: {e}")

# CALLBACK HANDLER
@router.callback_query(lambda c: c.data and (c.data.startswith("next_") or c.data.startswith("prev_") or c.data.startswith("close_")))
async def callback_handler(query: CallbackQuery):
    log_info(f"Received callback: {query.data} from user {query.from_user.id}")
    user_id = int(query.data.split("_")[1])

    if query.from_user.id != user_id:
        await query.answer("This button isn't for you!", show_alert=True)
        log_warn(f"User {query.from_user.id} tried to press button for user {user_id}")
        return

    if query.data.startswith("close_"):
        try:
            await query.message.delete()
            await query.answer()
            log_success(f"Message deleted by user {user_id}")
        except Exception as e:
            log_error(f"Failed to delete message: {e}")
            await query.answer("Failed to delete message.")
        return

    cache = user_search_cache.get(user_id)
    if not cache:
        await query.answer("❗ No cached search found. Please search again.")
        log_warn(f"No cached search for user {user_id} on callback {query.data}")
        return

    mode = cache["mode"]
    data = cache["data"]
    index = cache["index"]
    results_key = {
        "web": "organic",
        "img": "images",
        "vid": "videos",
        "news": "news"
    }[mode]
    results = data.get(results_key, [])

    if query.data.startswith("next_"):
        new_index = index + 1
        if new_index >= len(results):
            await query.answer("No more results available.", show_alert=True)
            log_warn(f"User {user_id} reached end of results")
            return
    elif query.data.startswith("prev_"):
        new_index = index - 1
        if new_index < 0:
            await query.answer("This is the first result.", show_alert=True)
            log_warn(f"User {user_id} tried to go before first result")
            return
    else:
        await query.answer()
        return

    user_search_cache[user_id]["index"] = new_index
    result = results[new_index]
    keyboard = get_inline_keyboard(user_id)

    try:
        if mode == "img":
            await query.message.edit_media(
                InputMediaPhoto(media=result["imageUrl"], caption=result["title"]),
                reply_markup=keyboard
            )
            log_success(f"Edited image media for user {user_id}")
        else:
            link = result.get("link", "")
            title = result.get("title", "No Title")
            snippet = result.get("snippet") or result.get("description") or "No description available."
            photo_url = result.get("thumbnailUrl") or result.get("imageUrl")
            caption = f'<a href="{link}"><b>{title}</b></a>\n\n{snippet}'

            if photo_url:
                await query.message.edit_media(
                    InputMediaPhoto(media=photo_url, caption=caption),
                    reply_markup=keyboard
                )
                log_success(f"Edited media with photo for user {user_id}")
            else:
                await query.message.edit_text(caption, reply_markup=keyboard)
                log_success(f"Edited text media for user {user_id}")

        await query.answer()
    except Exception as e:
        log_error(f"Failed to edit message: {e}")
        await query.answer("Failed to update message.")
        
# /start command
@router.message(Command("start"))
async def cmd_start(msg: types.Message):
    log_info(f"Start command invoked by user {msg.from_user.id}")
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
            "<b>Welcome to Smart Search Bot!</b>\n\n"
            "Search the web, images, videos, and news via Serper.dev.\n\n"
            "Use /help to view all commands.",
            reply_markup=keyboard,
            reply_to_message_id=msg.message_id
        )
        log_success(f"Sent welcome message to user {msg.from_user.id}")
    except Exception as e:
        log_error(f"Failed to send welcome message: {e}")

# /help command
@router.message(Command("help"))
async def cmd_help(msg: types.Message):
    log_info(f"Help command invoked by user {msg.from_user.id}")
    try:
        await msg.answer(
            "<b>Commands:</b>\n"
            "/web [query] - Web search\n"
            "/img [query] - Image search\n"
            "/vid [query] - Video search\n"
            "/news [query] - News search",
            reply_to_message_id=msg.message_id
        )
        log_success(f"Sent help message to user {msg.from_user.id}")
    except Exception as e:
        log_error(f"Failed to send help message: {e}")

# /web command
@router.message(Command("web"))
async def web_cmd(msg: types.Message):
    log_info(f"/web command invoked by user {msg.from_user.id}")
    try:
        await send_result(msg, "web")
    except Exception as e:
        log_error(f"Error in /web command: {e}")

# /img command
@router.message(Command("img"))
async def img_cmd(msg: types.Message):
    log_info(f"/img command invoked by user {msg.from_user.id}")
    try:
        await send_result(msg, "img")
    except Exception as e:
        log_error(f"Error in /img command: {e}")

# /vid command
@router.message(Command("vid"))
async def vid_cmd(msg: types.Message):
    log_info(f"/vid command invoked by user {msg.from_user.id}")
    try:
        await send_result(msg, "vid")
    except Exception as e:
        log_error(f"Error in /vid command: {e}")

# /news command
@router.message(Command("news"))
async def news_cmd(msg: types.Message):
    log_info(f"/news command invoked by user {msg.from_user.id}")
    try:
        await send_result(msg, "news")
    except Exception as e:
        log_error(f"Error in /news command: {e}")

# Group dummy trigger
@router.message(ChatTypeFilter(chat_type=["group", "supergroup"]))
async def dummy_keyword_trigger(msg: types.Message):
    try:
        text = (msg.text or "").lower()
        if "dummy" not in text:
            return

        now = datetime.utcnow()
        last_used = group_rate_limit.get(msg.chat.id)
        if last_used and now - last_used < timedelta(minutes=1):
            seconds_left = 60 - int((now - last_used).total_seconds())
            await msg.reply(f"⚠️ Please wait {seconds_left} seconds before making another request.")
            log_warn(f"Rate limit hit in chat {msg.chat.id}, user {msg.from_user.id}")
            return

        group_rate_limit[msg.chat.id] = now
        log_info(f"Rate limit timestamp updated for chat {msg.chat.id}")

        if text.strip() == "dummy":
            await msg.reply("❓ Tell me what you want.")
            log_info(f"User {msg.from_user.id} sent only 'dummy' in group {msg.chat.id}")
            return

        if any(w in text for w in ["pic", "img", "image"]):
            log_info(f"Triggering image search for user {msg.from_user.id} in group {msg.chat.id}")
            await send_result(msg, "img")
        elif any(w in text for w in ["vid", "video"]):
            log_info(f"Triggering video search for user {msg.from_user.id} in group {msg.chat.id}")
            await send_result(msg, "vid")
        elif "news" in text:
            log_info(f"Triggering news search for user {msg.from_user.id} in group {msg.chat.id}")
            await send_result(msg, "news")
        else:
            log_info(f"Triggering web search for user {msg.from_user.id} in group {msg.chat.id}")
            await send_result(msg, "web")
    except Exception as e:
        log_error(f"Exception in dummy_keyword_trigger: {e}")

# Private chat trigger
@router.message(ChatTypeFilter(chat_type="private"))
async def private_smart_trigger(msg: types.Message):
    try:
        text = (msg.text or "").lower()
        log_info(f"Private message detected from user {msg.from_user.id}: {text}")

        if any(w in text for w in ["pic", "img", "image"]):
            log_info(f"Triggering image search in private for user {msg.from_user.id}")
            await send_result(msg, "img")
        elif any(w in text for w in ["vid", "video"]):
            log_info(f"Triggering video search in private for user {msg.from_user.id}")
            await send_result(msg, "vid")
        elif "news" in text:
            log_info(f"Triggering news search in private for user {msg.from_user.id}")
            await send_result(msg, "news")
        elif "web" in text or "search" in text:
            log_info(f"Triggering web search in private for user {msg.from_user.id}")
            await send_result(msg, "web")
        else:
            log_warn(f"No valid trigger word found in private message: {text}")
            await msg.reply(
                "❓ I didn’t understand. Try something like:\n\n"
                "<code>naruto image</code>\n"
                "<code>today's news</code>\n"
                "<code>hinata video</code>"
            )
    except Exception as e:
        log_error(f"Exception in private_smart_trigger: {e}")

# Bot command registration
async def register_commands(bot: Bot):
    log_info("Registering bot commands")
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="help", description="List available commands"),
            BotCommand(command="web", description="Web search"),
            BotCommand(command="img", description="Image search"),
            BotCommand(command="vid", description="Video search"),
            BotCommand(command="news", description="News search")
        ])
        log_success("Bot commands registered successfully")
    except Exception as e:
        log_error(f"Failed to register commands: {e}")

# Main runner
async def main():
    log_info("Starting bot")
    await register_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log_error(f"Fatal error in main: {e}")
