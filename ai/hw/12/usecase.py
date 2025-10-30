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

    async def get_question(self, user_id, question_id=-1):
        # Получение текущего вопроса из словаря состояний пользователя
        if question_id == -1:
            question_id = await self.db.get_quiz_index(user_id)


        if question_id < len(quiz_data):
            quest = quiz_data[question_id]
            return quest['question'], quest['options'], quest['correct_option']

        return None, None, None

    async def new_quiz(self, user_id):
        await self.db.update_quiz_index(user_id, 0)

    async def get_quiz_index(self, user_id):
        return await self.db.get_quiz_index(user_id)
    
    async def quiz_index_add(self, user_id, inc=1):
        current_question_index = await self.db.get_quiz_index(user_id)
        # Обновление номера текущего вопроса в базе данных
        current_question_index += inc

        await self.db.update_quiz_index(user_id, current_question_index)
