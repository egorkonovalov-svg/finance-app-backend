from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.config import settings
from app.database import engine, Base
from app.routers import auth, categories, dev, transactions

SHOW_DOCS_ENVIRONMENT = ("local", "staging")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import all models so Base.metadata knows about them
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


app_configs: dict = {"title": "FinTrack API", "lifespan": lifespan}
if settings.ENVIRONMENT not in SHOW_DOCS_ENVIRONMENT:
    app_configs["openapi_url"] = None

app = FastAPI(**app_configs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(dev.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}

# if "name" == "__main__":
#     uvicorn.run("main:app",host:"0.0.0.0", port=8000)