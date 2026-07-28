import os

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from sqlalchemy.exc import IntegrityError
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    IntegerField,
    BooleanField,
    SelectField,
)
from wtforms.validators import DataRequired, Length, Email, Optional, NumberRange
from werkzeug.security import generate_password_hash
from defaults import DEFAULT_SETTINGS, SAMPLE_CHALLENGES
from models import User, Challenge, Submission
from extensions import db
from utils import (
    admin_required,
    get_setting,
    set_setting,
    user_score,
    save_logo,
    remove_logo,
)
from sqlalchemy import desc, func

admin_bp = Blueprint("admin", __name__)


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class ChallengeForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    category = StringField("Category", validators=[Optional(), Length(max=64)])
    description = TextAreaField("Description", validators=[DataRequired()])
    starting_points = TextAreaField("Starting Points", validators=[Optional()])
    points = IntegerField("Points", validators=[DataRequired(), NumberRange(min=1)])
    flag = StringField("Flag", validators=[DataRequired(), Length(max=512)])
    sort_order = IntegerField("Sort Order", validators=[Optional()], default=0)
    is_active = BooleanField("Active", default=True)


class UserCreateForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=32)]
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    display_name = StringField("Display Name", validators=[Optional(), Length(max=64)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8)]
    )
    role = SelectField("Role", choices=[("student", "Student"), ("admin", "Admin")])
    is_active = BooleanField("Active", default=True)


class UserEditForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=32)]
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    display_name = StringField("Display Name", validators=[Optional(), Length(max=64)])
    role = SelectField("Role", choices=[("student", "Student"), ("admin", "Admin")])
    is_active = BooleanField("Active", default=True)


class UserResetPasswordForm(FlaskForm):
    new_password = PasswordField(
        "New Password", validators=[DataRequired(), Length(min=8)]
    )


class SettingsForm(FlaskForm):
    portal_title = StringField("Portal Title", validators=[DataRequired(), Length(max=255)])
    portal_subtitle = StringField("Portal Subtitle", validators=[Optional(), Length(max=255)])
    footer_text = StringField("Footer Text", validators=[Optional(), Length(max=255)])
    logo = FileField("Logo (PNG, JPEG, GIF, WebP; max 2MB)", validators=[Optional()])
    remove_logo = BooleanField("Remove current logo")
    registration_open = BooleanField("Registration Open")
    registration_code = StringField("Registration Code", validators=[Optional(), Length(max=64)])
    scoreboard_enabled = BooleanField("Scoreboard Enabled")


class DeleteForm(FlaskForm):
    pass  # CSRF protection only


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@admin_bp.route("/")
@admin_required
def dashboard():
    user_count = User.query.count()
    challenge_count = Challenge.query.count()
    # Distinct solved (user, challenge) pairs; re-submits don't inflate the count
    distinct_solves = (
        db.session.query(Submission.user_id, Submission.challenge_id)
        .filter(Submission.is_correct == True)  # noqa: E712
        .distinct()
        .subquery()
    )
    solve_count = db.session.query(func.count()).select_from(distinct_solves).scalar()

    recent = (
        Submission.query.order_by(desc(Submission.submitted_at))
        .limit(20)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        user_count=user_count,
        challenge_count=challenge_count,
        solve_count=solve_count,
        recent_submissions=recent,
    )


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

@admin_bp.route("/challenges")
@admin_required
def challenges():
    challenges = Challenge.query.order_by(Challenge.sort_order, Challenge.id).all()
    return render_template("admin/challenges.html", challenges=challenges)


@admin_bp.route("/challenges/new", methods=["GET", "POST"])
@admin_required
def challenge_new():
    form = ChallengeForm()
    if form.validate_on_submit():
        challenge = Challenge(
            title=form.title.data,
            category=form.category.data or None,
            description=form.description.data,
            starting_points=form.starting_points.data or None,
            points=form.points.data,
            flag=form.flag.data,
            sort_order=form.sort_order.data or 0,
            is_active=form.is_active.data,
        )
        db.session.add(challenge)
        db.session.commit()
        flash("Challenge created.", "success")
        return redirect(url_for("admin.challenges"))
    return render_template("admin/challenge_form.html", form=form, editing=False)


