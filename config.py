import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _make_db_uri(raw: str) -> str:
    """Convert a relative sqlite:/// path to an absolute one."""
    if raw.startswith("sqlite:///") and not raw.startswith("sqlite:////"):
        rel = raw[len("sqlite:///"):]
        abs_path = (BASE_DIR / rel).as_posix()
        return f"sqlite:///{abs_path}"
    return raw


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = _make_db_uri(
        os.getenv("DATABASE_URL", "sqlite:///data/portal.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY is not set. Copy .env.example to .env and set a long random value."
            )
