from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db import crud

router = Router()

class ReviewForm(StatesGroup):
    branch = State()
    rating = State()
    text = State()
    photo = State()

@router.message(F.text == "/start")
async def start_cmd(msg: Message, state: FSMContext, session):
    user = await crud.upsert_user(session, msg.from_user.id, first_name=msg.from_user.first_name)
    await msg.answer("Assalomu alaykum! Filialni tanlang:")
    branches = await crud.list_branches(session)
    kb = InlineKeyboardBuilder()
    for b in branches:
        kb.button(text=b.name, callback_data=f"branch:{b.id}")
    await msg.answer("Filiallar:", reply_markup=kb.as_markup())
    await state.set_state(ReviewForm.branch)

@router.callback_query(F.data.startswith("branch:"))
async def choose_branch(cb: CallbackQuery, state: FSMContext):
    branch_id = int(cb.data.split(":")[1])
    await state.update_data(branch_id=branch_id)
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"rate:{i}")
    await cb.message.answer("Reyting tanlang:", reply_markup=kb.as_markup())
    await state.set_state(ReviewForm.rating)

@router.callback_query(F.data.startswith("rate:"))
async def choose_rating(cb: CallbackQuery, state: FSMContext):
    rating = int(cb.data.split(":")[1])
    await state.update_data(rating=rating)
    await cb.message.answer("Sharhingizni yozing (rasm ham yuborishingiz mumkin):")
    await state.set_state(ReviewForm.text)

@router.message(ReviewForm.text)
async def save_text(msg: Message, state: FSMContext):
    await state.update_data(text=msg.text)
    await msg.answer("Agar rasm yubormoqchi bo‘lsangiz yuboring, aks holda /skip bosing.")
    await state.set_state(ReviewForm.photo)

@router.message(ReviewForm.photo, F.photo)
async def save_photo(msg: Message, state: FSMContext, session):
    data = await state.get_data()
    file_id = msg.photo[-1].file_id
    await crud.create_review(
        session,
        user_id=msg.from_user.id,
        branch_id=data["branch_id"],
        rating=data["rating"],
        text=data.get("text"),
        photo_file_id=file_id,
    )
    await msg.answer("Rahmat! Sharhingiz qabul qilindi.")
    await state.clear()

@router.message(ReviewForm.photo, F.text == "/skip")
async def skip_photo(msg: Message, state: FSMContext, session):
    data = await state.get_data()
    await crud.create_review(
        session,
        user_id=msg.from_user.id,
        branch_id=data["branch_id"],
        rating=data["rating"],
        text=data.get("text"),
        photo_file_id=None,
    )
    await msg.answer("Rahmat! Sharhingiz qabul qilindi.")
    await state.clear()