import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import SignupRequest
from src.auth.service import handle_signup
from src.database import get_db

logger = logging.getLogger(__name__)

auth_router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    strict_content_type=True,
    include_in_schema=True,
)


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    logger.debug(msg="Received signup payload", extra={"payload": payload})
    await handle_signup(db, payload)
