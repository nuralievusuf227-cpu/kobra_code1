"""
YouTube Downloader Telegram Bot
Python 3.10+ | aiogram 3.x | yt-dlp
"""

import os
import asyncio
import re
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import yt_dlp
from dotenv import load_dotenv
import shutil

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to locate ffmpeg/ffprobe either from environment or system PATH
FFMPEG_PATH = os.getenv('FFMPEG_PATH') or shutil.which('ffmpeg')
FFPROBE_PATH = os.getenv('FFPROBE_PATH') or shutil.which('ffprobe')
FFMPEG_AVAILABLE = bool(FFMPEG_PATH and FFPROBE_PATH)
if not FFMPEG_AVAILABLE:
    logger.warning('FFmpeg/ffprobe not found. MP3 conversion will be unavailable.')

# ==================== CONFIGURATION ====================

TEMP_DIR = Path("temp_downloads")
MAX_FILESIZE_MB = 50  # Telegram limit for free accounts
YOUTUBE_URL_PATTERN = r"(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/"

# Create temp directory
TEMP_DIR.mkdir(exist_ok=True)

# ==================== STATE MACHINE ====================

class DownloadStates(StatesGroup):
    """FSM states for download process"""
    waiting_for_url = State()
    waiting_for_format = State()
    downloading = State()


# ==================== UTILITY FUNCTIONS ====================

def validate_youtube_url(url: str) -> bool:
    """Validate if URL is a valid YouTube link"""
    return bool(re.match(YOUTUBE_URL_PATTERN, url))


async def get_video_info(url: str) -> Optional[dict]:
    """Get video info using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            # prefer IPv4 and avoid certificate checks which can hang in some envs
            'source_address': '0.0.0.0',
            'nocheckcertificate': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'id': info.get('id'),
            }
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None


async def download_video(url: str, output_path: Path) -> bool:
    """Download video in MP4 format"""
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': str(output_path / '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        return True
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return False


async def download_audio(url: str, output_path: Path) -> bool:
    """Download audio in MP3 format"""
    try:
        # If FFmpeg is available, postprocess to MP3. Otherwise download best audio raw.
        if FFMPEG_AVAILABLE:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(output_path / '%(id)s.%(ext)s'),
                'ffmpeg_location': FFMPEG_PATH or None,
                'quiet': True,
                'no_warnings': True,
            }
        else:
            # Fallback: download best audio without conversion (may be webm/m4a/opus)
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_path / '%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        return True
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        return False


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB"""
    return file_path.stat().st_size / (1024 * 1024)


async def cleanup_files(file_path: Path):
    """Delete temporary file"""
    try:
        if file_path.exists():
            await asyncio.to_thread(file_path.unlink)
            logger.info(f"Cleaned up: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file: {e}")


async def cleanup_session(session_dir: Path):
    """Clean up all files in session directory"""
    try:
        if session_dir.exists():
            for file in session_dir.glob('*'):
                await cleanup_files(file)
            session_dir.rmdir()
    except Exception as e:
        logger.error(f"Error cleaning up session: {e}")


# ==================== KEYBOARD BUILDERS ====================

