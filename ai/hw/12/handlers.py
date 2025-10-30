from aiogram import Dispatcher, types, F
from aiogram.filters.command import Command

import ui
import usecase



def dispatcher(uc: usecase.QuizUseCase):
    # Диспетчер
    dp = Dispatcher()
    
    async def send_next_question_or_finish(user_id: int, message: types.Message, question_id = -1):
        quest, opts, correct = await uc.get_question(user_id, question_id)
        if quest is None:
            return await message.answer("Это был последний вопрос. Квиз завершен!")
        kb = ui.generate_options_keyboard(opts, opts[correct])
        return await message.answer(quest, reply_markup=kb)
    
    async def check_answer(user_id: int, callback: types.CallbackQuery):
        is_correct = callback.data == "right_answer"

        if is_correct:
            await callback.message.answer("Верно!")
        else:
            # Получаем текущий вопрос (до увеличения индекса!)
            _, opts, correct_idx = await uc.get_question(user_id)
            await callback.message.answer(f"Неправильно. Правильный ответ: {opts[correct_idx]}")

    # Хэндлер на команду /start
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer("Добро пожаловать в квиз!", reply_markup=ui.start())
    
    # Хэндлер на команду /quiz
    @dp.message(F.text=="Начать игру")
    @dp.message(Command("quiz"))
    async def cmd_quiz(message: types.Message):

        user_id = message.from_user.id

        await message.answer(f"Давайте начнем квиз!")
        await uc.new_quiz(user_id)        
        await send_next_question_or_finish(user_id, message, 0)

    @dp.callback_query(F.data.in_({"right_answer", "wrong_answer"}))
    async def handle_quiz_answer(callback: types.CallbackQuery):

        user_id     = callback.from_user.id
        message_id  = callback.message.message_id

         # Убираем кнопки у предыдущего сообщения
        await callback.bot.edit_message_reply_markup(
            chat_id         = user_id,
            message_id      = message_id,
            reply_markup    = None
        )

        await check_answer(user_id, callback)

        # Переходим к следующему вопросу
        await uc.quiz_index_add(user_id)
        await send_next_question_or_finish(user_id, callback.message)

    return dp


