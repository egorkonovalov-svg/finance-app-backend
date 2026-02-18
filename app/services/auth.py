from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import settings


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
