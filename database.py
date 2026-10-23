import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# main.py imports this file BEFORE it calls load_dotenv(), so load .env here too
load_dotenv()

# Online / PostgreSQL: set DATABASE_URL (in .env on your laptop, in the dashboard on the host).
# Not set: fall back to the local SQLite file, exactly like before.
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./intelliChat.db"
SQLALCHEMY_DATABASE_URL = DATABASE_URL  # old name, kept in case another file imports it

# Some hosts give "postgres://", SQLAlchemy needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping tests a connection before using it, because a free Postgres
    # goes to sleep when idle and the old connection may be dead.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()