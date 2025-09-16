from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.db import crud
from app.i18n import I18N
from app.keyboards import (
    branches_kb,
    review_menu_kb,
    rating_kb,
    lang_kb,
    back_to_review_menu_kb,
    new_review_kb,
)
router = Router()

class ReviewForm(StatesGroup):
    branch = State()
    rating = State()
    text = State()
    photo = State()
    confirm = State()
    confirm=State()


async def get_t(session, tg_id: int):
    """Fetch translator using user's saved locale (default 'uz')."""
    user = await crud.get_user_by_tg_id(session, tg_id)
    locale = (user.locale if user and user.locale else "uz")
    return I18N(locale).t


# Start: ask language first
@router.message(F.text == "/start")
async def start_cmd(msg: Message, state: FSMContext, session):
    await crud.upsert_user(session, msg.from_user.id, first_name=msg.from_user.first_name)
    await state.clear()
    t = I18N("uz").t
    await msg.answer(t("start.choose_lang", "Tilni tanlang / Выберите язык"), reply_markup=lang_kb(t))


@router.callback_query(F.data.startswith("lang:"))
async def choose_lang(cb: CallbackQuery, state: FSMContext, session):
    locale = cb.data.split(":")[1]
    await crud.upsert_user(session, cb.from_user.id, locale=locale)
    await state.update_data(locale=locale)
    t = I18N(locale).t
    await cb.message.edit_text(t("start.hello", "Assalomu alaykum! Xush kelibsiz."))

    branches = await crud.list_branches(session)
    if not branches:
        await cb.message.answer(t("branch.empty", "Hozircha filiallar ro‘yxati mavjud emas."))
        await state.clear()
        return
    await cb.message.answer(t("ask.branch", "Filialni tanlang:"), reply_markup=branches_kb(branches))
    await state.set_state(ReviewForm.branch)


# Filial tanlash
@router.callback_query(F.data.startswith("branch:"))
async def choose_branch(cb: CallbackQuery, state: FSMContext, session):
    branch_id = int(cb.data.split(":")[1])
    await state.update_data(branch_id=branch_id)
    t = await get_t(session, cb.from_user.id)

    await cb.message.delete()
    await cb.message.answer(
        t("ask.rating_or_review", "Baholash yoki sharh/rasm qoldiring:"),
        reply_markup=review_menu_kb(t, can_submit=False)
    )
    await state.set_state(ReviewForm.confirm)


# ⭐ Rating tanlash menyusi
@router.callback_query(F.data == "add_rating")
async def add_rating(cb: CallbackQuery, state: FSMContext, session):
    t = await get_t(session, cb.from_user.id)

    await cb.message.delete()
    await cb.message.answer("⭐ " + t("ask.rating", "Reyting tanlang:"), reply_markup=rating_kb())
    await state.set_state(ReviewForm.rating)


@router.callback_query(F.data.startswith("rate:"))
async def choose_rating(cb: CallbackQuery, state: FSMContext, session):
    rating = int(cb.data.split(":")[1])
    await state.update_data(rating=rating)
    t = await get_t(session, cb.from_user.id)

    await cb.message.delete()
    await cb.message.answer(
        f"{t('saved', 'Rahmat!')} ⭐ {rating}",
        reply_markup=review_menu_kb(t, can_submit=True)
    )
    await state.set_state(ReviewForm.confirm)


# ✍️ Izoh yozish
@router.callback_query(F.data == "add_text")
async def ask_text(cb: CallbackQuery, state: FSMContext, session):
    t = await get_t(session, cb.from_user.id)

    await cb.message.delete()
    await cb.message.answer(
        t("ask.review", "Sharh matnini yozing (rasm yuborishingiz mumkin)."),
        reply_markup=back_to_review_menu_kb(t)
    )
    await state.set_state(ReviewForm.text)


@router.message(ReviewForm.text)
async def save_text(msg: Message, state: FSMContext, session):
    await state.update_data(text=msg.text)
    t = await get_t(session, msg.from_user.id)

    await msg.answer(
        t("saved", "Sharhingiz qabul qilindi ✅"),
        reply_markup=review_menu_kb(t, can_submit=True)
    )
    await state.set_state(ReviewForm.confirm)


# 📷 Rasm yuborish
@router.callback_query(F.data == "add_photo")
async def ask_photo(cb: CallbackQuery, state: FSMContext, session):
    t = await get_t(session, cb.from_user.id)

    await cb.message.delete()
    await cb.message.answer(
        t("ask.photo", "Rasm yuboring:"),
        reply_markup=back_to_review_menu_kb(t)
    )
    await state.set_state(ReviewForm.photo)


@router.message(ReviewForm.photo, F.photo)
async def save_photo(msg: Message, state: FSMContext, session):
    file_id = msg.photo[-1].file_id
    await state.update_data(photo=file_id)
    t = await get_t(session, msg.from_user.id)

    await msg.answer(
        t("saved", "📷 Rasm qabul qilindi ✅"),
        reply_markup=review_menu_kb(t, can_submit=True)
    )
    await state.set_state(ReviewForm.photo)

