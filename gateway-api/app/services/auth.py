import hashlib
from sqlalchemy.orm import Session
from app.schemas.models import ApiKey


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key (hex digest)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def validate_api_key(raw_key: str, db: Session) -> ApiKey | None:
    """
    Look up the key by its hash and verify it is active.
    Returns the ApiKey ORM object or None.
    """
    key_hash = hash_api_key(raw_key)
    return (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.status == "active")
        .first()
    )
