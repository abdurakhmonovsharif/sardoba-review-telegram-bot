from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder,InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import KeyboardButton, ReplyKeyboardRemove
from typing import Callable
from app.i18n import I18N


def lang_kb(t: Callable[[str, str], str]):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("lang.uz", "🇺🇿 O'zbekcha"), callback_data="lang:uz")
    kb.button(text=t("lang.ru", "🇷🇺 Русский"), callback_data="lang:ru")
    kb.adjust(2)
    return kb.as_markup()


def contact_kb(t: Callable[[str, str], str]):
    label = t("kb.contact", "📞 Kontaktni yuborish")
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text=label, request_contact=True))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def branches_kb(branches: list, locale: str = "uz"):
    kb = InlineKeyboardBuilder()
    for b in branches:
        if locale == "ru":
            label = b.nameru or b.nameuz
        else:
            label = b.nameuz or b.nameru
        label = label or f"#{b.id}"
        kb.button(text=label, callback_data=f"branch:{b.id}")
    kb.adjust(1)
    return kb.as_markup()

def review_menu_kb(
    t: Callable[[str, str], str],
    can_submit: bool = False,
    allow_add_text: bool = True,
    allow_add_photo: bool = True,
    show_back: bool = True,
):
    kb = InlineKeyboardBuilder()
    if allow_add_text:
        kb.button(text="✍️ " + t("btn.add_text", "Sharh yozish"), callback_data="add_text")
    if allow_add_photo:
        kb.button(text="📷 " + t("btn.add_photo", "Rasm yuborish"), callback_data="add_photo")
    if can_submit:
        kb.button(text="✅ " + t("btn.submit", "Yuborish"), callback_data="submit_review")
    if show_back:
        kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="go_back_choose_branch")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def back_to_review_menu_kb(t):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="go_back_choose_review")
    kb.adjust(1)
    return kb.as_markup()
def rating_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 ⭐", callback_data="rate:1"),
                InlineKeyboardButton(text="2 ⭐", callback_data="rate:2"),
                InlineKeyboardButton(text="3 ⭐", callback_data="rate:3"),
                InlineKeyboardButton(text="4 ⭐", callback_data="rate:4"),
                InlineKeyboardButton(text="5 ⭐", callback_data="rate:5"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="go_back_choose_review"),
            ]
        ]
    )
    
def remove_reply_kb():
    return ReplyKeyboardRemove()


def new_review_kb(t: Callable[[str, str], str]):
    """Reply keyboard with localized labels: New Review, Change Language."""
    kb = ReplyKeyboardBuilder()
    label_new = t("kb.new_review", "🆕 Yangi sharh")
    label_lang = t("kb.change_lang", "🌐 Tilni o'zgartirish")
    kb.add(KeyboardButton(text=label_new))
    kb.add(KeyboardButton(text=label_lang))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)