def get_format_keyboard() -> InlineKeyboardMarkup:
    """Build format selection keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 MP4 (Видео)", callback_data="format_video"),
                InlineKeyboardButton(text="🎵 MP3 (Аудио)", callback_data="format_audio"),
            ]
        ]
    )


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Build start menu keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="help_info")],
        ]
    )


# ==================== MESSAGE HANDLERS ====================

async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    welcome_text = (
        "🎉 Хуш омадед ба боти мо !\n\n"
        "Ман метавонам аз YouTube видио ва музикаро скачат кунам.\n\n"
        "📝 Факат силкаро равон кун тамом:\n"
        "• 🎬 MP4 — скачать видео\n"
        "• 🎵 MP3 — скачать только музику\n\n"
        "⚠️ Хамаги то 50 МБ метавонам скачат кунам\n"
        "🔒 Бади баромад файлхо пок мешаванд\n\n"
        "👇 ссылкаро аз YouTube, равон кун то ман огоз кунам"
    )
    
    await message.answer(welcome_text, reply_markup=get_start_keyboard())
    await state.set_state(DownloadStates.waiting_for_url)


async def cmd_help(message: types.Message):
    """Handle /help command"""
    help_text = (
        "📖 Инструкция по использованию:\n\n"
        "1️⃣ Отправьте ссылку на YouTube видео\n"
        "   Примеры форматов:\n"
        "   • https://www.youtube.com/watch?v=...\n"
        "   • https://youtu.be/...\n\n"
        "2️⃣ Выберите формат скачивания:\n"
        "   • 🎬 MP4 — полное видео\n"
        "   • 🎵 MP3 — только аудио\n\n"
        "3️⃣ Ожидайте ⏳ пока бот скачает файл\n\n"
        "4️⃣ Получите готовый файл ✅\n\n"
        "⏱️ Время ожидания зависит от размера видео\n"
        "📊 Максимальный размер файла: 50 МБ"
    )
    await message.answer(help_text)


async def process_url_input(message: types.Message, state: FSMContext):
    """Process incoming URL"""
    url = message.text.strip()
    
    # Validate URL
    if not validate_youtube_url(url):
        await message.answer(
            "❌ Некорректная ссылка!\n\n"
            "Пожалуйста, отправьте правильную ссылку YouTube:\n"
            "• https://www.youtube.com/watch?v=...\n"
            "• https://youtu.be/..."
        )
        return
    
    # Show loading message
    status_msg = await message.answer("🔍 Проверяю видео...")
    
    try:
        # Get video info (increase timeout because extraction can be slow)
        info = await asyncio.wait_for(get_video_info(url), timeout=60)
        
        if not info:
            await status_msg.edit_text(
                "❌ Не удалось получить информацию о видео.\n"
                "Проверьте ссылку и попробуйте еще раз."
            )
            return
        
        # Show video info and format selection
        title = info['title'][:50] + "..." if len(info['title']) > 50 else info['title']
        duration_sec = info['duration']
        duration_min = duration_sec // 60
        
        info_text = (
            f"📹 Видео найдено!\n\n"
            f"📝 Название: {title}\n"
            f"⏱️ Длительность: {duration_min} мин\n\n"
            f"Выберите формат скачивания:"
        )
        
        # Store URL in state
        await state.update_data(url=url)
        
        # Update message with format selection
        await status_msg.edit_text(info_text, reply_markup=get_format_keyboard())
        await state.set_state(DownloadStates.waiting_for_format)
        
    except asyncio.TimeoutError:
        await status_msg.edit_text(
            "⏱️ Превышено время ожидания.\n"
            "Попробуйте другую ссылку."
        )
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        await status_msg.edit_text(
            "❌ Ошибка при обработке ссылки.\n"
            "Попробуйте еще раз."
        )


async def process_format_selection(callback: types.CallbackQuery, state: FSMContext):
    """Process format selection"""
    
    user_data = await state.get_data()
    url = user_data.get('url')
    
    if not url:
        await callback.answer("❌ Ошибка: ссылка потеряна", show_alert=True)
        return
    
    # Create session directory
    session_dir = TEMP_DIR / f"session_{callback.from_user.id}_{int(datetime.now().timestamp())}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Show downloading status
        await callback.message.edit_text("⏳ Загрузка файла...")
        await callback.answer()
        
        format_type = callback.data.split('_')[1]
        
        # Download file
        if format_type == "video":
            # Increase download timeout for larger videos / slow connections
            success = await asyncio.wait_for(download_video(url, session_dir), timeout=600)
            file_ext = "mp4"
            format_name = "MP4 видео"
        else:  # audio
            success = await asyncio.wait_for(download_audio(url, session_dir), timeout=600)
            file_ext = "mp3"
            format_name = "MP3 аудио"
        
        if not success:
            await callback.message.edit_text(
                "❌ Ошибка при скачивании файла.\n"
                "Попробуйте еще раз."
            )
            await cleanup_session(session_dir)
            return
        
        # Find downloaded file (any extension)
        files = list(session_dir.glob("*.*"))

        if not files:
            await callback.message.edit_text(
                "❌ Файл не найден после скачивания.\n"
                "Попробуйте еще раз."
            )
            await cleanup_session(session_dir)
            return

        # Prefer the first file (yt-dlp usually writes one file per session)
        file_path = files[0]
        file_size_mb = get_file_size_mb(file_path)
        file_ext = file_path.suffix.lstrip('.').lower()
        
        # Check file size
        if file_size_mb > MAX_FILESIZE_MB:
            await callback.message.edit_text(
                f"❌ Файл слишком большой: {file_size_mb:.1f} МБ\n"
                f"Максимальный размер: {MAX_FILESIZE_MB} МБ"
            )
            await cleanup_session(session_dir)
            return
        
        # Send file to user
        await callback.message.edit_text("📤 Отправляю файл...")

        caption = (
            f"✅ Готово!\n\n"
            f"📦 Формат: {format_name}\n"
            f"📊 Размер: {file_size_mb:.1f} МБ\n"
            f"📄 Файл: {file_path.name}"
        )

        fs_file = FSInputFile(str(file_path), filename=file_path.name)

        # If video
        if file_ext in ("mp4", "mkv", "mov", "webm") and format_type == "video":
            await callback.message.answer_video(fs_file, caption=caption)
        else:
            # Audio: if we have mp3 and ffmpeg was used, send as audio; otherwise send as document
            if format_type == "audio" and file_ext == "mp3":
                await callback.message.answer_audio(fs_file, caption=caption)
            else:
                # send as document when format is not standard mp3
                await callback.message.answer_document(fs_file, caption=caption)
        
        # Delete original message
        await callback.message.delete()
        
        # Cleanup
        await cleanup_session(session_dir)
        
        # Reset state
        await state.set_state(DownloadStates.waiting_for_url)
        
    except asyncio.TimeoutError:
        await callback.message.edit_text(
            "⏱️ Превышено время ожидания.\n"
            "Видео слишком большое или подключение медленное."
        )
        await cleanup_session(session_dir)
    except Exception as e:
        logger.error(f"Error in format selection: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при обработке запроса.\n"
            "Попробуйте еще раз."
        )
        await cleanup_session(session_dir)


async def handle_help_callback(callback: types.CallbackQuery):
    """Handle help button callback"""
    help_text = (
        "📖 Инструкция по использованию:\n\n"
        "1️⃣ Отправьте ссылку на YouTube видео\n"
        "   Примеры форматов:\n"
        "   • https://www.youtube.com/watch?v=...\n"
        "   • https://youtu.be/...\n\n"
        "2️⃣ Выберите формат скачивания:\n"
        "   • 🎬 MP4 — полное видео\n"
        "   • 🎵 MP3 — только аудио\n\n"
        "3️⃣ Ожидайте ⏳ пока бот скачает файл\n\n"
        "4️⃣ Получите готовый файл ✅\n\n"
        "⏱️ Время ожидания зависит от размера видео\n"
        "📊 Максимальный размер файла: 50 МБ"
    )
    await callback.message.answer(help_text)
    await callback.answer()


async def invalid_input(message: types.Message):
    """Handle invalid input"""
    await message.answer(
        "❌ Команда не распознана.\n\n"
        "Отправьте ссылку YouTube или используйте:\n"
        "/start — начать заново\n"
        "/help — инструкция"
    )


# ==================== MAIN SETUP ====================

async def main():
    """Main bot setup and run"""
    
    # Initialize bot and dispatcher
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register handlers
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(
        process_url_input,
        DownloadStates.waiting_for_url,
        F.text
    )
    dp.callback_query.register(
        process_format_selection,
        DownloadStates.waiting_for_format,
        F.data.startswith("format_")
    )
    dp.callback_query.register(handle_help_callback, F.data == "help_info")
    dp.message.register(invalid_input)
    
    logger.info("Bot started polling...")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