@admin_bp.route("/challenges/<int:cid>/edit", methods=["GET", "POST"])
@admin_required
def challenge_edit(cid):
    challenge = Challenge.query.get_or_404(cid)
    form = ChallengeForm(obj=challenge)
    if form.validate_on_submit():
        form.populate_obj(challenge)
        if not form.category.data:
            challenge.category = None
        if not form.starting_points.data:
            challenge.starting_points = None
        db.session.commit()
        flash("Challenge updated.", "success")
        return redirect(url_for("admin.challenges"))
    return render_template("admin/challenge_form.html", form=form, editing=True)


@admin_bp.route("/challenges/<int:cid>/delete", methods=["POST"])
@admin_required
def challenge_delete(cid):
    challenge = Challenge.query.get_or_404(cid)
    # Remove dependent submissions first (no FK cascade in SQLite by default)
    Submission.query.filter_by(challenge_id=cid).delete()
    db.session.delete(challenge)
    db.session.commit()
    flash("Challenge deleted.", "success")
    return redirect(url_for("admin.challenges"))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@admin_bp.route("/users")
@admin_required
def users():
    users = User.query.order_by(User.id).all()
    scores = {u.id: user_score(u) for u in users}
    return render_template("admin/users.html", users=users, scores=scores)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def user_new():
    form = UserCreateForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            form.username.errors.append("Username already taken.")
        if existing_email:
            form.email.errors.append("Email already registered.")
        if existing_user or existing_email:
            return render_template("admin/user_form.html", form=form, editing=False)

        user = User(
            username=form.username.data,
            email=form.email.data,
            display_name=form.display_name.data or None,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data,
            is_active=form.is_active.data,
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Username or email already registered.", "error")
            return render_template("admin/user_form.html", form=form, editing=False)
        flash("User created.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, editing=False)


@admin_bp.route("/users/<int:uid>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(uid):
    user = User.query.get_or_404(uid)
    form = UserEditForm(obj=user)
    if form.validate_on_submit():
        existing_user = User.query.filter(
            User.username == form.username.data, User.id != uid
        ).first()
        existing_email = User.query.filter(
            User.email == form.email.data, User.id != uid
        ).first()
        if existing_user:
            form.username.errors.append("Username already taken.")
        if existing_email:
            form.email.errors.append("Email already registered.")
        if existing_user or existing_email:
            return render_template(
                "admin/user_form.html", form=form, editing=True, user=user
            )

        # Guard: an admin cannot demote or deactivate their own account
        if user.id == current_user.id:
            form.role.data = user.role
            form.is_active.data = user.is_active
        form.populate_obj(user)
        if not form.display_name.data:
            user.display_name = None
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, editing=True, user=user)


@admin_bp.route("/users/<int:uid>/reset-password", methods=["POST"])
@admin_required
def user_reset_password(uid):
    user = User.query.get_or_404(uid)
    form = UserResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash(f"Password reset for {user.username}.", "success")
    else:
        flash("Invalid password.", "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:uid>/delete", methods=["POST"])
@admin_required
def user_delete(uid):
    user = User.query.get_or_404(uid)

    # Prevent self-deletion
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))

    # Remove dependent submissions first (no FK cascade in SQLite by default)
    Submission.query.filter_by(user_id=uid).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} deleted.", "success")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    form = SettingsForm()
    if form.validate_on_submit():
        set_setting("portal_title", form.portal_title.data)
        set_setting("portal_subtitle", form.portal_subtitle.data)
        set_setting("footer_text", form.footer_text.data or "")
        set_setting("registration_open", "true" if form.registration_open.data else "false")
        set_setting("registration_code", form.registration_code.data or "")
        set_setting(
            "scoreboard_enabled", "true" if form.scoreboard_enabled.data else "false"
        )

        data_dir = os.path.join(current_app.root_path, "data")
        if form.remove_logo.data:
            remove_logo(data_dir)
            set_setting("logo_filename", "")
        elif form.logo.data:
            try:
                filename = save_logo(form.logo.data, data_dir)
                set_setting("logo_filename", filename)
            except ValueError as e:
                flash(str(e), "error")
                return redirect(url_for("admin.settings"))

        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))

    # Pre-populate
    if request.method == "GET":
        form.portal_title.data = get_setting(
            "portal_title", "Exam and CTF Portal"
        )
        form.portal_subtitle.data = get_setting("portal_subtitle", "")
        form.footer_text.data = get_setting("footer_text", "Build Break Repeat")
        form.registration_open.data = get_setting("registration_open", "true") == "true"
        form.registration_code.data = get_setting("registration_code", "")
        form.scoreboard_enabled.data = (
            get_setting("scoreboard_enabled", "false") == "true"
        )

    return render_template("admin/settings.html", form=form)


