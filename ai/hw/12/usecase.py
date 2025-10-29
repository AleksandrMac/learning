import repo
import ui
# Структура квиза
quiz_data = [
    {
        'question': 'Что такое Python?',
        'options': ['Язык программирования', 'Тип данных', 'Музыкальный инструмент', 'Змея на английском'],
        'correct_option': 0
    },
    {
        'question': 'Какой тип данных используется для хранения целых чисел?',
        'options': ['int', 'float', 'str', 'natural'],
        'correct_option': 0
    },
    # Добавьте другие вопросы
]

class QuizUseCase:    
    def __init__(self, db: repo.QuizRepo):        
        self.db = db

    async def get_question(self, message, user_id):
        # Получение текущего вопроса из словаря состояний пользователя
        current_question_index = await self.db.get_quiz_index(user_id)
        correct_index = quiz_data[current_question_index]['correct_option']
        opts = quiz_data[current_question_index]['options']
        kb = ui.generate_options_keyboard(opts, opts[correct_index])
        await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


    async def new_quiz(self, message):
        user_id = message.from_user.id
        current_question_index = 0
        await self.db.update_quiz_index(user_id, current_question_index)
        await self.get_question(message, user_id)

    async def get_quiz_index(self, user_id):
        return await self.db.get_quiz_index(user_id)
    
    async def update_quiz_index(self, user_id, index):
        await self.db.update_quiz_index(user_id, index)
    
    async def next(self, user_id):
        current_question_index = await self.db.get_quiz_index(user.id)
        # Обновление номера текущего вопроса в базе данных
        current_question_index += 1
        await uc.update_quiz_index(callback.from_user.id, current_question_index)


        if current_question_index < len(quiz_data):
            await uc.get_question(callback.message, callback.from_user.id)
        else:
            await callback.message.answer("Это был последний вопрос. Квиз завершен!")