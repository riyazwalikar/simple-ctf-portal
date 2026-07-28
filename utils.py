import hmac
from functools import wraps
from flask import abort
from flask_login import current_user
from sqlalchemy import func, select
from models import Setting, Submission, Challenge
from extensions import db


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
