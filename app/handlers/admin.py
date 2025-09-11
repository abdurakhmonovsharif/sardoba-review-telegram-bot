from aiogram import Router, F
from aiogram.types import Message

from app.db import crud
from app.config import settings

router = Router()

@router.message(F.text == "/admin")
async def admin_menu(msg: Message, session):
    if msg.from_user.id not in settings.SUPER_ADMINS:
        is_admin = await crud.is_admin(session, msg.from_user.id)
        if not is_admin:
            await msg.answer("Siz admin emassiz.")
            return

    stats = await crud.branch_stats(session)
    text = "📊 Filial statistikasi:\n"
    for s in stats:
        text += f"\n🏢 {s['name']} — {s['reviews_count']} sharh, ⭐ {s['avg_rating']}"
    await msg.answer(text)