# Imports:
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select


# Helper Funcs:
async def check_exists(db: AsyncSession, model_obj: Any, val1: Any, val2: Any, return_obj=False, load_immediately=None):
    if load_immediately:
        result = await db.execute(select(model_obj).options(selectinload(load_immediately)).where(val1 == val2))
    result = await db.execute(select(model_obj).where(val1 == val2))
    if return_obj:
        return result.scalars().first()
    return bool(result.scalars().first())