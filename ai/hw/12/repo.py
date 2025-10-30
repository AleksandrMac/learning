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
            try:
                await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
                # Сохраняем изменения
                await db.commit()
            except Exception as e:
                print(e)