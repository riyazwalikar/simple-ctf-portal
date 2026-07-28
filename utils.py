import hmac
import os
from functools import wraps
from flask import abort
from flask_login import current_user
from sqlalchemy import func, select
from models import Setting, Submission, Challenge
from extensions import db

# Logo upload: raster formats only. SVG is deliberately excluded — it can
# carry script and would be a stored-XSS vector when served back.
LOGO_MAGIC = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    b"RIFF": ".webp",  # refined below (RIFF....WEBP)
}


def sniff_logo_ext(data):
    """Return the allowed extension for *data* by magic bytes, else None."""
    for magic, ext in LOGO_MAGIC.items():
        if data.startswith(magic):
            if ext == ".webp" and data[8:12] != b"WEBP":
                return None
            return ext
    return None


def save_logo(file_storage, data_dir):
    """Validate and persist an uploaded logo. Returns the saved filename.

    Raises ValueError on bad content. Overwrites any previous logo."""
    head = file_storage.read(16)
    file_storage.seek(0)
    ext = sniff_logo_ext(head)
    if ext is None:
        raise ValueError("Logo must be a PNG, JPEG, GIF, or WebP image.")
    # Remove old logos (any allowed extension)
    for old_ext in (".png", ".jpg", ".gif", ".webp"):
        old = os.path.join(data_dir, f"logo{old_ext}")
        if os.path.exists(old):
            os.remove(old)
    filename = f"logo{ext}"
    file_storage.save(os.path.join(data_dir, filename))
    return filename


def remove_logo(data_dir):
    """Delete any stored logo file."""
    for ext in (".png", ".jpg", ".gif", ".webp"):
        path = os.path.join(data_dir, f"logo{ext}")
        if os.path.exists(path):
            os.remove(path)


def admin_required(f):
    """Decorator: reject non-admin users with 403."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)

    return decorated


def get_setting(key, default=None):
    """Read a setting value from the DB, falling back to *default*."""
    setting = db.session.get(Setting, key)
    if setting is None:
        return default
    return setting.value


def set_setting(key, value):
    """Upsert a setting."""
    setting = db.session.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value=str(value) if value is not None else "")
        db.session.add(setting)
    else:
        setting.value = str(value) if value is not None else ""
    db.session.commit()


def user_score(user):
    """Total points from distinct solved challenges. Points count once per solved
    challenge regardless of how many times the same flag was submitted."""
    solved_challenge_ids = select(Submission.challenge_id).where(
        Submission.user_id == user.id,
        Submission.is_correct == True,  # noqa: E712
    ).distinct()
    result = (
        db.session.query(func.sum(Challenge.points))
        .filter(Challenge.id.in_(solved_challenge_ids))
        .scalar()
    )
    return result or 0


def compare_flag(submitted, stored):
    """Constant-time flag comparison after trimming."""
    return hmac.compare_digest(submitted.strip(), stored.strip())
