import os
from flask import Flask, abort
from config import Config
from extensions import db, login_manager, csrf, limiter


def create_app():
    Config.validate()

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB (logo uploads)

    # ProxyFix when behind TLS reverse proxy
    if app.config["SESSION_COOKIE_SECURE"]:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        # Returning None for deactivated users kills their existing sessions
        user = db.session.get(User, int(user_id))
        if user is None or not user.is_active:
            return None
        return user

    # Context processors for templates
    from utils import get_setting, user_score

    @app.context_processor
    def inject_helpers():
        logo_filename = get_setting("logo_filename", "")
        logo_dark_path = os.path.join(app.root_path, "data", "logo-dark.png")
        return {
            "get_setting": get_setting,
            "user_score": user_score,
            "logo_filename": logo_filename,
            "logo_dark_available": os.path.exists(logo_dark_path),
        }

    @app.route("/logo")
    def logo():
        """Serve the admin-uploaded logo from the data directory."""
        from flask import send_from_directory

        filename = get_setting("logo_filename", "")
        if not filename:
            abort(404)
        data_dir = os.path.join(app.root_path, "data")
        return send_from_directory(data_dir, filename)

    @app.route("/logo-dark")
    def logo_dark():
        """Serve the light-mode (dark-colored) logo variant, if present."""
        from flask import send_from_directory

        data_dir = os.path.join(app.root_path, "data")
        if not os.path.exists(os.path.join(data_dir, "logo-dark.png")):
            abort(404)
        return send_from_directory(data_dir, "logo-dark.png")

    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.student import student_bp
    from blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Create data directory and tables on first request if needed
    with app.app_context():
        import os as _os

        data_dir = _os.path.join(app.root_path, "data")
        _os.makedirs(data_dir, exist_ok=True)
        db.create_all()

        # First-boot auto-seed: if no admin exists (fresh deploy, seed.py
        # never run), bootstrap admin + settings + sample challenges.
        # Idempotent — seed() skips anything that already exists.
        if not User.query.filter_by(role="admin").first():
            from seed import seed

            seed(app)
            print("First boot: no admin user found — seeded admin, settings, sample challenges.")

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
