"""First-run bootstrap: create tables, admin user, settings, and sample challenges.

Run once before first start. Idempotent where reasonable.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from defaults import DEFAULT_SETTINGS, SAMPLE_CHALLENGES
from extensions import db
from models import User, Challenge, Setting
from werkzeug.security import generate_password_hash

app = create_app()


def seed():
    with app.app_context():
        db.create_all()

        # Create admin user
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "change-me")

        existing = User.query.filter_by(username=admin_username).first()
        if not existing:
            admin = User(
                username=admin_username,
                email=admin_email,
                display_name="Administrator",
                password_hash=generate_password_hash(admin_password),
                role="admin",
                is_active=True,
            )
            db.session.add(admin)
            print(f"Created admin user: {admin_username}")
        else:
            print(f"Admin user '{admin_username}' already exists. Skipping.")

        # Insert default settings
        for key, value in DEFAULT_SETTINGS.items():
            if db.session.get(Setting, key) is None:
                db.session.add(Setting(key=key, value=value))
                print(f"Inserted setting: {key}")
            else:
                print(f"Setting '{key}' already exists. Skipping.")

        # Insert sample challenges
        for data in SAMPLE_CHALLENGES:
            existing_chal = Challenge.query.filter_by(title=data["title"]).first()
            if not existing_chal:
                db.session.add(Challenge(**data))
                print(f"Created sample challenge: {data['title']}")
            else:
                print(f"Challenge '{data['title']}' already exists. Skipping.")

        db.session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    seed()
