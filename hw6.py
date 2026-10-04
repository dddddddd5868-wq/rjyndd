import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Токен бота хранится в переменной окружения BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
  raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

# Настройка базы данных SQLite
conn = sqlite3.connect("schedule.db")
cursor = conn.cursor()
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT,
    subject TEXT,
    time TEXT,
    cabinet TEXT
)
"""
)
conn.commit()

router = Router()


# Состояния FSM для добавления занятия
class AddLesson(StatesGroup):
    day = State()
    subject = State()
    time = State()
    cabinet = State()


# Дни недели для кнопок
DAYS = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]


def get_days_keyboard():
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text=day, callback_data=f"day_{day}")]
          for day in DAYS
      ]
  )
  return keyboard


# Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message):
  kb = [
      [
          InlineKeyboardButton(
              text="➕ Добавить занятие", callback_data="add_lesson"
          )
      ],
      [
          InlineKeyboardButton(
              text="📋 Показать расписание", callback_data="show_all"
          )
      ],
      [
          InlineKeyboardButton(
              text="📅 Выбрать день", callback_data="select_day"
          )
      ],
      [
          InlineKeyboardButton(
              text="🗑 Удалить занятие", callback_data="delete_lesson"
          )
      ],
  ]
  keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
  await message.answer(
      "Привет! Я бот для управления расписанием. Выберите действие:",
      reply_markup=keyboard,
  )


# --- 1. ДОБАВИТЬ ЗАНЯТИЕ (FSM) ---
@router.callback_query(F.data == "add_lesson")
async def start_add(callback: CallbackQuery, state: FSMContext):
  await callback.message.answer("Введите день недели (например, Понедельник):")
  await state.set_state(AddLesson.day)
  await callback.answer()


@router.message(AddLesson.day)
async def process_day(message: Message, state: FSMContext):
  await state.update_data(day=message.text)
  await message.answer("Введите название предмета:")
  await state.set_state(AddLesson.subject)


@router.message(AddLesson.subject)
async def process_subject(message: Message, state: FSMContext):
  await state.update_data(subject=message.text)
  await message.answer("Введите время (например, 09:00):")
  await state.set_state(AddLesson.time)


@router.message(AddLesson.time)
async def process_time(message: Message, state: FSMContext):
  await state.update_data(time=message.text)
  await message.answer("Введите кабинет (например, 305):")
  await state.set_state(AddLesson.cabinet)


@router.message(AddLesson.cabinet)
async def process_cabinet(message: Message, state: FSMContext):
  user_data = await state.get_data()

  # Сохранение в базу данных (INSERT)
  cursor.execute(
      "INSERT INTO schedule (day, subject, time, cabinet) VALUES (?, ?, ?, ?)",
      (
          user_data["day"],
          user_data["subject"],
          user_data["time"],
          message.text,
      ),
  )
  conn.commit()

  await message.answer("✅ Занятие успешно добавлено!")
  await state.clear()


# --- 2. ПОКАЗАТЬ РАСПИСАНИЕ ---
@router.callback_query(F.data == "show_all")
async def show_schedule(callback: CallbackQuery):
  cursor.execute("SELECT id, day, subject, time, cabinet FROM schedule")
  rows = cursor.fetchall()

  if not rows:
    await callback.message.answer("Расписание пока пусто.")
    await callback.answer()
    return

  text = "📋 **Все расписание:**\n\n"
  for row in rows:
    text += f"ID: {row[0]} | {row[1]} — {row[2]} в {row[3]} (каб. {row[4]})\n"

  await callback.message.answer(text, parse_mode="Markdown")
  await callback.answer()


# --- 3. ВЫБРАТЬ ДЕНЬ ---
@router.callback_query(F.data == "select_day")
async def select_day_menu(callback: CallbackQuery):
  await callback.message.answer(
      "Выберите день недели:", reply_markup=get_days_keyboard()
  )
  await callback.answer()


@router.callback_query(F.data.startswith("day_"))
async def show_day_schedule(callback: CallbackQuery):
  day = callback.data.split("_")[1]
  cursor.execute(
      "SELECT subject, time, cabinet FROM schedule WHERE day = ?", (day,)
  )
  rows = cursor.fetchall()

  if not rows:
    await callback.message.answer(f"На день ({day}) занятий нет.")
    await callback.answer()
    return

  text = f"📅 **Расписание на {day}:**\n\n"
  for row in rows:
    text += f"• {row[0]} — {row[1]} (каб. {row[2]})\n"

  await callback.message.answer(text, parse_mode="Markdown")
  await callback.answer()


# --- 4. УДАЛИТЬ ЗАНЯТИЕ ---
@router.callback_query(F.data == "delete_lesson")
async def delete_menu(callback: CallbackQuery):
  cursor.execute("SELECT id, day, subject, time FROM schedule")
  rows = cursor.fetchall()

  if not rows:
    await callback.message.answer("Нет занятий для удаления.")
    await callback.answer()
    return

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text=f"Удалить: {row[1]} | {row[2]} ({row[3]})",
                  callback_data=f"del_{row[0]}",
              )
          ]
          for row in rows
      ]
  )
  await callback.message.answer(
      "Выберите занятие для удаления:", reply_markup=keyboard
  )
  await callback.answer()


@router.callback_query(F.data.startswith("del_"))
async def process_delete(callback: CallbackQuery):
  lesson_id = callback.data.split("_")[1]
  cursor.execute("DELETE FROM schedule WHERE id = ?", (lesson_id,))
  conn.commit()

  await callback.message.answer("🗑 Занятие успешно удалено!")
  await callback.answer()


# Запуск бота
async def main():
  bot = Bot(token=TOKEN)
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)

  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())