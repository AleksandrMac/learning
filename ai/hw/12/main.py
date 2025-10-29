import asyncio
import logging

from dotenv import load_dotenv
import os

from handlers import dispatcher
from migration import migrate
import repo
import usecase

load_dotenv()  # This loads variables from .env into os.environ

# необходимо создать файл .env
API_TOKEN = os.getenv("API_KEY")

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)


# Зададим имя базы данных
DB_NAME = 'quiz_bot.db'




# Запуск процесса поллинга новых апдейтов
async def main():

    # Запускаем создание таблицы базы данных
    await migrate(DB_NAME)

    db = repo.QuizRepo(DB_NAME)
    uc = usecase.QuizUseCase(db)
    await dispatcher(uc).start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())