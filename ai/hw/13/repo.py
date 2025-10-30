import aiosqlite

class QuizRepo:
    def __init__(self, db_name: str):        
        self.db_path = db_name

    async def get_quiz_index(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем запись для заданного пользователя
            async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
                # Возвращаем результат
                results = await cursor.fetchone()
                if results is not None:
                    return results[0]
                else:
                    return 0

    async def update_quiz_index(self, user_id, index):
        async with aiosqlite.connect(self.db_path) as db:
            # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
            await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
            # Сохраняем изменения
            await db.commit()

    async def get_statistic(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем запись для заданного пользователя
            async with db.execute('SELECT last_amount FROM statistic WHERE user_id = (?)', (user_id, )) as cursor:
                # Возвращаем результат
                results = await cursor.fetchone()
                if results is not None:
                    return results[0]
                else:
                    return 0

    async def update_statistic(self, user_id, amount):
        async with aiosqlite.connect(self.db_path) as db:
            # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
            await db.execute('INSERT OR REPLACE INTO statistic (user_id, last_amount) VALUES (?, ?)', (user_id, amount))
            # Сохраняем изменения
            await db.commit()