import os
from flask import Flask
from config import Config
from extensions import db, login_manager, csrf, limiter


def create_app():
    Config.validate()

    app = Flask(__name__)
    app.config.from_object(Config)

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
        return {
            "get_setting": get_setting,
            "user_score": user_score,
        }

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
