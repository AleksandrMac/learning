import aiosqlite

async def migrate(db_name: str):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(db_name) as db:
        await create_table_quiz_state(db)
        await create_table_statistic(db)
        await db.commit()

async def create_table_quiz_state(db: aiosqlite.Connection):
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER)''')

async def create_table_statistic(db: aiosqlite.Connection):
        await db.execute('''CREATE TABLE IF NOT EXISTS statistic (user_id INTEGER PRIMARY KEY, last_amount INTEGER)''')