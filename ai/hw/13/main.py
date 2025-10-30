import asyncio
import logging
from aiogram import Bot

from dotenv import load_dotenv
import os

from handlers import dispatcher
from migration import migrate
import repo
import usecase

load_dotenv()  # This loads variables from .env into os.environ

# необходимо создать файл .env
API_TOKEN = os.getenv("API_KEY")
DB_NAME = 'quiz_bot.db'

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Запуск процесса поллинга новых апдейтов
async def main():

    # Запускаем создание таблицы базы данных
    await migrate(DB_NAME)

    db = repo.QuizRepo(DB_NAME)
    uc = usecase.QuizUseCase(db)
    # Объект бота
    bot = Bot(token=API_TOKEN)
    await dispatcher(uc).start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())