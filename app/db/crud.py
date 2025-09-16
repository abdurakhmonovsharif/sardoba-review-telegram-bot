from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, Branch, Review, Admin
from app.config import settings
from sqlalchemy.orm import joinedload
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
    photo_file_id: str | None
) -> Review:
    r = Review(
        user_id=user_id,
        branch_id=branch_id,
        rating=rating,
        text=text,
        photo_file_id=photo_file_id
    )
    session.add(r)
    await session.commit()
    await session.refresh(r)

    # Eager load with relations (user, branch)
    q = await session.execute(
        select(Review)
        .options(joinedload(Review.user), joinedload(Review.branch))
        .where(Review.id == r.id)
    )
    return q.scalar_one()

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


async def list_reviews_admin(
    session: AsyncSession,
    requested_by_tg_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[Review]:
    await _ensure_admin(session, requested_by_tg_id)
    q = await session.execute(
        select(Review).options(
            joinedload(Review.user),
            joinedload(Review.branch)
            ).order_by(Review.id.desc()).offset(offset).limit(limit)
    )
    return list(q.scalars().all())


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
    q = await session.execute(
        select(Admin.group_id).where(Admin.tg_id == super_admin_id)
    )
    return q.scalar_one_or_none()