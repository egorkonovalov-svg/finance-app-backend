from fastapi import APIRouter, status

from app.database import engine, Base
import app.models  # noqa: F401

router = APIRouter(prefix="/dev", tags=["Dev"])


@router.post("/reset-db", status_code=status.HTTP_200_OK)
async def reset_database():
    """Drop all tables and recreate them. Destroys all data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"detail": "All tables dropped and recreated"}
