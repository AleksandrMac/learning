
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def generate_options_keyboard(answer_options: list[str] , query_index: int):
    builder = InlineKeyboardBuilder()   

    for key, option in enumerate(answer_options):
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data= f"opt:{query_index}:{key}")
        )

    builder.adjust(1)
    return builder.as_markup()

def start():    
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    return builder.as_markup(resize_keyboard=True)