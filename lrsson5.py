#
# CRUD
# Create - INSERT
# Read - SELECT
# Update - UPDATE
# Delete - DELETE
#
# SELECT * FROM servers — Все столбцы, все строки.
# SELECT name, status FROM servers — только нужные столбцы
# SELECT * FROM servers WHERE status = "мёртв" — фильтр
# SELECT * FROM servers WHERE type != 'web' — не равно
# SELECT * FROM servers WHERE name LIKE '%server%'; — поиск по подстроке
# SELECT * FROM servers WHERE status = 'жив' AND type = 'db' — несколько условий
# SELECT * FROM servers ORDER BY name — сортировка А->Я
# SELECT * FROM servers ORDER BY id DESC — сортировка по убыванию
# SELECT * FROM servers ORDER BY id ASC — сортировка по возрастанию
# ASC — Ascending — Восходящий, от меньшего к большему
# DESC — Descending — Нисходящий, от большего к меньшему
# SELECT * FROM servers LIMIT 2 — только первые 2 строки
#
# UPDATE servers SET status = 'мёртв' WHERE name = 'mail_server'
# UPDATE servers SET status = 'жив', type = 'db' WHERE id = 2
#
# DELETE FROM servers WHERE name = "mail_server"

import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

import db

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm_save")],
    [InlineKeyboardButton(text="❌ Отмена", callback_data="confirm_cancel")],
])

class AddServerStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_status = State()

@router.message(Command("add_server"))
async def add_server(message: Message, state: FSMContext):
    await message.answer("Введите имя нового сервера:")
    await state.set_state(AddServerStates.waiting_for_name)

@router.message(AddServerStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Тип сервера (web / db / backup):")
    await state.set_state(AddServerStates.waiting_for_type)

@router.message(AddServerStates.waiting_for_type)

async def process_type(message: Message, state: FSMContext):
    await state.update_data(type=message.text)
    await message.answer("Статус (жив / мёртв / в отпуске):")
    await state.set_sate(AddServerStates.waiting_for_status)

@router.message(AddServerStates.waiting_for_status)
async def process_status(message: Message, state: FSMContext):
    data = await state.update_data(status=message.text)
    await message.answer(
        f"Проверьте:\nИмя:{data['name']}\nТип: {data['type']}\nСтатус:{data['status']}",
        reply_markup = confirm_keyboard
    )

@router.callback_query(F.data == "confirm_save")
async def confirm_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        db.add_server(data["name"], data["type"], data["status"])
        await callback.message.edit_text("Сервер сохранён в реестре ✅")
    except Exception:
        await callback.message.edit_text("Сервер с таким именем уже существует ⚠️")
        await state.clear()
        await callback.answer()

@router.callback_query(F.data == "confirm_cancel")
async def confirm_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Добавление отменено ❌")
    await callback.answer()

@router.message(Command("list_servers"))
async def list_servers(message: Message):
    servers = db.get_all_servers()
    if not servers:
        await message.answer("Реестр пуст. Самое время добавить через /add_server.")
        return

    lines = [f"• {row['name']} ({row['type']}) — {row['status']}" for row in servers]
    await message.asnwer("Серверы в реестре:\n" + "\n".join(lines))

@router.message(Command("server"))
async def server(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Напишите так: /server имя сервера")
        return

    server = db.get_server_by_name(parts[1])
    if server is None:
        await message.answer(f"Сервер '{parts[1]}' не найден в реестре.")
        return

    await message.answer(
        f" 🖥️ {server['name']}\nТип: {server['type']}\nСтатус: {server['status']}"
    )
    
    @router.message(Command("update_status"))
    async def update_status(message: Message):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Напишите так:/update_status имя сервера новый статус")
            return 


        