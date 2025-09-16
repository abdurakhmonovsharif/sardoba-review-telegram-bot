from aiogram import Bot
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, Branch, Review, Admin, ReviewPhoto
from aiogram.types import InputMediaPhoto
from app.config import settings
from sqlalchemy.orm import joinedload
from zoneinfo import ZoneInfo
async def get_review_with_relations(session: AsyncSession, review_id: int) -> Review | None:
    q = await session.execute(
        select(Review)
        .options(joinedload(Review.user), joinedload(Review.branch))
        .where(Review.id == review_id)
    )
    return q.scalar_one_or_none()

async def upsert_user(session: AsyncSession, tg_id: int, **kwargs) -> User:
    q = await session.execute(select(User).where(User.tg_id == tg_id))
    user = q.scalar_one_or_none()
    if user is None:
        user = User(tg_id=tg_id, **kwargs)
        session.add(user)
    else:
        for k, v in kwargs.items():
            setattr(user, k, v)
    await session.commit()
    await session.refresh(user)
    return user

async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    q = await session.execute(select(User).where(User.tg_id == tg_id))
    return q.scalar_one_or_none()

async def list_branches(session: AsyncSession) -> list[Branch]:
    q = await session.execute(select(Branch).order_by(Branch.name))
    return list(q.scalars().all())

async def create_review(
    session: AsyncSession,
    user_id: int,
    branch_id: int,
    rating: int | None,
    text: str | None,
    photos: list[str] | None
) -> Review:
    # 1. Review obyektini yaratish
    r = Review(
        user_id=user_id,
        branch_id=branch_id,
        rating=rating,
        text=text,
    )
    session.add(r)
    await session.flush()  # id olish uchun

    # 2. Photo qo‘shish (commitdan oldin!)
    if photos:
        for file_id in photos:
            session.add(ReviewPhoto(review_id=r.id, file_id=file_id))

    # 3. Commit
    await session.commit()

    # 4. Review ni qayta olish (user, branch, photos bilan)
    q = await session.execute(
        select(Review)
        .options(
            joinedload(Review.user),
            joinedload(Review.branch),
            joinedload(Review.photos)
        )
        .where(Review.id == r.id)
    )
    return q.unique().scalar_one()   # 👈 muammoni hal qiladi

async def is_super_admin(session: AsyncSession, tg_id: int) -> bool:
    q = await session.execute(select(Admin).where(Admin.tg_id == tg_id, Admin.role == 'super_admin'))
    return q.scalar_one_or_none() is not None

async def is_admin(session: AsyncSession, tg_id: int) -> bool:
    q = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
    return q.scalar_one_or_none() is not None

async def add_admin(session: AsyncSession, tg_id: int, role: str = 'admin') -> Admin:
    a = Admin(tg_id=tg_id, role=role)
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


# =============== Admin CRUD (super admin only) ===============

async def get_admin_by_tg_id(session: AsyncSession, tg_id: int) -> Admin | None:
    q = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
    return q.scalar_one_or_none()


async def list_admins(session: AsyncSession, requested_by_tg_id: int) -> list[Admin]:
    # Only super admin from env allowed to list admins
    if requested_by_tg_id not in settings.SUPER_ADMINS:
        raise PermissionError("Only super admin can list admins")
    q = await session.execute(select(Admin).order_by(Admin.role.desc(), Admin.id))
    return list(q.scalars().all())


async def remove_admin(session: AsyncSession, requested_by_tg_id: int, tg_id: int) -> bool:
    # Only super admin from env allowed to remove admins
    if requested_by_tg_id not in settings.SUPER_ADMINS:
        raise PermissionError("Only super admin can remove admins")
    # Do not allow removing env super admin
    if tg_id in settings.SUPER_ADMINS:
        return False
    q = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
    a = q.scalar_one_or_none()
    if a is None:
        return False
    await session.delete(a)
    await session.commit()
    return True

