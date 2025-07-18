from typing import Any, Generator
from sqlalchemy.orm import Session
from .connection import SessionLocal
from .schema import *


def get_db()-> Generator[Session, Any, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
