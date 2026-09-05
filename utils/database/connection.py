from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

from config import DATABASE_PATH

Base = declarative_base()

SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
session_local = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
