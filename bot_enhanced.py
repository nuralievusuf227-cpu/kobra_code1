"""
Enhanced version with additional features and database support
Optional: Uncomment and modify as needed
"""

# This is an optional enhanced version with the following features:
# - User statistics tracking
# - Download history
# - Rate limiting
# - Admin commands
# - Configuration management

"""
# Uncomment to use this version

import json
from datetime import datetime, timedelta
from typing import Dict, List

# Database simulation (use SQLite for production)
USER_STATS: Dict = {}
DOWNLOAD_HISTORY: List = []


async def track_download(user_id: int, video_title: str, format_type: str, file_size_mb: float):
    '''Track user download statistics'''
    
    if user_id not in USER_STATS:
        USER_STATS[user_id] = {
            'downloads': 0,
            'total_size_mb': 0.0,
            'last_download': None,
            'favorite_format': None
        }
    
    stats = USER_STATS[user_id]
    stats['downloads'] += 1
    stats['total_size_mb'] += file_size_mb
    stats['last_download'] = datetime.now().isoformat()
    
    # Update favorite format
    format_list = [h.get('format') for h in DOWNLOAD_HISTORY if h['user_id'] == user_id]
    if format_list:
        video_count = format_list.count('mp4')
        audio_count = format_list.count('mp3')
        stats['favorite_format'] = 'MP4' if video_count >= audio_count else 'MP3'
    
    # Add to history
    DOWNLOAD_HISTORY.append({
        'user_id': user_id,
        'title': video_title,
        'format': format_type,
        'size_mb': file_size_mb,
        'timestamp': datetime.now().isoformat()
    })


async def get_user_stats(user_id: int) -> str:
    '''Get user statistics'''
    if user_id not in USER_STATS:
        return "У вас еще нет загрузок"
    
    stats = USER_STATS[user_id]
    stats_text = (
        f"📊 Ваша статистика:\n\n"
        f"📥 Всего загрузок: {stats['downloads']}\n"
        f"📦 Общий размер: {stats['total_size_mb']:.1f} МБ\n"
        f"⭐ Любимый формат: {stats['favorite_format'] or 'не определен'}\n"
        f"🕐 Последняя загрузка: {stats['last_download']}"
    )
    return stats_text


# Rate limiting
RATE_LIMITS: Dict[int, List[datetime]] = {}
MAX_DOWNLOADS_PER_HOUR = 10


async def check_rate_limit(user_id: int) -> bool:
    '''Check if user exceeded rate limit'''
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    
    if user_id not in RATE_LIMITS:
        RATE_LIMITS[user_id] = []
    
    # Remove old timestamps
    RATE_LIMITS[user_id] = [
        ts for ts in RATE_LIMITS[user_id] if ts > hour_ago
    ]
    
    if len(RATE_LIMITS[user_id]) >= MAX_DOWNLOADS_PER_HOUR:
        return False
    
    RATE_LIMITS[user_id].append(now)
    return True


# Admin commands
ADMIN_IDS = [123456789]  # Add your admin Telegram ID


async def cmd_admin_stats(message: types.Message):
    '''Get global statistics (admin only)'''
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа")
        return
    
    total_users = len(USER_STATS)
    total_downloads = sum(s['downloads'] for s in USER_STATS.values())
    total_size = sum(s['total_size_mb'] for s in USER_STATS.values())
    
    stats_text = (
        f"📊 Глобальная статистика:\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"📥 Всего загрузок: {total_downloads}\n"
        f"📦 Общий размер: {total_size:.1f} МБ"
    )
    
    await message.answer(stats_text)


async def cmd_stats(message: types.Message):
    '''User statistics command'''
    stats_text = await get_user_stats(message.from_user.id)
    await message.answer(stats_text)
"""

# To enable enhanced features:
# 1. Uncomment the code above
# 2. Register command handler in main():
#    dp.message.register(cmd_stats, Command("stats"))
#    dp.message.register(cmd_admin_stats, Command("admin_stats"))
# 3. Add rate limiting check before download:
#    if not await check_rate_limit(user_id):
#        await message.answer("❌ Превышен лимит загрузок")
# 4. Track downloads after successful upload:
#    await track_download(user_id, title, format_type, file_size_mb)
