import hashlib
import logging
import secrets

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from mona_core.db import ApiKey
from mona_core.schemas import ApiKeyCreate
from mona_core.security import (
    admin_router,
    get_db,
)

logger = logging.getLogger(__name__)


@admin_router.post("/api")
def create_api_key(body: ApiKeyCreate, db: Session = Depends(get_db)):
    api_key = f"mona_api_{secrets.token_urlsafe(32)}"
    api_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    key = ApiKey(name=body.name, key_hash=api_hash)
    db.add(key)
    try:
        db.commit()
        db.refresh(key)
    except Exception:
        db.rollback()
        logger.exception("Error during creating device")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error"
        )
    logger.info("API key created")
    return {"apiKey": api_key, "name": key.name, "id": key.id}
