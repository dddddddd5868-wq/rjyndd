import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from dotenv import load_dotenv
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

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
  raise RuntimeError("BOT_TOKEN не найден в файле .env")
PROXY_URL = os.getenv("BOT_PROXY")

# Настройка базы данных SQLite
conn = sqlite3.connect("finance.db")
cursor = conn.cursor()
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    op_type TEXT,
    category TEXT,
    amount REAL,
    date TEXT
)
"""
)
conn.commit()

router = Router()


# Состояния FSM для добавления транзакции
class FinanceState(StatesGroup):
  op_type = State()
  category = State()
  amount = State()


# Главное меню
@router.message(Command("start"))
async def cmd_start(message: Message):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="➕ Добавить запись", callback_data="add_tx"
              )
          ],
          [
              InlineKeyboardButton(
                  text="📋 Все операции", callback_data="show_all"
              )
          ],
          [
              InlineKeyboardButton(
                  text="🔍 Фильтр (Доходы/Расходы)", callback_data="filter_menu"
              )
          ],
          [
              InlineKeyboardButton(
                  text="🗑 Удалить запись", callback_data="delete_menu"
              )
          ],
      ]
  )
  await message.answer(
      "Привет! Я твой личный финансовый бот. Выбери действие:",
      reply_markup=keyboard,
  )


# --- 1. ДОБАВИТЬ ЗАПИСЬ (FSM) ---
@router.callback_query(F.data == "add_tx")
async def start_add_tx(callback: CallbackQuery, state: FSMContext):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📉 Расход", callback_data="type_Расход"
              ),
              InlineKeyboardButton(text="📈 Доход", callback_data="type_Доход"),
          ]
      ]
  )
  await callback.message.answer(
      "Выберите тип операции:", reply_markup=keyboard
  )
  await state.set_state(FinanceState.op_type)
  await callback.answer()


@router.callback_query(FinanceState.op_type, F.data.startswith("type_"))
async def process_op_type(callback: CallbackQuery, state: FSMContext):
  op_type = callback.data.split("_")[1]
  await state.update_data(op_type=op_type)
  await callback.message.answer(
      "Введите категорию (например, Еда, Зарплата, Транспорт):"
  )
  await state.set_state(FinanceState.category)
  await callback.answer()


@router.message(FinanceState.category)
async def process_category(message: Message, state: FSMContext):
  await state.update_data(category=message.text)
  await message.answer("Введите сумму (числом, например, 500 или 1500.50):")
  await state.set_state(FinanceState.amount)


@router.message(FinanceState.amount)
async def process_amount(message: Message, state: FSMContext):
  try:
    amount = float(message.text.replace(",", "."))
  except ValueError:
    await message.answer("Пожалуйста, введите корректное число для суммы.")
    return

  user_data = await state.get_data()
  from datetime import datetime

  current_date = datetime.now().strftime("%Y-%m-%d %H:%M")

  # Сохранение в базу данных (INSERT)
  cursor.execute(
      "INSERT INTO transactions (op_type, category, amount, date) VALUES (?,"
      " ?, ?, ?)",
      (user_data["op_type"], user_data["category"], amount, current_date),
  )
  conn.commit()

  await message.answer("✅ Запись успешно сохранена!")
  await state.clear()


# --- 2. ПОКАЗАТЬ ВСЕ ОПЕРАЦИИ ---
@router.callback_query(F.data == "show_all")
async def show_all_tx(callback: CallbackQuery):
  cursor.execute(
      "SELECT id, op_type, category, amount, date FROM transactions"
  )
  rows = cursor.fetchall()

  if not rows:
    await callback.message.answer("Список операций пока пуст.")
    await callback.answer()
    return

  text = "📋 **История всех операций:**\n\n"
  for row in rows:
    emoji = "📈" if row[1] == "Доход" else "📉"
    text += (
        f"{emoji} ID: {row[0]} | {row[1]} | {row[2]} — {row[3]} сом ({row[4]})\n"
    )

  await callback.message.answer(text, parse_mode="Markdown")
  await callback.answer()


# --- 3. ФИЛЬТР (ДОХОДЫ / РАСХОДЫ) ---
@router.callback_query(F.data == "filter_menu")
async def filter_menu(callback: CallbackQuery):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📉 Только расходы", callback_data="filter_Расход"
              ),
              InlineKeyboardButton(
                  text="📈 Только доходы", callback_data="filter_Доход"
              ),
          ]
      ]
  )
  await callback.message.answer(
      "Выберите категорию для фильтрации:", reply_markup=keyboard
  )
  await callback.answer()


@router.callback_query(F.data.startswith("filter_"))
async def show_filtered(callback: CallbackQuery):
  f_type = callback.data.split("_")[1]
  cursor.execute(
      "SELECT category, amount, date FROM transactions WHERE op_type = ?",
      (f_type,),
  )
  rows = cursor.fetchall()

  if not rows:
    await callback.message.answer(f"Нет записей по типу: {f_type}")
    await callback.answer()
    return

  text = f"🔍 **Отчет: {f_type}**\n\n"
  total = 0
  for row in rows:
    text += f"• {row[0]} — {row[1]} сом ({row[2]})\n"
    total += row[1]

  text += f"\n**Итого:** {total} сом"
  await callback.message.answer(text, parse_mode="Markdown")
  await callback.answer()


# --- 4. УДАЛЕНИЕ ЗАПИСИ ---
@router.callback_query(F.data == "delete_menu")
async def delete_menu(callback: CallbackQuery):
  cursor.execute("SELECT id, op_type, category, amount FROM transactions")
  rows = cursor.fetchall()

  if not rows:
    await callback.message.answer("Нет записей для удаления.")
    await callback.answer()
    return

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text=f"Удалить ID {row[0]}: {row[2]} ({row[3]} сом)",
                  callback_data=f"del_{row[0]}",
              )
          ]
          for row in rows
      ]
  )
  await callback.message.answer(
      "Выберите запись для удаления:", reply_markup=keyboard
  )
  await callback.answer()


@router.callback_query(F.data.startswith("del_"))
async def process_delete(callback: CallbackQuery):
  tx_id = callback.data.split("_")[1]
  cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
  conn.commit()

  await callback.message.answer("🗑 Запись успешно удалена!")
  await callback.answer()


# Запуск бота
async def main():
  session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
  bot = Bot(token=TOKEN, session=session)
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)

  try:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
  except TelegramNetworkError:
    logging.error(
      "Не удалось подключиться к Telegram API. "
      "Проверьте интернет или задайте BOT_PROXY в файле .env."
    )
  finally:
    await bot.session.close()


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())