from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.schemas.database import SessionLocal
from app.schemas.models import ProviderConfig

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    configs = db.query(ProviderConfig).filter(ProviderConfig.is_active == True).all()
    return [
        {
            "id": f"{c.provider_name}/{c.model_name}",
            "provider": c.provider_name,
            "model": c.model_name,
            "max_context_tokens": c.max_context_tokens,
        }
        for c in configs
    ]
