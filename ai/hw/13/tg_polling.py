import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from handlers import router
from migrate import run_migrations
from _ydb import get_ydb_pool_dev
import repo
import usecase

load_dotenv()  # This loads variables from .env into os.environ

# необходимо создать файл .env
API_TOKEN       = os.getenv("API_TOKEN")
YDB_ENDPOINT    = os.getenv("YDB_ENDPOINT")
YDB_DATABASE    = os.getenv("YDB_DATABASE")


bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Запуск процесса поллинга новых апдейтов
async def main():
    
    qr = repo.QuizRepo(get_ydb_pool_dev(YDB_ENDPOINT, YDB_DATABASE))
    uc = usecase.QuizUseCase(qr)

    dp.include_router(router(uc))

    run_migrations(YDB_ENDPOINT, YDB_DATABASE)

    await bot.delete_webhook()
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())