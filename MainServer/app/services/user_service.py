from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UpdateUserRequest


class UserService:
    @staticmethod
    async def update_profile(
        db: AsyncSession, user: User, data: UpdateUserRequest
    ) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(
                user,
                field,
                value.strip().upper() if field == "country" and value else value,
            )
        await db.commit()
        await db.refresh(user)
        return user