# ---------------------------------------------------------------------------
# Scoreboard (admin view: totals + per-category top scorers)
# ---------------------------------------------------------------------------

@admin_bp.route("/scoreboard")
@admin_required
def scoreboard():
    sort = request.args.get("sort", "desc")
    if sort not in ("asc", "desc"):
        sort = "desc"
    selected_category = request.args.get("category", "")

    categories = [
        row[0]
        for row in db.session.query(Challenge.category).distinct().all()
        if row[0]
    ]
    categories.sort()

    students = User.query.filter_by(role="student").order_by(User.id).all()
    rows = []
    for u in students:
        # Distinct solved challenges for this user
        solved = (
            Challenge.query.join(Submission, Submission.challenge_id == Challenge.id)
            .filter(
                Submission.user_id == u.id,
                Submission.is_correct == True,  # noqa: E712
            )
            .group_by(Challenge.id)
            .all()
        )
        per_category = {}
        for chal in solved:
            key = chal.category or "Uncategorized"
            per_category[key] = per_category.get(key, 0) + chal.points
        total = sum(per_category.values())
        rows.append(
            {
                "username": u.username,
                "display_name": u.display_name or u.username,
                "total": total,
                "per_category": per_category,
            }
        )

    if selected_category:
        # Top scorers in one category: only users with points there
        rows = [r for r in rows if r["per_category"].get(selected_category, 0) > 0]
        rows.sort(
            key=lambda r: r["per_category"][selected_category],
            reverse=(sort == "desc"),
        )
    else:
        rows.sort(key=lambda r: r["total"], reverse=(sort == "desc"))

    return render_template(
        "admin/scoreboard.html",
        rows=rows,
        categories=categories,
        selected_category=selected_category,
        sort=sort,
    )


# ---------------------------------------------------------------------------
# Reset to defaults
# ---------------------------------------------------------------------------

@admin_bp.route("/reset", methods=["POST"])
@admin_required
def reset_portal():
    """Wipe students, challenges, and submissions; restore default settings
    and re-seed the sample challenges. Admin accounts are preserved so the
    current session stays valid."""
    Submission.query.delete()
    Challenge.query.delete()
    User.query.filter(User.role != "admin").delete()

    for key, value in DEFAULT_SETTINGS.items():
        set_setting(key, value)

    remove_logo(os.path.join(current_app.root_path, "data"))

    for data in SAMPLE_CHALLENGES:
        db.session.add(Challenge(**data))

    db.session.commit()
    flash(
        "Portal reset to defaults. Students, challenges, and submissions wiped; "
        "sample challenges restored. Admin accounts unchanged.",
        "success",
    )
    return redirect(url_for("admin.settings"))
