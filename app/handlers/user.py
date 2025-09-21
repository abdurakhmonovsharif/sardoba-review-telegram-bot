import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.db import crud
from app.config import settings
from app.i18n import I18N
from app.keyboards import (
    branches_kb,
    contact_kb,
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
    text = State()    # 📝 matn, rasm, albom shu yerda
    phone = State()
    confirm = State()


async def get_t(session, tg_id: int):
    user = await crud.get_user_by_tg_id(session, tg_id)
    locale = (user.locale if user and user.locale else "uz")
    return I18N(locale).t


# 🚀 Start
@router.message(F.text == "/start")
async def start_cmd(msg: Message, state: FSMContext, session):
    await crud.upsert_user(session, msg.from_user.id, first_name=msg.from_user.first_name)
    await state.clear()
    t = I18N("uz").t
    await msg.answer(t("start.choose_lang", "Tilni tanlang / Выберите язык"), reply_markup=lang_kb(t))


# 🌐 Til tanlash
@router.callback_query(F.data.startswith("lang:"))
async def choose_lang(cb: CallbackQuery, state: FSMContext, session):
    locale = cb.data.split(":")[1]
    await crud.upsert_user(session, cb.from_user.id, locale=locale)
    t = I18N(locale).t

    user = await crud.get_user_by_tg_id(session, cb.from_user.id)

    # Agar telefon allaqachon bor bo‘lsa – faqat tilni almashtirish
    if user and user.phone:
        await cb.message.answer(t("lang.changed", "✅ Til o‘zgartirildi"),reply_markup=new_review_kb(t))
        await cb.message.delete()
        return

    # Yangi foydalanuvchi bo‘lsa → to‘liq start oqimi
    await cb.message.edit_text(t("start.hello", "Assalomu alaykum! Xush kelibsiz."))
    await cb.message.answer(
        t("ask.phone", "📞 Telefon raqamingizni yuboring:"),
        reply_markup=contact_kb(t),
    )
    await state.set_state(ReviewForm.phone)

# 📞 Telefon olish
@router.message(ReviewForm.phone, F.contact)
async def on_phone_contact(msg: Message, state: FSMContext, session):
    await crud.upsert_user(session, msg.from_user.id, phone=msg.contact.phone_number)
    t = await get_t(session, msg.from_user.id)
    locale = getattr(getattr(t, "__self__", None), "locale", "uz")
    await msg.answer(t("thank_you", "Rahmat ✅"), reply_markup=ReplyKeyboardRemove())

    branches = await crud.list_branches(session)
    if not branches:
        await msg.answer(t("branch.empty", "Hozircha filiallar yo‘q."))
        await state.clear()
        return

    await msg.answer(
        t("ask.branch", "Filialni tanlang:"),
        reply_markup=branches_kb(branches, locale=locale),
    )
    await state.set_state(ReviewForm.branch)


# 🏢 Filial tanlash
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


# ⭐ Reyting
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


# ✍️ Izoh (text + photo + album)
@router.callback_query(F.data == "add_text")
async def ask_text(cb: CallbackQuery, state: FSMContext, session):
    t = await get_t(session, cb.from_user.id)
    await cb.message.delete()
    await cb.message.answer(
        t("ask.review", "Sharh yozing (rasm yoki albom yuborishingiz ham mumkin)."),
        reply_markup=back_to_review_menu_kb(t)
    )
    await state.set_state(ReviewForm.text)


@router.message(ReviewForm.text)
async def handle_review_content(msg: Message, state: FSMContext, session):
    if msg.media_group_id:  
        return await save_album(msg, state, session)
    elif msg.photo:  
        return await save_single_photo(msg, state, session)
    elif msg.text: 
        return await save_text(msg, state, session)
    else: 
        t = await get_t(session, msg.from_user.id)
        await msg.answer(t("error.unsupported", "Faqat matn yoki rasm yuboring."))


async def save_text(msg: Message, state: FSMContext, session):
    await state.update_data(text=msg.text)
    t = await get_t(session, msg.from_user.id)
    await msg.answer(
        t("saved", "Sharhingiz qabul qilindi ✅"),
        reply_markup=review_menu_kb(t, can_submit=True)
    )
    await state.set_state(ReviewForm.confirm)


async def save_single_photo(msg: Message, state: FSMContext, session):
    data = await state.get_data()
    photos = data.get("photos", [])
    photos.append(msg.photo[-1].file_id)
    await state.update_data(photos=photos)

    t = await get_t(session, msg.from_user.id)
    await msg.answer(
        t("saved.photo", "📷 Rasm qabul qilindi ✅"),
        reply_markup=review_menu_kb(t, can_submit=True),
    )
    await state.set_state(ReviewForm.confirm)


album_buffer: dict[str, list[Message]] = {}

async def save_album(msg: Message, state: FSMContext, session):
    media_id = msg.media_group_id
    album_buffer.setdefault(media_id, []).append(msg)
    await asyncio.sleep(1)

    if album_buffer.get(media_id):
        messages = album_buffer.pop(media_id)
        file_ids = [m.photo[-1].file_id for m in messages if m.photo]

        data = await state.get_data()
        photos = data.get("photos", [])
        photos.extend(file_ids)
        await state.update_data(photos=photos)

        t = await get_t(session, msg.from_user.id)
        await msg.answer(
            t("saved.album", f"📷 {len(file_ids)} ta rasm qabul qilindi ✅"),
            reply_markup=review_menu_kb(t, can_submit=True),
        )
        await state.set_state(ReviewForm.confirm)


# 📷 Rasm tugmasi (xohlasa alohida rasm yuborishi uchun)
@router.callback_query(F.data == "add_photo")
async def ask_photo(cb: CallbackQuery, state: FSMContext, session):
    t = await get_t(session, cb.from_user.id)
    await cb.message.delete()
    await cb.message.answer(
        t("ask.photo", "Rasm yuboring (bir nechta rasm bo‘lishi mumkin):"),
        reply_markup=back_to_review_menu_kb(t)
    )
    await state.set_state(ReviewForm.text)  # 👈 universal handler ishlaydi


# ✅ Yakuniy yuborish
@router.callback_query(F.data == "submit_review")
async def submit_review(cb: CallbackQuery, state: FSMContext, session):
    data = await state.get_data()
    t = await get_t(session, cb.from_user.id)

    if not (data.get("rating") or data.get("text") or data.get("photos")):
        await cb.answer(t("review.submit.empty", "Kamida bittasini tanlang: Reyting, Izoh yoki Rasm."), show_alert=True)
        await cb.message.edit_text(
            t("ask.rating_or_review", "Baholash yoki sharh/rasm qoldiring:"),
            reply_markup=review_menu_kb(t, can_submit=False)
        )
        return

    user = await crud.get_user_by_tg_id(session, cb.from_user.id)
    if user is None:
        user = await crud.upsert_user(session, cb.from_user.id, first_name=cb.from_user.first_name)

    review = await crud.create_review(
        session,
        user_id=user.id,
        branch_id=data["branch_id"],
        rating=data.get("rating"),
        text=data.get("text"),
        photos=data.get("photos", [])
    )
    await state.clear()
    await cb.message.delete()
    await cb.message.answer(t("saved", "Rahmat! Sharhingiz saqlandi 🙏"))
    await crud.notify_superadmin_group(cb.bot, session, settings.SUPER_ADMINS[0], review)
    await cb.message.answer(
        t("ask.new_review", "Yangi sharh boshlash uchun tugmani bosing."),
        reply_markup=new_review_kb(t),
    )
    
# new review and change language 


# --- REPLY KEYBOARD HANDLERS ---
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
        await msg.answer(t("branch.empty", "Hozircha filiallar yo‘q."))
        return
    locale = getattr(getattr(t, "__self__", None), "locale", "uz")
    await msg.answer(
        t("ask.branch", "Filialni tanlang:"),
        reply_markup=branches_kb(branches, locale=locale),
    )
    await state.set_state(ReviewForm.branch)


@router.message(F.text.in_(_labels_new_review()))
async def on_new_review_label(msg: Message, state: FSMContext, session):
    await _start_new_review_flow(msg, state, session)


@router.message(F.text.in_(_labels_change_lang()))
async def on_change_lang_label(msg: Message, state: FSMContext, session):
    t = await get_t(session, msg.from_user.id)
    await msg.answer(
        t("start.choose_lang", "Tilni tanlang / Выберите язык"),
        reply_markup=lang_kb(t)
    )
