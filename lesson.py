import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message


TOKEN = "BOT_TOKEN"


bot = Bot(token=TOKEN)
dp = Dispatcher()


keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🐍 Python", callback_data="btn_python"
            )
        ],
        [InlineKeyboardButton(text="📱 SQL", callback_data="btn_sql")],
        [InlineKeyboardButton(text="🐧 Linux", callback_data="btn_linux")],
    ]
)



@dp.message(CommandStart())
async def cmd_start(message: Message):
  await message.answer(
      "🧠 Выберите тему:", reply_markup=keyboard
  )



@dp.callback_query(
    F.data.in_(["btn_python", "btn_sql", "btn_linux"])
)
async def process_callback(callback: CallbackQuery):
  
  if callback.data == "btn_python":
    await callback.message.answer(
        "🐍 Python — популярный язык программирования общего назначения."
    )
  elif callback.data == "btn_sql":
    await callback.message.answer(
        "📱 SQL — язык для работы с базами данных."
    )
  elif callback.data == "btn_linux":
    await callback.message.answer(
        "🐧 Linux — операционная система с открытым исходным кодом."
    )

  
  await callback.answer()



async def main():
  logging.basicConfig(
      level=logging.INFO, stream=sys.stdout
  )
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())


