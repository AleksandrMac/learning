import repo
import question

class QuizUseCase:    
    def __init__(self, db: repo.QuizRepo):        
        self.db = db
        self.dataset = question.quiz_data
        self.amount = 0

    async def get_question(self, user_id, question_id=-1):
        # Получение текущего вопроса из словаря состояний пользователя
        if question_id == -1:
            question_id = await self.db.get_quiz_index(user_id)


        if question_id < len(self.dataset):
            quest = self.dataset[question_id]
            return quest['question'], quest['options'], quest['correct_option'], question_id

        return None, None, None, None

    async def new_quiz(self, user_id):
        self.amount_reset()
        await self.db.update_quiz_index(user_id, 0)

    async def get_quiz_index(self, user_id):
        return await self.db.get_quiz_index(user_id)
    
    async def quiz_index_add(self, user_id, inc=1):
        current_question_index = await self.db.get_quiz_index(user_id)
        # Обновление номера текущего вопроса в базе данных
        current_question_index += inc

        await self.db.update_quiz_index(user_id, current_question_index)

    def check_answer(self, question_id: int, selected_option: int) -> bool:
        quest = self.dataset[question_id]
        correct_option = quest['correct_option']
        return selected_option == correct_option
    
    def getOptionsById(self, question_id: int, option_id: int) -> str:
        quest = self.dataset[question_id]
        return quest['options'][option_id]
    
    async def get_statistic(self, user_id):
        return await self.db.get_statistic(user_id)
    
    async def update_statistic(self, user_id, amount):
        await self.db.update_statistic(user_id, amount)
    
    def amount_add(self, inc=1):
        self.amount += inc

    def amount_reset(self):
        self.amount = 0
