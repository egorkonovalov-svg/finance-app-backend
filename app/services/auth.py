import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.verification_code import VerificationCode

MAX_VERIFICATION_ATTEMPTS = 5


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


async def create_verification(
    db: AsyncSession, user_id: UUID, purpose: str
) -> tuple[str, str]:
    code = generate_verification_code()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES
    )
    record = VerificationCode(
        user_id=user_id, code=code, purpose=purpose, expires_at=expires
    )
    db.add(record)
    await db.flush()
    session_id = str(record.id)
    await db.commit()
    return session_id, code


async def validate_verification_code(
    db: AsyncSession, session_id: str, code: str
) -> VerificationCode:
    result = await db.execute(
        select(VerificationCode).where(VerificationCode.id == UUID(session_id))
    )
    record = result.scalar_one_or_none()

    if not record or record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification session",
        )

    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code expired"
        )

    if record.attempts >= MAX_VERIFICATION_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please request a new code.",
        )

    if record.code != code:
        record.attempts += 1
        await db.commit()
        remaining = MAX_VERIFICATION_ATTEMPTS - record.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid code. {remaining} attempt(s) remaining.",
        )

    record.used = True
    await db.commit()
    return record


DEFAULT_CATEGORIES = [
    {"name": "Salary", "icon": "cash", "color": "#10B981", "type": "income"},
    {"name": "Freelance", "icon": "laptop", "color": "#6366F1", "type": "income"},
    {"name": "Investments", "icon": "trending-up", "color": "#8B5CF6", "type": "income"},
    {"name": "Food & Drinks", "icon": "restaurant", "color": "#F59E0B", "type": "expense"},
    {"name": "Transport", "icon": "car", "color": "#3B82F6", "type": "expense"},
    {"name": "Shopping", "icon": "cart", "color": "#EC4899", "type": "expense"},
    {"name": "Entertainment", "icon": "game-controller", "color": "#F97316", "type": "expense"},
    {"name": "Health", "icon": "fitness", "color": "#EF4444", "type": "expense"},
    {"name": "Bills & Utilities", "icon": "flash", "color": "#14B8A6", "type": "expense"},
    {"name": "Education", "icon": "school", "color": "#0EA5E9", "type": "expense"},
    {"name": "Gifts", "icon": "gift", "color": "#D946EF", "type": "both"},
    {"name": "Other", "icon": "ellipsis-horizontal", "color": "#6B7280", "type": "both"},
]
