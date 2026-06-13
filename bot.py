import logging
import os
import asyncio
from typing import List
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from proxy_parser import ProxyParser, ProxyValidator

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования (выводит в консоль)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем конфиги
BOT_TOKEN = os.getenv('BOT_TOKEN', '8944317518:AAEUOsUTK60QND_pnDjLYCqIq5EF4IL5MPI')
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '5159147982')

logger.info("=" * 70)
logger.info("🤖 ИНИЦИАЛИЗАЦИЯ БОТА")
logger.info("=" * 70)

# Парсим ADMIN_IDS
ADMIN_IDS = []
if ADMIN_IDS_STR:
    try:
        ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(',')]
        logger.info(f"✅ ADMIN_IDS: {ADMIN_IDS}")
    except ValueError as e:
        logger.error(f"⚠️  Ошибка парсинга ADMIN_IDS '{ADMIN_IDS_STR}': {e}")
        ADMIN_IDS = []

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    raise ValueError("BOT_TOKEN обязателен")
else:
    logger.info(f"✅ BOT_TOKEN загружен")


class ProxyBot:
    """Telegram бот для парсинга прокси"""
    
    PROXY_TYPES = {
        'socks4': 'SOCKS4',
        'socks5': 'SOCKS5',
        'http': 'HTTP',
        'https': 'HTTPS'
    }
    
    def __init__(self):
        self.application = None
    
    def check_access(self, user_id: int) -> bool:
        """Проверяет доступ пользователя"""
        if not ADMIN_IDS:
            # Если админов нет - доступ для всех
            return True
        
        has_access = user_id in ADMIN_IDS
        if not has_access:
            logger.warning(f"❌ Доступ запрещен пользователю {user_id} (админы: {ADMIN_IDS})")
        return has_access
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        try:
            user = update.effective_user
            logger.info(f"📨 /start от {user.id} {user.first_name}")
            
            if not self.check_access(user.id):
                logger.warning(f"❌ Доступ запрещен {user.id}")
                await update.message.reply_text(
                    f"❌ Доступ запрещен\n"
                    f"Ваш ID: {user.id}\n"
                    f"Админы: {ADMIN_IDS}"
                )
                return
            
            keyboard = [
                [
                    InlineKeyboardButton("🔹 SOCKS4", callback_data='fetch_socks4'),
                    InlineKeyboardButton("🔷 SOCKS5", callback_data='fetch_socks5'),
                ],
                [
                    InlineKeyboardButton("🟢 HTTP", callback_data='fetch_http'),
                    InlineKeyboardButton("🟢 HTTPS", callback_data='fetch_https'),
                ],
                [
                    InlineKeyboardButton("⭐ Все", callback_data='fetch_all'),
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = (
                f"👋 Привет {user.first_name}!\n\n"
                "🤖 Я парсер прокси\n"
                "Выберите тип прокси:"
            )
            
            await update.message.reply_text(message_text, reply_markup=reply_markup)
            logger.info(f"✅ Ответ отправлен {user.id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в start: {e}", exc_info=True)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        try:
            user = update.effective_user
            logger.info(f"📨 /help от {user.id}")
            
            if not self.check_access(user.id):
                await update.message.reply_text("❌ Доступ запрещен")
                return
            
            help_text = """
📖 **Справка:**

/start - Главное меню
/help - Эта справка
/status - Статус бота

**Типы прокси:**
🔹 SOCKS4, 🔷 SOCKS5
🟢 HTTP, 🟢 HTTPS

**Функции:**
✅ Валидация IP:Port
✅ Проверка живых прокси
✅ Удаление дубликатов
            """
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
            logger.info(f"✅ Help отправлен {user.id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в help: {e}", exc_info=True)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /status"""
        try:
            user = update.effective_user
            logger.info(f"📨 /status от {user.id}")
            
            if not self.check_access(user.id):
                await update.message.reply_text("❌ Доступ запрещен")
                return
            
            status_text = (
                "🤖 **Статус бота:**\n\n"
                "✅ Бот активен\n"
                f"✅ Ваш ID: `{user.id}`\n"
                f"✅ Админы: {ADMIN_IDS}\n"
                f"✅ Вы админ: {'ДА' if user.id in ADMIN_IDS else 'НЕТ'}\n"
            )
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            logger.info(f"✅ Status отправлен {user.id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в status: {e}", exc_info=True)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик кнопок"""
        try:
            query = update.callback_query
            user = query.from_user
            
            logger.info(f"🔘 Кнопка '{query.data}' от {user.id}")
            
            if not self.check_access(user.id):
                await query.answer("Доступ запрещен")
                return
            
            proxy_type = query.data.replace('fetch_', '')
            
            await query.answer()
            
            await query.edit_message_text(
                f"⏳ Получаю {self.PROXY_TYPES.get(proxy_type, proxy_type)} прокси...\n\n"
                "🔍 Парсим источники\n"
                "✅ Валидируем\n"
                "🔌 Проверяем..."
            )
            
            logger.info(f"📦 Начинаю получение {proxy_type}")
            
            proxies = await ProxyParser.fetch_and_check_proxies(proxy_type, max_count=50)
            logger.info(f"✅ Получено {len(proxies)} прокси")
            
            if not proxies:
                await query.edit_message_text(
                    f"❌ Не найдено живых {proxy_type} прокси"
                )
                return
            
            proxy_list = '\n'.join(proxies[:30])
            result = (
                f"✅ **{self.PROXY_TYPES.get(proxy_type, proxy_type)}**\n\n"
                f"📊 Найдено: `{len(proxies)}`\n\n"
                f"```\n{proxy_list}\n```"
            )
            
            await query.edit_message_text(result, parse_mode='Markdown')
            logger.info(f"✅ Результаты отправлены {user.id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в callback: {e}", exc_info=True)
    
    def setup_handlers(self) -> None:
        """Регистрирует обработчики"""
        logger.info("📌 Регистрирую обработчики...")
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("✅ Обработчики зарегистрированы")
    
    async def run(self) -> None:
        """Запускает бота"""
        logger.info("🚀 Запускаю бота...")
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        
        logger.info("🔌 Подключаюсь к Telegram...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("=" * 70)
        logger.info("✅ БОТ ЗАПУЩЕН И ГОТОВ!")
        logger.info("=" * 70)
        logger.info(f"BOT_TOKEN: загружен")
        logger.info(f"ADMIN_IDS: {ADMIN_IDS}")
        logger.info("Ожидаю сообщений...")
        logger.info("=" * 70)
        
        await asyncio.Event().wait()


def main():
    """Главная функция"""
    try:
        bot = ProxyBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)


if __name__ == '__main__':
    main()
