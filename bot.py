import logging
import functools
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, OWNER_ID
from database import Database

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

# Константы для callback_data
REGISTER = "register"
VIEW_EMAIL = "view_email"
ASSIGN_NEW = "assign_new"


def owner_only(func):
    """Декоратор для проверки, что пользователь является владельцем бота."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            await update.message.reply_text(
                "Извините, у вас нет доступа к этому боту."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper



@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Привет! Я бот для управления аккаунтами Google.\n\n"
        "Отправьте мне название сервиса, для которого вы хотите использовать почту "
        "(например, 'groq', 'openai', 'anthropic')."
    )


@owner_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    await update.message.reply_text(
        "Как использовать этого бота:\n\n"
        "1. Отправьте название сервиса (например, 'groq')\n"
        "2. Выберите действие: 'Зарегистрироваться' или 'Посмотреть почту'\n"
        "3. Следуйте инструкциям бота\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку"
    )


@owner_only
async def handle_service_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик сообщений с названием сервиса."""
    service_name = update.message.text.strip()
    context.user_data["service_name"] = service_name
    
    keyboard = [
        [
            InlineKeyboardButton("Зарегистрироваться", callback_data=REGISTER),
            InlineKeyboardButton("Посмотреть почту", callback_data=VIEW_EMAIL),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Выбран сервис: {service_name}\n"
        f"Что вы хотите сделать?",
        reply_markup=reply_markup,
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки."""
    query = update.callback_query
    await query.answer()
    
    # Проверка, что пользователь является владельцем бота
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await query.edit_message_text(
            "Извините, у вас нет доступа к этому боту."
        )
        return
    
    service_name = context.user_data.get("service_name")
    if not service_name:
        await query.edit_message_text(
            "Произошла ошибка. Пожалуйста, отправьте название сервиса заново."
        )
        return
    
    if query.data == REGISTER:
        await handle_registration(query, context, service_name)
    elif query.data == VIEW_EMAIL:
        await handle_view_email(query, service_name)
    elif query.data == ASSIGN_NEW:
        await handle_assign_new(query, service_name)


async def handle_registration(query, context, service_name):
    """Обработка регистрации."""
    has_email, email = db.check_and_assign_gmail(service_name)
    
    if has_email:
        keyboard = [
            [InlineKeyboardButton("Привязать новую почту", callback_data=ASSIGN_NEW)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем все почты для этого сервиса
        all_emails = db.get_service_gmails(service_name)
        email_count = len(all_emails)
        
        await query.edit_message_text(
            f"К сервису {service_name} уже привязана почта: {email}\n"
            f"Это почта #{email_count} для этого сервиса.\n"
            f"Хотите привязать новую почту?",
            reply_markup=reply_markup,
        )
    else:
        if email == "Нет доступных почт":
            await query.edit_message_text(
                f"К сожалению, все почты уже использованы. "
                f"Пожалуйста, добавьте новые почты в файл."
            )
        else:
            await query.edit_message_text(
                f"Для сервиса {service_name} выделена почта: {email}\n"
                f"Это первая почта для этого сервиса.\n"
                f"Используйте её для регистрации."
            )


async def handle_view_email(query, service_name):
    """Обработка просмотра почты."""
    emails = db.get_service_gmails(service_name)
    
    if emails:
        if len(emails) == 1:
            await query.edit_message_text(
                f"К сервису {service_name} привязана почта: {emails[0]}"
            )
        else:
            email_list = "\n".join([f"{i+1}. {email}" for i, email in enumerate(emails)])
            await query.edit_message_text(
                f"К сервису {service_name} привязаны следующие почты:\n\n{email_list}\n\n"
                f"Последняя использованная: {emails[-1]}"
            )
    else:
        await query.edit_message_text(
            f"К сервису {service_name} еще не привязана ни одна почта.\n"
            f"Используйте кнопку 'Зарегистрироваться', чтобы привязать почту."
        )


async def handle_assign_new(query, service_name):
    """Обработка привязки новой почты."""
    new_email = db.get_unused_gmail_for_service(service_name)
    
    if new_email:
        db.assign_gmail_to_service(service_name, new_email)
        
        # Получаем все почты для этого сервиса
        all_emails = db.get_service_gmails(service_name)
        email_count = len(all_emails)
        
        await query.edit_message_text(
            f"К сервису {service_name} привязана новая почта: {new_email}\n"
            f"Это почта #{email_count} для этого сервиса."
        )
    else:
        await query.edit_message_text(
            f"К сожалению, все почты уже использованы для этого сервиса. "
            f"Пожалуйста, добавьте новые почты в файл."
        )


def main() -> None:
    """Запуск бота."""
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_service_name))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
