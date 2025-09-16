from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError
from zoneinfo import ZoneInfo
from app.db import crud
from app.i18n import I18N
from app.config import settings
from aiogram.types import InputMediaPhoto
router = Router()


# --- States ---
class AdminStates(StatesGroup):
    br_add = State()
    br_edit = State()  # expects text for selected branch
    rev_edit = State()  # expects text for selected review
    sa_add_admin = State()  # super admin: add admin by tg_id
    sa_remove_admin = State()  # super admin: remove admin by tg_id


# --- Helpers ---
async def get_t(session, tg_id: int):
    user = await crud.get_user_by_tg_id(session, tg_id)
    locale = user.locale if user and user.locale else "uz"
    return I18N(locale).t


async def is_admin(session, tg_id: int) -> bool:
    if tg_id in settings.SUPER_ADMINS:
        return True
    return await crud.is_admin(session, tg_id)


def is_super_admin_env(tg_id: int) -> bool:
    return tg_id in settings.SUPER_ADMINS


def admin_main_kb(t):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("admin.kb.branches", "🏢 Filiallar"), callback_data="adm:br")
    kb.button(text=t("admin.kb.users", "👥 Foydalanuvchilar"), callback_data="adm:us")
    kb.button(text=t("admin.kb.reviews", "📝 Sharhlar"), callback_data="adm:re")
    kb.adjust(1)
    return kb.as_markup()


def branches_menu_kb(t):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("admin.kb.branches.add", "➕ Filial qo‘shish"), callback_data="adm:br:add")
    kb.button(text=t("admin.kb.branches.edit", "✏️ Filialni tahrirlash"), callback_data="adm:br:edit")
    kb.button(text=t("admin.kb.branches.delete", "🗑 Filialni o‘chirish"), callback_data="adm:br:del")
    kb.button(text=t("admin.kb.branches.stats", "📊 Filial statistikasi"), callback_data="adm:br:stats")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:back")
    kb.adjust(1)
    return kb.as_markup()


def back_to_branches_kb(t):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:br")
    kb.adjust(1)
    return kb.as_markup()


def users_menu_kb(t):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("admin.kb.users.list", "📃 Foydalanuvchilar ro‘yxati"), callback_data="adm:us:list")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:back")
    kb.adjust(1)
    return kb.as_markup()


def reviews_menu_kb(t):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("admin.kb.reviews.list", "📃 Sharhlar ro‘yxati"), callback_data="adm:re:list")
    kb.button(text=t("admin.kb.reviews.edit", "✏️ Sharhni tahrirlash"), callback_data="adm:re:edit")
    kb.button(text=t("admin.kb.reviews.delete", "🗑 Sharhni o‘chirish"), callback_data="adm:re:del")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:back")
    kb.adjust(1)
    return kb.as_markup()


def sa_menu_kb(t):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("admin.kb.admins", "🛡 Administratorlar"), callback_data="sa:list")
    kb.button(text=t("admin.kb.admins.add", "➕ Admin qo‘shish"), callback_data="sa:add")
    kb.button(text=t("admin.kb.admins.remove", "🗑 Adminni o‘chirish"), callback_data="sa:remove")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:back")
    kb.adjust(1)
    return kb.as_markup()


# --- Entry ---
@router.message(F.text == "/admin_sardoba")
async def admin_panel(msg: Message, session):
    if not await is_admin(session, msg.from_user.id):
        t = I18N("uz").t
        await msg.answer(t("admin.not_admin", "Siz admin emassiz."))
        return
    t = await get_t(session, msg.from_user.id)
    await msg.answer(t("admin.menu.title", "⚙️ Admin Panel"), reply_markup=admin_main_kb(t))


# --- Super Admin ---
@router.message(F.text == "/super_admin")
async def super_admin_panel(msg: Message, session):
    if not is_super_admin_env(msg.from_user.id):
        t = I18N("uz").t
        await msg.answer(t("admin.not_superadmin", "Siz super admin emassiz."))
        return
    t = await get_t(session, msg.from_user.id)
    await msg.answer(t("admin.super.panel", "Super Admin Panel"), reply_markup=sa_menu_kb(t))


