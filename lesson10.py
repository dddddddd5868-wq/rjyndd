import asyncio
import logging
import os
import sqlite3
import sys
from pathlib import Path
from aiogram import Bot, Dispatcher, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

def load_token() -> str:
  token = os.getenv("BOT_TOKEN")
  if token:
    return token

  env_file = Path(__file__).resolve().parent / ".env"
  if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
      key, separator, value = line.partition("=")
      if separator and key.strip() == "BOT_TOKEN":
        token = value.strip().strip("\"'")
        if token:
          return token

  raise RuntimeError(
      "BOT_TOKEN не задан. Добавьте его в переменную окружения "
      "или в файл .env рядом с lesson10.py."
  )


TOKEN = load_token()

# Инициализация базы данных SQLite
def init_db():
  conn = sqlite3.connect("students.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age TEXT,
            city TEXT
        )
    """)
  conn.commit()
  conn.close()

init_db()

# Определение состояний FSM для добавления студента
class StudentState(StatesGroup):
  waiting_for_name = State()
  waiting_for_age = State()
  waiting_for_city = State()

dp = Dispatcher()

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
  await message.answer(
      f"Привет, {html.bold(message.from_user.full_name)}! "
      "Я бот для учета студентов.\n\n"
      "Команды:\n"
      "/add — Добавить студента\n"
      "/list — Показать список студентов"
  )

# Шаг 1: Запуск добавления студента (FSM)
@dp.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
  await state.set_state(StudentState.waiting_for_name)
  await message.answer("Введите имя студента:")

# Шаг 2: Получение имени и переход к возрасту
@dp.message(StudentState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
  await state.update_data(name=message.text)
  await state.set_state(StudentState.waiting_for_age)
  await message.answer("Введите возраст студента:")

# Шаг 3: Получение возраста и переход к городу
@dp.message(StudentState.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
  await state.update_data(age=message.text)
  await state.set_state(StudentState.waiting_for_city)
  await message.answer("Введите город студента:")

# Шаг 4: Получение города и сохранение в SQLite
@dp.message(StudentState.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
  await state.update_data(city=message.text)
  data = await state.get_data()

  # Сохраняем в базу данных
  conn = sqlite3.connect("students.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO students (name, age, city) VALUES (?, ?, ?)",
      (data["name"], data["age"], data["city"]),
  )
  conn.commit()
  conn.close()

  await message.answer(
      f"✅ Студент успешно добавлен!\n"
      f"Имя: {data['name']}\n"
      f"Возраст: {data['age']}\n"
      f"Город: {data['city']}"
  )
  await state.clear()

# Просмотр списка студентов с Inline-кнопками для удаления
@dp.message(Command("list"))
async def cmd_list(message: Message):
  conn = sqlite3.connect("students.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, age, city FROM students")
  students = cursor.fetchall()
  conn.close()

  if not students:
    await message.answer("Список студентов пока пуст.")
    return

  for student in students:
    student_id, name, age, city = student
    # Создаем Inline-кнопку для удаления конкретного студента
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=f"🗑 Удалить {name}", callback_data=f"del_{student_id}"
            )
        ]]
    )
    await message.answer(
        f"👤 <b>{name}</b>\nВозраст: {age}\nГород: {city}",
        reply_markup=keyboard,
    )

# Обработка Callback-запроса от Inline-кнопки (удаление)
@dp.callback_query(F.data.startswith("del_"))
async def process_delete_callback(callback: CallbackQuery):
  # Извлекаем ID студента из callback_data (например, "del_5" -> 5)
  student_id = int(callback.data.split("_")[1])

  conn = sqlite3.connect("students.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
  conn.commit()
  conn.close()

  # Уведомляем пользователя и удаляем сообщение с кнопкой
  await callback.answer("Студент удален из базы!")
  await callback.message.edit_text("❌ Студент был удален.")

# Запуск бота
async def main():
  bot = Bot(
      token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
  )
  await dp.start_polling(bot)

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  asyncio.run(main())