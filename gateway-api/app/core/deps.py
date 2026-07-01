from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.schemas.database import SessionLocal
from app.schemas.models import ApiKey
from app.services.auth import validate_api_key


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_api_key(
    authorization: str = Header(..., description="Bearer <api-key>"),
    db: Session = Depends(get_db),
) -> ApiKey:
    """
    Validate the Bearer token from the Authorization header.
    Returns the active ApiKey ORM object or raises 401.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header must be 'Bearer <key>'",
        )
    raw_key = authorization[len("Bearer "):]
    api_key = validate_api_key(raw_key, db)
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return api_key
