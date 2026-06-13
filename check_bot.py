import os
import asyncio
import logging
from dotenv import load_dotenv
import aiohttp

# Загружаем переменные окружения
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS', '')

async def check_bot_health():
    """Проверяет здоровье бота и подключение к Telegram"""
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return False
    
    logger.info(f"✅ BOT_TOKEN найден (длина: {len(BOT_TOKEN)})")
    logger.info(f"✅ ADMIN_IDS: {ADMIN_IDS if ADMIN_IDS else 'Не установлены'}")
    
    # Проверяем подключение к Telegram API
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                
                if resp.status == 200:
                    logger.info(f"✅ Бот подключен к Telegram!")
                    logger.info(f"✅ Имя бота: @{data['result']['username']}")
                    logger.info(f"✅ ID бота: {data['result']['id']}")
                    return True
                else:
                    logger.error(f"❌ Ошибка Telegram API: {data}")
                    return False
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Telegram: {e}")
        return False

async def check_webhook_status():
    """Проверяет статус webhook"""
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                
                if resp.status == 200:
                    webhook_info = data['result']
                    logger.info(f"📡 Webhook информация:")
                    logger.info(f"   URL: {webhook_info.get('url', 'Не установлен')}")
                    logger.info(f"   Статус: {'Активен' if webhook_info.get('url') else 'Отключен'}")
                    logger.info(f"   Pending обновлений: {webhook_info.get('pending_update_count', 0)}")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке webhook: {e}")

async def main():
    """Главная функция"""
    logger.info("=" * 50)
    logger.info("🔍 ПРОВЕРКА ЗДОРОВЬЯ БОТА")
    logger.info("=" * 50)
    
    is_healthy = await check_bot_health()
    
    if is_healthy:
        logger.info("\n📡 Проверка Webhook статуса...")
        await check_webhook_status()
        
        logger.info("\n✅ Бот готов к работе!")
        logger.info("⏳ Если бот не отвечает, проверьте:")
        logger.info("   1. Бот запущен? (docker-compose logs -f)")
        logger.info("   2. Используете ли вы правильный BOT_TOKEN?")
        logger.info("   3. Добавили ли вы бота в чат?")
        logger.info("   4. Отправили ли /start?")
    else:
        logger.error("\n❌ Бот не подключен к Telegram!")
        logger.error("Проверьте BOT_TOKEN и интернет соединение")

if __name__ == '__main__':
    asyncio.run(main())
