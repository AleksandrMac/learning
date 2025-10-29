import aiosqlite

async def migrate(db_name: str):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(db_name) as db:
        await create_table_quiz_state(db)

        await db.commit()
        await db.close()

async def create_table_quiz_state(db: aiosqlite.Connection):
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER)''')