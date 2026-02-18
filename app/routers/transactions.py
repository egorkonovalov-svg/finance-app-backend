from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    StatsResponse,
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.stats import get_monthly_stats

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _to_response(tx: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=str(tx.id),
        type=tx.type,
        amount=float(tx.amount),
        currency=tx.currency,
        category=tx.category,
        note=tx.note,
        date=tx.date,
        recurring=tx.recurring,
    )


def _apply_filters(
    q: Select,
    user_id: UUID,
    *,
    type: str | None,
    category: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    amount_min: float | None,
    amount_max: float | None,
    search: str | None,
) -> Select:
    q = q.where(Transaction.user_id == user_id)
    if type:
        q = q.where(Transaction.type == type)
    if category:
        q = q.where(Transaction.category == category)
    if date_from:
        q = q.where(Transaction.date >= date_from)
    if date_to:
        q = q.where(Transaction.date <= date_to)
    if amount_min is not None:
        q = q.where(Transaction.amount >= amount_min)
    if amount_max is not None:
        q = q.where(Transaction.amount <= amount_max)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            Transaction.note.ilike(pattern) | Transaction.category.ilike(pattern)
        )
    return q


@router.get("/stats", response_model=StatsResponse)
async def stats(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if month:
        year, m = int(month[:4]), int(month[5:])
    else:
        now = datetime.now(timezone.utc)
        year, m = now.year, now.month

    data = await get_monthly_stats(db, current_user.id, year, m)
    return StatsResponse(**data)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    type: str | None = None,
    category: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filter_kwargs = dict(
        type=type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        search=search,
    )

    count_q = _apply_filters(
        select(func.count(Transaction.id)), current_user.id, **filter_kwargs
    )
    total = (await db.execute(count_q)).scalar() or 0

    items_q = _apply_filters(
        select(Transaction), current_user.id, **filter_kwargs
    )
    items_q = (
        items_q.order_by(Transaction.date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(items_q)
    items = result.scalars().all()

    return TransactionListResponse(
        items=[_to_response(tx) for tx in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return _to_response(tx)


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tx = Transaction(user_id=current_user.id, **body.model_dump())
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return _to_response(tx)


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    body: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)

    await db.commit()
    await db.refresh(tx)
    return _to_response(tx)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    await db.delete(tx)
    await db.commit()
    return None