@router.callback_query(F.data == "sa:add")
async def sa_add_admin_ask(cb: CallbackQuery, state: FSMContext, session):
    if not is_super_admin_env(cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    await state.set_state(AdminStates.sa_add_admin)
    await cb.message.edit_text(t("admin.admins.add.prompt", "Yozing: TG_ID | role(admin/super_admin) (ixt.)"))


@router.message(AdminStates.sa_add_admin)
async def sa_add_admin_do(msg: Message, state: FSMContext, session):
    if not is_super_admin_env(msg.from_user.id):
        await state.clear()
        return
    t = await get_t(session, msg.from_user.id)
    raw = (msg.text or "").strip()
    # Extract first number (tg_id)
    try:
        tg_id = int(raw.split()[0].replace("@", ""))
    except Exception:
        await msg.answer(t("error", "Xatolik yuz berdi. Qayta urinib ko‘ring."))
        return
    try:
        await crud.add_admin(session, tg_id=tg_id, role='admin')
        await msg.answer(t("admin.admins.add.success", "Admin qo‘shildi."))
    except IntegrityError:
        await msg.answer(t("admin.updated", "Updated ✅"))
    await state.clear()
    await msg.answer(t("admin.super.panel", "Super Admin Panel"), reply_markup=sa_menu_kb(t))


@router.callback_query(F.data == "sa:list")
async def sa_list_admins(cb: CallbackQuery, session):
    if not is_super_admin_env(cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    admins = await crud.list_admins(session, requested_by_tg_id=cb.from_user.id)
    if not admins:
        await cb.message.edit_text(t("no_data", "Ma'lumot yo'q"), reply_markup=sa_menu_kb(t))
        return
    lines = [t("admin.admins.title", "🛡 Administratorlar")]
    for a in admins:
        lines.append(f"• tg:{a.tg_id} | role:{a.role}")
    await cb.message.edit_text("\n".join(lines), reply_markup=sa_menu_kb(t))


@router.callback_query(F.data == "sa:remove")
async def sa_remove_admin_ask(cb: CallbackQuery, state: FSMContext, session):
    if not is_super_admin_env(cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    await state.set_state(AdminStates.sa_remove_admin)
    await cb.message.edit_text(t("admin.admins.remove.prompt", "Yozing: TG_ID"))


@router.message(AdminStates.sa_remove_admin)
async def sa_remove_admin_do(msg: Message, state: FSMContext, session):
    if not is_super_admin_env(msg.from_user.id):
        await state.clear()
        return
    t = await get_t(session, msg.from_user.id)
    raw = (msg.text or "").strip()
    try:
        target = int(raw.split()[0].replace("@", ""))
    except Exception:
        await msg.answer(t("error", "Xatolik yuz berdi. Qayta urinib ko‘ring."))
        return
    ok = await crud.remove_admin(session, requested_by_tg_id=msg.from_user.id, tg_id=target)
    if not ok:
        await msg.answer(t("admin.admins.remove.not_found", "Bunday admin topilmadi."))
    else:
        await msg.answer(t("admin.admins.remove.success", "Admin olib tashlandi."))
    await state.clear()
    await msg.answer(t("admin.super.panel", "Super Admin Panel"), reply_markup=sa_menu_kb(t))


@router.callback_query(F.data == "adm:back")
async def admin_back(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    await cb.message.edit_text(t("admin.menu.title", "⚙️ Admin Panel"), reply_markup=admin_main_kb(t))


# --- Branches ---
@router.callback_query(F.data == "adm:br")
async def branches_menu(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    await cb.message.edit_text(t("admin.branches.title", "🏢 Filiallar"), reply_markup=branches_menu_kb(t))


@router.callback_query(F.data == "adm:br:stats")
async def branches_stats(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    stats = await crud.branch_stats(session)
    if not stats:
        await cb.message.edit_text(t("admin.stats.empty", "Hozircha statistika yo‘q."), reply_markup=branches_menu_kb(t))
        return
    lines = [t("admin.stats.header", "📊 Filial statistikasi")]
    for s in stats:
        lines.append(f"• {s['name']}: {s['reviews_count']} {t('admin.stats.reviews','sharh')}, ⭐ {s['avg_rating']}")
    await cb.message.edit_text("\n".join(lines), reply_markup=branches_menu_kb(t))


@router.callback_query(F.data == "adm:br:add")
async def branch_add_start(cb: CallbackQuery, state: FSMContext, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    await state.set_state(AdminStates.br_add)
    # Remove previous menu, then prompt with a back-only keyboard
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.message.answer(
        t("admin.branch.add.usage", "Foydalanish: Nomi | Manzil(ixtiyoriy)"),
        reply_markup=back_to_branches_kb(t)
    )


@router.message(AdminStates.br_add)
async def branch_add_finish(msg: Message, state: FSMContext, session):
    if not await is_admin(session, msg.from_user.id):
        await state.clear()
        return
    t = await get_t(session, msg.from_user.id)
    text = msg.text or ""
    parts = [p.strip() for p in text.split("|", 1)]
    name = parts[0] if parts and parts[0] else None
    address = parts[1] if len(parts) > 1 and parts[1] else None
    if not name:
        await msg.answer(t("admin.branch.add.usage", "Foydalanish: Nomi | Manzil(ixtiyoriy)"))
        return
    await crud.create_branch_admin(session, requested_by_tg_id=msg.from_user.id, name=name, address=address)
    await state.clear()
    # Inform about success, then show branches menu again
    await msg.answer(t("admin.branch.add.success", "Filial qo‘shildi."))
    await msg.answer(t("admin.branches.title", "🏢 Filiallar"), reply_markup=branches_menu_kb(t))


@router.callback_query(F.data == "adm:br:edit")
async def branch_edit_list(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    branches = await crud.list_branches(session)
    if not branches:
        await cb.message.edit_text(t("admin.branch.empty", "Filiallar yo‘q."), reply_markup=branches_menu_kb(t))
        return
    kb = InlineKeyboardBuilder()
    for b in branches:
        kb.button(text=f"✏️ {b.name}", callback_data=f"adm:br:edit:{b.id}")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:br")
    kb.adjust(1)
    await cb.message.edit_text(t("admin.kb.branches.edit", "✏️ Filialni tahrirlash"), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm:br:edit:"))
async def branch_edit_start(cb: CallbackQuery, state: FSMContext, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    branch_id = int(cb.data.split(":")[3])
    await state.update_data(branch_id=branch_id)
    await state.set_state(AdminStates.br_edit)
    await cb.message.edit_text(
        t("admin.branch.edit.usage", "Yozing: ID | Yangi nom(ixt.) | Yangi manzil(ixt.)"),
        reply_markup=back_to_branches_kb(t),
    )


@router.message(AdminStates.br_edit)
async def branch_edit_finish(msg: Message, state: FSMContext, session):
    if not await is_admin(session, msg.from_user.id):
        await state.clear()
        return
    t = await get_t(session, msg.from_user.id)
    data = await state.get_data()
    branch_id = int(data.get("branch_id"))
    raw = msg.text or ""
    name = None
    address = None
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|", 1)]
        name = parts[0] or None
        address = parts[1] or None
    else:
        name = raw.strip() or None
    try:
        await crud.update_branch_admin(session, requested_by_tg_id=msg.from_user.id, branch_id=branch_id, name=name, address=address)
    except ValueError:
        await msg.answer(t("admin.branch.edit.not_found", "Bunday ID li filial topilmadi."))
        await state.clear()
        return
    await state.clear()
    await msg.answer(t("admin.branch.edit.success", "Filial yangilandi."))
    await msg.answer(t("admin.branches.title", "🏢 Filiallar"), reply_markup=branches_menu_kb(t))


@router.callback_query(F.data == "adm:br:del")
async def branch_delete_list(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    branches = await crud.list_branches(session)
    if not branches:
        await cb.message.edit_text(t("admin.branch.empty", "Filiallar yo‘q."), reply_markup=branches_menu_kb(t))
        return
    kb = InlineKeyboardBuilder()
    for b in branches:
        kb.button(text=f"🗑 {b.name}", callback_data=f"adm:br:del:{b.id}")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:br")
    kb.adjust(1)
    await cb.message.edit_text(t("admin.kb.branches.delete", "🗑 Filialni o‘chirish"), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm:br:del:"))
async def branch_delete_do(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    branch_id = int(cb.data.split(":")[3])
    ok = await crud.delete_branch_admin(session, requested_by_tg_id=cb.from_user.id, branch_id=branch_id)
    if not ok:
        await cb.answer(t("admin.branch.delete.not_found", "Topilmadi"), show_alert=True)
    else:
        await cb.answer(t("admin.branch.delete.success", "O‘chirildi"), show_alert=True)
    # Refresh list
    branches = await crud.list_branches(session)
    kb = InlineKeyboardBuilder()
    for b in branches:
        kb.button(text=f"🗑 {b.name}", callback_data=f"adm:br:del:{b.id}")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:br")
    kb.adjust(1)
    await cb.message.edit_text(t("admin.kb.branches.delete", "🗑 Filialni o‘chirish"), reply_markup=kb.as_markup())


# --- Users ---
@router.callback_query(F.data == "adm:us")
async def users_menu(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    await cb.message.edit_text(t("admin.users.title", "👥 Foydalanuvchilar"), reply_markup=users_menu_kb(t))

@router.callback_query(F.data == "adm:us:list")
async def users_list(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    users = await crud.list_users_admin(session, requested_by_tg_id=cb.from_user.id, limit=50)
    if not users:
        await cb.message.edit_text(t("no_data", "Ma'lumot yo'q"), reply_markup=users_menu_kb(t))
        return

    lines = [t("admin.users.list.header", "👥 Foydalanuvchilar:")]
    for u in users:
        name = " ".join(filter(None, [u.first_name, u.last_name])) or "-"
        phone = u.phone or "-"
        tg_link = f"<a href='tg://user?id={u.tg_id}'>{name or 'User'}</a>"

        # ✅ only one argument inside append
        lines.append(f"#{u.id} | {tg_link} | {phone}")
    await cb.message.edit_text(
        "\n".join(lines),
        reply_markup=users_menu_kb(t),
        parse_mode="HTML"   # ✅ moved parse_mode here
    )
# --- Groups ---
@router.message(F.text == "/setgroup")
async def set_group(msg: Message, session):
    # Faqat guruhda ishlasin
    if msg.chat.type not in ("group", "supergroup"):
        await msg.answer("❗ Bu buyruqni faqat guruhda yuboring")
        return

    try:
        await crud.set_admin_group(session, msg.from_user.id, msg.chat.id)
        await msg.answer("✅ Guruh muvaffaqiyatli bog‘landi")
    except ValueError:
        await msg.answer("⛔ Siz superadmin emassiz")
# --- Reviews ---
@router.callback_query(F.data == "adm:re")
async def reviews_menu(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    await cb.message.edit_text(t("admin.reviews.title", "📝 Sharhlar"), reply_markup=reviews_menu_kb(t))

@router.callback_query(F.data == "adm:re:list")
async def reviews_list(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)

    reviews = await crud.list_reviews_admin(session, requested_by_tg_id=cb.from_user.id, limit=10)
    if not reviews:
        await cb.message.edit_text(t("no_data", "Ma'lumot yo'q"), reply_markup=reviews_menu_kb(t))
        return

    await cb.message.delete()  # oldingi menyuni tozalash

    for r in reviews:
        user = r.user
        branch = r.branch

        # User haqida
        name = " ".join(filter(None, [user.first_name, user.last_name])) if user else "-"
        phone = user.phone if user and user.phone else "-"
        tg_link = f"<a href='tg://user?id={user.tg_id}'>{name or 'User'}</a>" if user else "-"

        # Vaqt
        localtime = r.created_at.astimezone(ZoneInfo("Asia/Tashkent"))

        caption = (
            f"#{r.id} | ⭐ {r.rating or '-'}\n"
            f"👤 {tg_link} | 📱 {phone}\n"
            f"📍 {branch.name if branch else '-'}\n"
            f"💬 {r.text or '-'}\n"
            f"🕒 {localtime.strftime('%Y-%m-%d %H:%M')}"
        )

        photos = [p.file_id for p in (r.photos or [])]

        if photos:
            media = []
            for idx, fid in enumerate(photos):
                if idx == 0:
                    media.append(InputMediaPhoto(media=fid, caption=caption, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=fid))
            await cb.message.answer_media_group(media)
        else:
            await cb.message.answer(caption, parse_mode="HTML")

    # menyuni qayta chiqarish
    await cb.message.answer(
        t("admin.reviews.title", "📝 Sharhlar"),
        reply_markup=reviews_menu_kb(t)
    )
    
@router.callback_query(F.data.startswith("adm:re:edit:"))
async def review_edit_start(cb: CallbackQuery, state: FSMContext, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    review_id = int(cb.data.split(":")[3])
    await state.update_data(review_id=review_id)
    await state.set_state(AdminStates.rev_edit)
    await cb.message.edit_text(t("admin.reviews.edit.prompt", "Send: rating|text (either can be omitted)"))


@router.message(AdminStates.rev_edit)
async def review_edit_finish(msg: Message, state: FSMContext, session):
    if not await is_admin(session, msg.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    review_id = int(data.get("review_id"))
    raw = (msg.text or "").strip()
    rating: int | None = None
    text: str | None = None
    if "|" in raw:
        left, right = [p.strip() for p in raw.split("|", 1)]
        if left.isdigit():
            r = int(left)
            if 1 <= r <= 5:
                rating = r
        text = right or None
    else:
        if raw.isdigit():
            r = int(raw)
            if 1 <= r <= 5:
                rating = r
        else:
            text = raw or None
    t = await get_t(session, msg.from_user.id)
    try:
        await crud.update_review_admin(session, requested_by_tg_id=msg.from_user.id, review_id=review_id, rating=rating, text=text)
    except ValueError:
        await msg.answer("Review not found")
        await state.clear()
        return
    await state.clear()
    t = await get_t(session, msg.from_user.id)
    await msg.answer(t("admin.updated", "Updated ✅"))


@router.callback_query(F.data == "adm:re:del")
async def review_delete_list(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    t = await get_t(session, cb.from_user.id)
    reviews = await crud.list_reviews_admin(session, requested_by_tg_id=cb.from_user.id, limit=30)
    if not reviews:
        await cb.message.edit_text(t("no_data", "Ma'lumot yo'q"), reply_markup=reviews_menu_kb(t))
        return
    kb = InlineKeyboardBuilder()
    for r in reviews:
        kb.button(text=f"🗑 #{r.id} ⭐{r.rating}", callback_data=f"adm:re:del:{r.id}")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:re")
    kb.adjust(2)
    await cb.message.edit_text(t("admin.kb.reviews.delete", "🗑 Sharhni o‘chirish"), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm:re:del:"))
async def review_delete_do(cb: CallbackQuery, session):
    if not await is_admin(session, cb.from_user.id):
        return
    review_id = int(cb.data.split(":")[3])
    ok = await crud.delete_review_admin(session, requested_by_tg_id=cb.from_user.id, review_id=review_id)
    t = await get_t(session, cb.from_user.id)
    if ok:
        await cb.answer(t("admin.deleted", "Deleted"), show_alert=True)
    else:
        await cb.answer(t("admin.not_found", "Not found"), show_alert=True)
    # refresh list
    t = await get_t(session, cb.from_user.id)
    reviews = await crud.list_reviews_admin(session, requested_by_tg_id=cb.from_user.id, limit=30)
    kb = InlineKeyboardBuilder()
    for r in reviews:
        kb.button(text=f"🗑 #{r.id} ⭐{r.rating}", callback_data=f"adm:re:del:{r.id}")
    kb.button(text=t("common.kb.back", "⬅ Orqaga"), callback_data="adm:re")
    kb.adjust(2)
    await cb.message.edit_text(t("admin.kb.reviews.delete", "🗑 Sharhni o‘chirish"), reply_markup=kb.as_markup())
