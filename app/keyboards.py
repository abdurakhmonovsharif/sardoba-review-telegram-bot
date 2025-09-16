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


def branches_kb(branches: list):
    kb = InlineKeyboardBuilder()
    for b in branches:
        kb.button(text=b.name, callback_data=f"branch:{b.id}")
    kb.adjust(1)
    return kb.as_markup()

def review_menu_kb(t, can_submit: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ " + t("btn.add_rating", "Reyting"), callback_data="add_rating")
    kb.button(text="✍️ " + t("btn.add_text", "Sharh yozish"), callback_data="add_text")
    kb.button(text="📷 " + t("btn.add_photo", "Rasm yuborish"), callback_data="add_photo")
    if can_submit:
        kb.button(text="✅ " + t("btn.submit", "Yuborish"), callback_data="submit_review")
    # Back to branch selection
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="go_back_choose_branch")
    # If submit is hidden, keep layout 2x2 + back; if submit visible, it will also fit rows nicely
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