async def branch_stats(session: AsyncSession):
    q = await session.execute(
        select(
            Branch.id,
            Branch.name,
            func.count(Review.id),
            func.round(func.avg(Review.rating), 2)
        ).join(Review, Review.branch_id == Branch.id, isouter=True)
         .group_by(Branch.id)
         .order_by(Branch.name)
    )
    return [
        {
            "branch_id": r[0],
            "name": r[1],
            "reviews_count": int(r[2] or 0),
            "avg_rating": float(r[3] or 0)
        } for r in q.all()
    ]

# =============== Branch CRUD (admin only) ===============

async def _ensure_admin(session: AsyncSession, tg_id: int) -> None:
    # SUPER_ADMINS from config are always allowed
    if tg_id in settings.SUPER_ADMINS:
        return
    q = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
    if q.scalar_one_or_none() is None:
        raise PermissionError("Only admins can perform this action")


async def get_branch(session: AsyncSession, branch_id: int) -> Branch | None:
    q = await session.execute(select(Branch).where(Branch.id == branch_id))
    return q.scalar_one_or_none()


async def create_branch_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
    name: str,
    address: str | None = None,
) -> Branch:
    await _ensure_admin(session, requested_by_tg_id)
    b = Branch(name=name, address=address)
    session.add(b)
    await session.commit()
    await session.refresh(b)
    return b


async def update_branch_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
    branch_id: int,
    name: str | None = None,
    address: str | None = None,
) -> Branch:
    await _ensure_admin(session, requested_by_tg_id)
    q = await session.execute(select(Branch).where(Branch.id == branch_id))
    b = q.scalar_one_or_none()
    if b is None:
        raise ValueError("Branch not found")
    if name is not None:
        b.name = name
    if address is not None:
        b.address = address
    await session.commit()
    await session.refresh(b)
    return b


async def delete_branch_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
    branch_id: int,
) -> bool:
    await _ensure_admin(session, requested_by_tg_id)
    q = await session.execute(select(Branch).where(Branch.id == branch_id))
    b = q.scalar_one_or_none()
    if b is None:
        return False
    await session.delete(b)
    await session.commit()
    return True


# =============== Aggregates ===============
async def count_users(session: AsyncSession) -> int:
    q = await session.execute(select(func.count(User.id)))
    return int(q.scalar() or 0)


async def count_reviews(session: AsyncSession) -> int:
    q = await session.execute(select(func.count(Review.id)))
    return int(q.scalar() or 0)


# =============== Admin helpers for Users & Reviews ===============

async def list_users_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    await _ensure_admin(session, requested_by_tg_id)
    q = await session.execute(
        select(User).order_by(User.id).offset(offset).limit(limit)
    )
    return list(q.scalars().all())


from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Review

async def list_reviews_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
) -> list[Review]:
    await _ensure_admin(session, requested_by_tg_id)

    q = (
        select(Review)
        .options(
            joinedload(Review.user),
            joinedload(Review.branch),
            joinedload(Review.photos),  
        )
        .order_by(Review.id.desc())
    )
    res = await session.execute(q)
    return res.unique().scalars().all()  


async def get_review(session: AsyncSession, review_id: int) -> Review | None:
    q = await session.execute(select(Review).where(Review.id == review_id))
    return q.scalar_one_or_none()


async def update_review_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
    review_id: int,
    rating: int | None = None,
    text: str | None = None,
) -> Review:
    await _ensure_admin(session, requested_by_tg_id)
    q = await session.execute(select(Review).where(Review.id == review_id))
    r = q.scalar_one_or_none()
    if r is None:
        raise ValueError("Review not found")
    if rating is not None:
        r.rating = rating
    if text is not None:
        r.text = text
    await session.commit()
    await session.refresh(r)
    return r


async def delete_review_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
    review_id: int,
) -> bool:
    await _ensure_admin(session, requested_by_tg_id)
    q = await session.execute(select(Review).where(Review.id == review_id))
    r = q.scalar_one_or_none()
    if r is None:
        return False
    await session.delete(r)
    await session.commit()
    return True

