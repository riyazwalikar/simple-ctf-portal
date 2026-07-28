from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    abort,
)
from flask_login import login_required, current_user
from models import Challenge, Submission, User
from extensions import db, limiter
from utils import get_setting, user_score, compare_flag
from sqlalchemy import func

student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@login_required
def dashboard():
    challenges = (
        Challenge.query.filter_by(is_active=True)
        .order_by(Challenge.sort_order, Challenge.id)
        .all()
    )

    # Which challenges has the current user solved?
    solved_ids = set(
        row[0]
        for row in db.session.query(Submission.challenge_id)
        .filter(
            Submission.user_id == current_user.id,
            Submission.is_correct == True,  # noqa: E712
        )
        .all()
    )

    score = user_score(current_user)
    return render_template(
        "dashboard.html",
        challenges=challenges,
        solved_ids=solved_ids,
        score=score,
    )


@student_bp.route("/challenges/<int:cid>/submit", methods=["POST"])
@login_required
@limiter.limit("20 per minute", key_func=lambda: str(current_user.id))
def submit_flag(cid):
    challenge = Challenge.query.get_or_404(cid)

    if not challenge.is_active:
        abort(404)

    flag = request.form.get("flag", "").strip()

    if not flag or len(flag) > 512:
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if is_ajax:
            return jsonify({"result": "error", "message": "Invalid flag."}), 400
        flash("Invalid flag submission.", "error")
        return redirect(url_for("student.dashboard"))

    # Check if already solved
    already_solved = Submission.query.filter_by(
        user_id=current_user.id,
        challenge_id=cid,
        is_correct=True,
    ).first()

    correct = compare_flag(flag, challenge.flag)

    if already_solved:
        # Store audit submission but don't double-count
        submission = Submission(
            user_id=current_user.id,
            challenge_id=cid,
            submitted_flag=flag,
            is_correct=correct,
        )
        db.session.add(submission)
        db.session.commit()
        score = user_score(current_user)
        return _submit_response("already_solved", score, cid)

    submission = Submission(
        user_id=current_user.id,
        challenge_id=cid,
        submitted_flag=flag,
        is_correct=correct,
    )
    db.session.add(submission)
    db.session.commit()

    score = user_score(current_user)
    if correct:
        return _submit_response("correct", score, cid)
    else:
        return _submit_response("incorrect", score, cid)


def _submit_response(result, score, cid):
    """Return JSON for AJAX or redirect for no-JS form fallback."""
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if is_ajax:
        return jsonify({"result": result, "score": score, "challenge_id": cid})

    messages = {
        "correct": "Correct! Challenge solved.",
        "incorrect": "Incorrect flag.",
        "already_solved": "You have already solved this challenge.",
    }
    flash(messages.get(result, ""), "success" if result == "correct" else "info")
    return redirect(url_for("student.dashboard"))


@student_bp.route("/scoreboard")
def scoreboard():
    if get_setting("scoreboard_enabled", "false") != "true":
        abort(404)

    # Get all students with their scores
    users = User.query.filter_by(role="student", is_active=True).all()
    scores = []
    for u in users:
        s = user_score(u)
        # Tiebreak: time of the user's LAST first-solve. Re-submits of an
        # already-solved challenge must not skew it, so take each challenge's
        # earliest correct submission, then the max of those.
        first_solves = (
            db.session.query(func.min(Submission.submitted_at).label("first_solve"))
            .filter(
                Submission.user_id == u.id,
                Submission.is_correct == True,  # noqa: E712
            )
            .group_by(Submission.challenge_id)
            .subquery()
        )
        last_solve = db.session.query(
            func.max(first_solves.c.first_solve)
        ).scalar()
        scores.append(
            {
                "display_name": u.display_name or u.username,
                "score": s,
                "last_solve": last_solve,
            }
        )

    # Rank: score desc, then earliest last-solve (None sorts last)
    scores.sort(key=lambda x: (-x["score"], x["last_solve"] is None, x["last_solve"] or ""))
    return render_template("scoreboard.html", scores=scores)