# ✅ Yuborish (yakuniy)
@router.callback_query(F.data == "submit_review")
async def submit_review(cb: CallbackQuery, state: FSMContext, session):
    data = await state.get_data()
    t = await get_t(session, cb.from_user.id)

    # Validate: require at least one of rating, text, photo
    if not (data.get("rating") or data.get("text") or data.get("photo")):
        await cb.answer(t("review.submit.empty", "Kamida bittasini tanlang: Reyting, Izoh yoki Rasm."), show_alert=True)
        # Refresh review menu without submit button
        await cb.message.edit_text(
            t("ask.rating_or_review", "Baholash yoki sharh/rasm qoldiring:"),
            reply_markup=review_menu_kb(t, can_submit=False)
        )
        return

    # Ensure user exists and use DB primary key for FK
    user = await crud.get_user_by_tg_id(session, cb.from_user.id)
    if user is None:
        user = await crud.upsert_user(session, cb.from_user.id, first_name=cb.from_user.first_name)

    review = await crud.create_review(
        session,
        user_id=user.id,
        branch_id=data["branch_id"],
        rating=data.get("rating"),
        text=data.get("text"),
        photo_file_id=data.get("photo"),
    )
    await state.clear()
    await cb.message.delete()
    await cb.message.answer(t("saved", "Rahmat! Sharhingiz saqlandi 🙏"))
    # Notify group
    await crud.notify_new_review(session, review, bot=cb.bot)
    # Offer to start a new review with a localized command button
    await cb.message.answer(
        t("ask.new_review", "Yangi sharh boshlash uchun tugmani bosing."),
        reply_markup=new_review_kb(t),
    )

def _labels_new_review() -> set[str]:
    return {
        I18N("uz").t("kb.new_review", "🆕 Yangi sharh"),
        I18N("ru").t("kb.new_review", "🆕 Новый отзыв"),
    }


def _labels_change_lang() -> set[str]:
    return {
        I18N("uz").t("kb.change_lang", "🌐 Tilni o'zgartirish"),
        I18N("ru").t("kb.change_lang", "🌐 Изменить язык"),
    }


async def _start_new_review_flow(msg: Message, state: FSMContext, session):
    t = await get_t(session, msg.from_user.id)
    await state.clear()
    branches = await crud.list_branches(session)
    if not branches:
        await msg.answer(t("branch.empty", "Hozircha filiallar ro‘yxati mavjud emas."))
        return
    await msg.answer(t("ask.branch", "Filialni tanlang:"), reply_markup=branches_kb(branches))
    await state.set_state(ReviewForm.branch)


@router.message(F.text.in_(_labels_new_review()))
async def on_new_review_label(msg: Message, state: FSMContext, session):
    await _start_new_review_flow(msg, state, session)


@router.message(F.text.in_(_labels_change_lang()))
async def on_change_lang_label(msg: Message, state: FSMContext, session):
    t = await get_t(session, msg.from_user.id)
    await msg.answer(t("start.choose_lang", "Tilni tanlang / Выберите язык"), reply_markup=lang_kb(t))


# Keep slash commands for compatibility
@router.message(F.text == "/yangi_sharh")
async def new_review_uz(msg: Message, state: FSMContext, session):
    await _start_new_review_flow(msg, state, session)


@router.message(F.text == "/novyy_otzyv")
async def new_review_ru(msg: Message, state: FSMContext, session):
    await _start_new_review_flow(msg, state, session)

# Back from rating to review menu
@router.callback_query(F.data == "go_back_choose_review")
async def go_back_choose_review(cb: CallbackQuery, state: FSMContext, session):
    t = await get_t(session, cb.from_user.id)
    data = await state.get_data()
    can_submit = bool(data.get("rating") or data.get("text") or data.get("photo"))
    await cb.message.delete()
    await cb.message.answer(
        t("ask.rating_or_review", "Baholash yoki sharh/rasm qoldiring:"),
        reply_markup=review_menu_kb(t, can_submit=can_submit)
    )
    await state.set_state(ReviewForm.confirm)

# Back from review menu to branch selection
@router.callback_query(F.data == "go_back_choose_branch")
async def go_back_choose_branch(cb: CallbackQuery, state: FSMContext, session):
    t = await get_t(session, cb.from_user.id)
    branches = await crud.list_branches(session)
    await cb.message.delete()
    await cb.message.answer(t("ask.branch", "Filialni tanlang:"), reply_markup=branches_kb(branches))
    await state.set_state(ReviewForm.branch)
@router.message(F.text == "/yangi_sharh")
async def new_review_uz(msg: Message, state: FSMContext, session):
    t = await get_t(session, msg.from_user.id)
    await state.clear()
    branches = await crud.list_branches(session)
    if not branches:
        await msg.answer(t("branch.empty", "Hozircha filiallar ro‘yxati mavjud emas."))
        return
    await msg.answer(t("ask.branch", "Filialni tanlang:"), reply_markup=branches_kb(branches))
    await state.set_state(ReviewForm.branch)


@router.message(F.text == "/novyy_otzyv")
async def new_review_ru(msg: Message, state: FSMContext, session):
    t = await get_t(session, msg.from_user.id)
    await state.clear()
    branches = await crud.list_branches(session)
    if not branches:
        await msg.answer(t("branch.empty", "Пока список филиалов недоступен."))
        return
    await msg.answer(t("ask.branch", "Выберите филиал:"), reply_markup=branches_kb(branches))
    await state.set_state(ReviewForm.branch)