async def get_admin_group(session: AsyncSession, super_admin_id: int) -> int | None:
    """
    Super admin uchun bog‘langan guruh ID sini qaytaradi.
    Agar topilmasa, None qaytaradi.
    """
    # Ensure column exists (idempotent)
    await session.execute(text("ALTER TABLE admins ADD COLUMN IF NOT EXISTS group_id BIGINT"))
    await session.commit()
    q = await session.execute(
        select(Admin.group_id).where(Admin.tg_id == super_admin_id)
    )
    return q.scalar_one_or_none()


async def set_admin_group(session: AsyncSession, tg_id: int, group_id: int):
    """Superadmin uchun guruh ID ni saqlash (yoki yangilash)."""
    # faqat SUPER_ADMINS ro'yxatidagi foydalanuvchilar o'zgartira oladi
    if tg_id not in settings.SUPER_ADMINS:
        raise ValueError("Not a superadmin")

    # Ensure column exists (idempotent)
    await session.execute(text("ALTER TABLE admins ADD COLUMN IF NOT EXISTS group_id BIGINT"))
    await session.commit()

    q = await session.execute(select(Admin).where(Admin.tg_id == tg_id))
    admin = q.scalar_one_or_none()
    if admin is None:
        # Agar DBda bo'lmasa, super_admin sifatida yaratamiz
        admin = Admin(tg_id=tg_id, role='super_admin', group_id=group_id)
        session.add(admin)
    else:
        admin.group_id = group_id
    await session.commit()
    await session.refresh(admin)
    return admin

async def notify_superadmin_group(bot: Bot, session: AsyncSession, super_admin_id: int, review: Review):
    """Yangi sharh haqida superadmin guruhiga xabar yuborish"""

    # Guruh ID ni olish
    group_id = await get_admin_group(session, super_admin_id)
    if not group_id:
        print("[notify_superadmin_group] ⚠️ Superadmin uchun group_id topilmadi")
        return

    # Review ni barcha relation’lari bilan qayta yuklab olish
    review = await get_review_with_relations(session, review.id)
    if not review:
        print(f"[notify_superadmin_group] ⚠️ Review id={review.id} topilmadi")
        return

    user = review.user
    branch = review.branch

    # Vaqtni Toshkent TZ ga o‘tkazish
    localtime = review.created_at.astimezone(ZoneInfo("Asia/Tashkent"))

    # User haqida ma'lumot
    name = " ".join(filter(None, [user.first_name, user.last_name])) if user else "-"
    phone = user.phone if user and user.phone else "-"
    tg_link = f"<a href='tg://user?id={user.tg_id}'>{name or 'User'}</a>" if user else "-"

    # Caption formatlash
    caption = (
        f"🆕 Yangi sharh!\n"
        f"#{review.id} | ⭐ {review.rating or '-'}\n"
        f"👤 {tg_link} | 📱 {phone}\n"
        f"📍 {branch.name if branch else '-'}\n"
        f"💬 {review.text or '-'}\n"
        f"🕒 {localtime.strftime('%Y-%m-%d %H:%M')}"
    )

    photos = [p.file_id for p in (review.photos or [])]

    try:
        if not photos:
            # faqat text
            await bot.send_message(
                chat_id=group_id,
                text=caption,
                parse_mode="HTML"
            )
        elif len(photos) == 1:
            # bitta rasm
            await bot.send_photo(
                chat_id=group_id,
                photo=photos[0],
                caption=caption,
                parse_mode="HTML"
            )
        else:
            # ko‘p rasm → media group
            media = []
            for idx, file_id in enumerate(photos):
                if idx == 0:
                    media.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=file_id))
            await bot.send_media_group(chat_id=group_id, media=media)

    except Exception as e:
        print(f"[notify_superadmin_group] ❌ Guruhga yuborishda xatolik: {e}")