from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, Branch, Review, Admin

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

async def list_branches(session: AsyncSession) -> list[Branch]:
    q = await session.execute(select(Branch).order_by(Branch.name))
    return list(q.scalars().all())

async def create_review(session: AsyncSession, user_id: int, branch_id: int, rating: int, text: str | None, photo_file_id: str | None) -> Review:
    r = Review(user_id=user_id, branch_id=branch_id, rating=rating, text=text, photo_file_id=photo_file_id)
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r

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