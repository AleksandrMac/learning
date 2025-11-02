import logging
import json
import os
from aiogram import Bot, Dispatcher, types

from handlers import router
from migrate import run_migrations
from _ydb import get_ydb_pool
import repo
import usecase

# необходимо создать файл .env
API_TOKEN       = os.getenv("API_TOKEN")
YDB_ENDPOINT    = os.getenv("YDB_ENDPOINT")
YDB_DATABASE    = os.getenv("YDB_DATABASE")


bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

async def process_event(event):

    # await bot.set_webhook("https://d5dp3hd5n2pee7favpgj.ubofext2.apigw.yandexcloud.net/bot-api")
    update = types.Update.model_validate(json.loads(event['body']), context={"bot": bot})
    await dp.feed_update(bot, update)

async def webhook(event, context):
    
    run_migrations(YDB_ENDPOINT, YDB_DATABASE)
    
    qr = repo.QuizRepo(get_ydb_pool(YDB_ENDPOINT, YDB_DATABASE))
    uc = usecase.QuizUseCase(qr)

    dp.include_router(router(uc))

    if event['httpMethod'] == 'POST':
        # Bot and dispatcher initialization
        # Объект бота

        await process_event(event)
        return {'statusCode': 200, 'body': 'ok'}

    return {'statusCode': 405}

