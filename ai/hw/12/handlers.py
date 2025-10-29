import asyncio
from aiogram import Dispatcher, types, Bot
from aiogram.filters.command import Command

import ui
import usecase




def dispatcher(uc: usecase.QuizUseCase):
    # Диспетчер
    dp = Dispatcher()
    # Объект бота
    bot = Bot(token=API_TOKEN)

    # Хэндлер на команду /start
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer("Добро пожаловать в квиз!", reply_markup=ui.start())
    
    # Хэндлер на команду /quiz
    @dp.message(F.text=="Начать игру")
    @dp.message(Command("quiz"))
    async def cmd_quiz(message: types.Message):

        await message.answer(f"Давайте начнем квиз!")
        await uc.new_quiz(message)

    @dp.callback_query(F.data == "right_answer")
    async def right_answer(callback: types.CallbackQuery):

        await callback.bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )

        await callback.message.answer("Верно!")
        await callback.message.answer(uc.next(callback.from_user.id))
        # current_question_index = await uc.get_quiz_index(callback.from_user.id)
        # # Обновление номера текущего вопроса в базе данных
        # current_question_index += 1
        # await uc.update_quiz_index(callback.from_user.id, current_question_index)


        # if current_question_index < len(quiz_data):
        #     await uc.get_question(callback.message, callback.from_user.id)
        # else:
        #     await callback.message.answer("Это был последний вопрос. Квиз завершен!")


    @dp.callback_query(F.data == "wrong_answer")
    async def wrong_answer(callback: types.CallbackQuery):
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )

        # Получение текущего вопроса из словаря состояний пользователя
        current_question_index = await uc.get_quiz_index(callback.from_user.id)
        correct_option = quiz_data[current_question_index]['correct_option']

        await callback.message.answer(f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

        # Обновление номера текущего вопроса в базе данных
        current_question_index += 1
        await uc.update_quiz_index(callback.from_user.id, current_question_index)


        if current_question_index < len(quiz_data):
            await uc.get_question(callback.message, callback.from_user.id)
        else:
            await callback.message.answer("Это был последний вопрос. Квиз завершен!")



    return dp


