from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    category: str
    note: str | None = None
    date: datetime
    recurring: bool = False


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    category: str | None = None
    note: str | None = None
    date: datetime | None = None
    recurring: bool | None = None


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    currency: str
    category: str
    note: str | None = None
    date: datetime
    recurring: bool

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CategoryStat(BaseModel):
    category: str
    amount: float
    color: str


class DailyStat(BaseModel):
    date: str
    income: float
    expense: float


class StatsResponse(BaseModel):
    total_income: float
    total_expenses: float
    balance: float
    by_category: list[CategoryStat]
    daily: list[DailyStat]
