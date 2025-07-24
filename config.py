# Конфигурационный файл для телеграм-бота
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Токен вашего бота (загружается из .env файла)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID владельца бота в Telegram (загружается из .env файла)
# Чтобы узнать свой ID, отправьте сообщение боту @userinfobot
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# Путь к файлу с почтами
GMAILS_FILE = "gmails.txt"

# Путь к файлу с данными о привязках сервисов к почтам
DATABASE_FILE = "services_data.json"
