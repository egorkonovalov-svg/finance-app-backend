from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, cast, extract, func, select, case, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.transaction import Transaction


async def get_monthly_stats(
    db: AsyncSession, user_id: UUID, year: int, month: int
) -> dict:
    base_filter = and_(
        Transaction.user_id == user_id,
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month,
    )

    # Totals
    totals_q = select(
        func.coalesce(
            func.sum(case((Transaction.type == "income", Transaction.amount), else_=Decimal(0))),
            Decimal(0),
        ).label("total_income"),
        func.coalesce(
            func.sum(case((Transaction.type == "expense", Transaction.amount), else_=Decimal(0))),
            Decimal(0),
        ).label("total_expenses"),
    ).where(base_filter)

    totals = (await db.execute(totals_q)).one()
    total_income = float(totals.total_income)
    total_expenses = float(totals.total_expenses)

    # By category (expenses only, with color from categories table)
    by_cat_q = (
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("amount"),
            func.coalesce(Category.color, "#6B7280").label("color"),
        )
        .outerjoin(
            Category,
            and_(
                Category.user_id == user_id,
                Category.name == Transaction.category,
            ),
        )
        .where(and_(base_filter, Transaction.type == "expense"))
        .group_by(Transaction.category, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
    )
    by_cat_rows = (await db.execute(by_cat_q)).all()
    by_category = [
        {"category": r.category, "amount": float(r.amount), "color": r.color}
        for r in by_cat_rows
    ]

    # Daily breakdown for the whole month
    day_col = cast(Transaction.date, Date).label("day")
    daily_q = (
        select(
            day_col,
            func.coalesce(
                func.sum(case((Transaction.type == "income", Transaction.amount), else_=Decimal(0))),
                Decimal(0),
            ).label("income"),
            func.coalesce(
                func.sum(case((Transaction.type == "expense", Transaction.amount), else_=Decimal(0))),
                Decimal(0),
            ).label("expense"),
        )
        .where(base_filter)
        .group_by(day_col)
        .order_by(day_col)
    )
    daily_rows = (await db.execute(daily_q)).all()

    today = datetime.now(timezone.utc).date()
    last_day = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    end_day = min(today, last_day)
    start_day = date(year, month, 1)

    daily_map: dict[str, dict] = {}
    for r in daily_rows:
        d = r.day if isinstance(r.day, date) else r.day.date()
        daily_map[d.isoformat()] = {"income": float(r.income), "expense": float(r.expense)}

    daily = []
    current = start_day
    while current < end_day:
        key = current.isoformat()
        entry = daily_map.get(key, {"income": 0.0, "expense": 0.0})
        daily.append({"date": key, **entry})
        current = date.fromordinal(current.toordinal() + 1)

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses,
        "by_category": by_category,
        "daily": daily,
    }
