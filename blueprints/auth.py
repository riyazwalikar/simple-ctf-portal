from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy.exc import IntegrityError
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, Regexp
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from extensions import db, limiter
from utils import get_setting

auth_bp = Blueprint("auth", __name__)


def is_safe_redirect(target):
    """Only allow local, relative redirect targets (no //host, no schemes)."""
    if not target:
        return False
    parsed = urlparse(target)
    return (
        not parsed.scheme
        and not parsed.netloc
        and target.startswith("/")
        and not target.startswith("//")
    )


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=32),
            Regexp(
                r"^[A-Za-z0-9_.-]+$",
                message="Letters, digits, dot, dash, underscore only.",
            ),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    display_name = StringField("Display Name", validators=[Optional(), Length(max=64)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8)]
    )
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    registration_code = StringField("Registration Code", validators=[Optional()])

    def validate_registration_code(self, field):
        required_code = get_setting("registration_code", "")
        if required_code and field.data != required_code:
            from wtforms.validators import ValidationError

            raise ValidationError("Invalid registration code.")


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    if get_setting("registration_open", "true") != "true":
        flash("Registration is currently closed.", "error")
        return redirect(url_for("auth.login"))

    code_required = bool(get_setting("registration_code", ""))
    form = RegistrationForm()
    # Only validate registration code if one is required
    if not code_required:
        del form.registration_code

    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            form.username.errors.append("Username already taken.")
        if existing_email:
            form.email.errors.append("Email already registered.")
        if existing_user or existing_email:
            return render_template(
                "auth/register.html", form=form, code_required=code_required
            )

        user = User(
            username=form.username.data,
            email=form.email.data,
            display_name=form.display_name.data or None,
            password_hash=generate_password_hash(form.password.data),
            role="student",
            is_active=True,
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Username or email already registered.", "error")
            return render_template(
                "auth/register.html", form=form, code_required=code_required
            )
        login_user(user)
        flash("Registration successful. Welcome!", "success")
        return redirect(url_for("student.dashboard"))

    return render_template(
        "auth/register.html", form=form, code_required=code_required
    )


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        # Generic error - don't distinguish "no such user" from "wrong password"
        if user is None or not check_password_hash(user.password_hash, form.password.data):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html", form=form)

        if not user.is_active:
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html", form=form)

        login_user(user)
        flash("Logged in successfully.", "success")
        next_page = request.args.get("next")
        if is_safe_redirect(next_page):
            return redirect(next_page)
        return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
