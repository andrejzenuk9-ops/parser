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
    level=logging.DEBUG  # DEBUG чтобы видеть всё
)
logger = logging.getLogger(__name__)

# Получаем конфиги из окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')

# Парсим ADMIN_IDS
ADMIN_IDS = []
if ADMIN_IDS_STR:
    try:
        ADMIN_IDS = list(map(int, ADMIN_IDS_STR.split(',')))
        logger.info(f"✅ ADMIN_IDS загружены: {ADMIN_IDS}")
    except ValueError:
        logger.warning(f"⚠️  ADMIN_IDS некорректны: {ADMIN_IDS_STR}")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    logger.error("Добавьте BOT_TOKEN в .env файл или переменные окружения")
else:
    logger.info(f"✅ BOT_TOKEN загружен (длина: {len(BOT_TOKEN)})")


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
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        logger.info(f"📨 Команда /start от пользователя {user.id} ({user.first_name})")
        
        # Проверяем админа
        if ADMIN_IDS and user.id not in ADMIN_IDS:
            logger.warning(f"❌ Пользователь {user.id} не в списке админов")
            await update.message.reply_text(
                "❌ У вас нет доступа к этому боту.\n"
                f"Ваш ID: {user.id}\n"
                "Обратитесь к администратору."
            )
            return
        
        logger.info(f"✅ Пользователь {user.id} авторизован")
        
        # Создаём инлайн клавиатуру с типами прокси
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
                InlineKeyboardButton("⭐ Все типы", callback_data='fetch_all'),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "🤖 Я парсер прокси сервисов.\n"
            "Выберите тип прокси для получения:\n\n"
            "��се прокси проходят валидацию и проверку на доступность."
        )
        
        logger.info(f"📤 Отправляю стартовое сообщение пользователю {user.id}")
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        user = update.effective_user
        logger.info(f"📨 Команда /help от пользователя {user.id}")
        
        if ADMIN_IDS and user.id not in ADMIN_IDS:
            logger.warning(f"❌ Пользователь {user.id} не авторизован для /help")
            await update.message.reply_text("❌ Нет доступа")
            return
        
        help_text = """
📖 **Справка по использованию:**

/start - Начать работу, выбрать тип прокси
/help - Эта справка
/status - Статус бота

**Типы прокси:**
• 🔹 SOCKS4 - Протокол SOCKS версии 4
• 🔷 SOCKS5 - Протокол SOCKS версии 5 (более новый)
• 🟢 HTTP - Протокол HTTP
• 🟢 HTTPS - Протокол HTTPS

**Особенности:**
✅ Автоматическая валидация IP и портов
✅ Проверка на доступность (живые прокси)
✅ Удаление дубликатов
✅ Быстрая доставка результатов

📝 Просто нажмите на нужный тип прокси и получите список!
        """
        
        logger.info(f"📤 Отправляю справку пользователю {user.id}")
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /status"""
        user = update.effective_user
        logger.info(f"📨 Команда /status от пользователя {user.id}")
        
        if ADMIN_IDS and user.id not in ADMIN_IDS:
            await update.message.reply_text("❌ Нет доступа")
            return
        
        status_text = (
            "🤖 **Статус бота:**\n\n"
            "✅ Бот запущен и работает\n"
            f"✅ BOT_TOKEN: загружен\n"
            f"✅ ADMIN_IDS: {ADMIN_IDS if ADMIN_IDS else 'Не установлены (доступ всем)'}\n"
            f"✅ Ваш ID: `{user.id}`\n\n"
            "📝 Используйте /start для выбора типа прокси"
        )
        
        logger.info(f"📤 Отправляю статус пользователю {user.id}")
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def handle_proxy_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, proxy_type: str) -> None:
        """Обработчик запроса на получение прокси"""
        query = update.callback_query
        user = query.from_user
        
        logger.info(f"🔘 Кнопка нажата: {proxy_type} от пользователя {user.id}")
        
        await query.answer()
        
        if ADMIN_IDS and user.id not in ADMIN_IDS:
            logger.warning(f"❌ Пользователь {user.id} не авторизован")
            await query.edit_message_text("❌ Нет доступа")
            return
        
        # Отправляем статус обработки
        logger.info(f"⏳ Начинаю получение {proxy_type} прокси")
        await query.edit_message_text(
            f"⏳ Получение {self.PROXY_TYPES.get(proxy_type, proxy_type)} прокси...\n\n"
            "🔍 Парсим источники...\n"
            "✅ Валидируем...\n"
            "🔌 Проверяем доступность...",
            parse_mode='Markdown'
        )
        
        try:
            # Получаем и проверяем прокси
            if proxy_type == 'all':
                logger.info("📦 Получаю все типы прокси")
                all_proxies = {}
                tasks = []
                for ptype in ['socks4', 'socks5', 'http', 'https']:
                    tasks.append(self._fetch_proxies_for_type(ptype, all_proxies))
                
                await asyncio.gather(*tasks)
            else:
                # Получаем прокси одного типа
                logger.info(f"📦 Получаю {proxy_type} прокси")
                proxies = await ProxyParser.fetch_and_check_proxies(proxy_type, max_count=50)
                logger.info(f"✅ Получено {len(proxies)} {proxy_type} прокси")
                
                if not proxies:
                    logger.warning(f"⚠️  Живых {proxy_type} прокси не найдено")
                    await query.edit_message_text(
                        f"❌ Не удалось получить {self.PROXY_TYPES.get(proxy_type, proxy_type)} прокси\n\n"
                        "Возможные причины:\n"
                        "• Источники недоступны\n"
                        "• Нет живых прокси на данный момент\n"
                        "• Ошибка сети\n\n"
                        "Попробуйте позже или выберите другой тип."
                    )
                    return
                
                # Форматируем результаты
                result_text = self._format_proxies(proxy_type, proxies)
                
                # Отправляем результаты
                logger.info(f"📤 Отправляю результаты пользователю {user.id}")
                await query.edit_message_text(result_text, parse_mode='Markdown')
                
                # Опционально: сохраняем в файл если много прокси
                if len(proxies) > 30:
                    logger.info(f"💾 Сохраняю прокси в файл")
                    await self._save_and_send_file(query, proxy_type, proxies, context)
        
        except Exception as e:
            logger.error(f"❌ Ошибка при получении прокси: {e}", exc_info=True)
            await query.edit_message_text(
                f"❌ Ошибка при обработке запроса:\n{str(e)}\n\n"
                "Попробуйте позже."
            )
    
    async def _fetch_proxies_for_type(self, proxy_type: str, results: dict) -> None:
        """Получает прокси для конкретного типа"""
        try:
            logger.info(f"📦 Получаю {proxy_type} прокси (параллельно)")
            proxies = await ProxyParser.fetch_and_check_proxies(proxy_type, max_count=20)
            results[proxy_type] = proxies
            logger.info(f"✅ Получено {len(proxies)} {proxy_type} прокси")
        except Exception as e:
            logger.error(f"❌ Ошибка при получении {proxy_type}: {e}")
            results[proxy_type] = []
    
    def _format_proxies(self, proxy_type: str, proxies: List[str]) -> str:
        """Форматирует список прокси для вывода"""
        proxy_list = '\n'.join(proxies[:30])
        
        return (
            f"✅ **{self.PROXY_TYPES.get(proxy_type, proxy_type)} Прокси**\n\n"
            f"📊 Найдено: `{len(proxies)}` живых прокси\n\n"
            f"```\n{proxy_list}\n```\n\n"
            f"💾 Всего получено: `{len(proxies)}`"
        )
    
    async def _save_and_send_file(self, query, proxy_type: str, proxies: List[str], context: ContextTypes.DEFAULT_TYPE) -> None:
        """Сохраняет прокси в файл и отправляет"""
        try:
            filename = f"{proxy_type}_proxies.txt"
            with open(filename, 'w') as f:
                f.write('\n'.join(proxies))
            
            logger.info(f"📁 Файл создан: {filename}")
            
            with open(filename, 'rb') as f:
                await query.message.reply_document(
                    f,
                    caption=f"📄 Файл со всеми {self.PROXY_TYPES.get(proxy_type, proxy_type)} прокси ({len(proxies)} шт.)"
                )
            
            os.remove(filename)
            logger.info(f"✅ Файл отправлен и удален")
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении файла: {e}")
    
    def setup_handlers(self) -> None:
        """Настраивает обработчики команд"""
        logger.info("📌 Регистрирую обработчики команд")
        
        # Команды
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Callback кнопок
        self.application.add_handler(CallbackQueryHandler(
            lambda u, c: self.handle_proxy_request(u, c, 'socks4'),
            pattern='^fetch_socks4$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            lambda u, c: self.handle_proxy_request(u, c, 'socks5'),
            pattern='^fetch_socks5$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            lambda u, c: self.handle_proxy_request(u, c, 'http'),
            pattern='^fetch_http$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            lambda u, c: self.handle_proxy_request(u, c, 'https'),
            pattern='^fetch_https$'
        ))
        self.application.add_handler(CallbackQueryHandler(
            lambda u, c: self.handle_proxy_request(u, c, 'all'),
            pattern='^fetch_all$'
        ))
        
        logger.info("✅ Обработчики команд зарегистрированы")
    
    async def run(self) -> None:
        """Запускает бота"""
        logger.info("=" * 60)
        logger.info("🤖 ЗАПУСК TELEGRAM БОТА")
        logger.info("=" * 60)
        
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN не установлен!")
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        
        logger.info(f"✅ BOT_TOKEN: загружен (длина {len(BOT_TOKEN)})")
        logger.info(f"✅ ADMIN_IDS: {ADMIN_IDS if ADMIN_IDS else 'Не установлены (доступ всем)'}")
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        self.setup_handlers()
        
        # Запускаем бота
        logger.info("🔌 Подключаюсь к Telegram...")
        await self.application.initialize()
        logger.info("✅ Инициализация завершена")
        
        await self.application.start()
        logger.info("✅ Приложение запущено")
        
        await self.application.updater.start_polling()
        logger.info("✅ Polling запущен - бот готов к работе!")
        logger.info("=" * 60)
        logger.info("📝 Напишите боту /start")
        logger.info("=" * 60)
        
        # Блокируем поток
        await asyncio.Event().wait()


def main():
    """Главная функция"""
    bot = ProxyBot()
    asyncio.run(bot.run())


if __name__ == '__main__':
    main()
