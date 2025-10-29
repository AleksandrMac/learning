import aiosqlite

class QuizRepo:
    def __init__(self, db_name: str):        
        self.db = aiosqlite.connect(db_name)

    async def get_quiz_index(self, user_id):
        # Получаем запись для заданного пользователя
        async with self.db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


    async def update_quiz_index(self, user_id, index):
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await self.db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        # Сохраняем изменения
        await self.db.commit()