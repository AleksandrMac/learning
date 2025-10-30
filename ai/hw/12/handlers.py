from aiogram import Dispatcher, types, F
from aiogram.filters.command import Command
import asyncio

import ui
import usecase



def dispatcher(uc: usecase.QuizUseCase):
    # Диспетчер
    dp = Dispatcher()
    
    async def send_next_question_or_finish(user_id: int, message: types.Message, question_id = -1):
        quest, opts, correct, question_id = await uc.get_question(user_id, question_id)
        if quest is None:
            await uc.update_statistic(user_id, uc.amount)
            return await message.answer("Это был последний вопрос. Квиз завершен!")
        kb = ui.generate_options_keyboard(opts, question_id)
        return await message.answer(quest, reply_markup=kb)
    
    async def check_answer(user_id: int, callback: types.CallbackQuery):
        data = callback.data
        _, q_index, selected_option = data.split(":")

        if uc.check_answer(int(q_index), int(selected_option)):
            await callback.message.answer("Верно!")
            uc.amount_add(1)
        else:
            # Получаем текущий вопрос (до увеличения индекса!)
            _, opts, correct_idx, _ = await uc.get_question(user_id)
            await callback.message.answer(f"Неправильно. Правильный ответ: {opts[correct_idx]}")

    async def print_answer(callback: types.CallbackQuery):
        data = callback.data
        _, q_index, selected_option = data.split(":")
        option_text = uc.getOptionsById(int(q_index), int(selected_option))
        return await callback.message.answer(f"Ваш ответ: {option_text}")

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

        # Хэндлер на команду /quiz
    @dp.message(F.text=="Статистика")
    @dp.message(Command("statistic"))
    async def cmd_statistic(message: types.Message):
        user_id = message.from_user.id
        amount = await uc.get_statistic(user_id)
        stats_text = f"Ваш последний результат: {amount} из 10"
        await message.answer(stats_text)


    @dp.callback_query(F.data.startswith("opt:"))
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
        await print_answer(callback)

        # Переходим к следующему вопросу
        await uc.quiz_index_add(user_id)
        await send_next_question_or_finish(user_id, callback.message)

    return dp


