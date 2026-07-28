# Simple CTF Portal

Self-contained flag-submission portal for hands-on security exams and CTFs. Students register, read challenge descriptions, and submit flags; correct submissions mark challenges solved and award points. Admins manage challenges, users, branding, and portal resets entirely through the web UI.

**Stack:** Python 3.11+, Flask, SQLAlchemy, SQLite. Single process, zero external dependencies at runtime (no CDNs, no fonts, no external JS/CSS).

## Quick Start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set SECRET_KEY and ADMIN_PASSWORD
python seed.py
python app.py
```

App serves on `0.0.0.0:5000` (set `PORT` env to override).

## Deploying (Railway, etc.)

- Set env vars: `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`. Optional: `SESSION_COOKIE_SECURE=true` (TLS), `DATABASE_URL`.
- **First boot auto-seeds**: if no admin user exists, the app creates the admin (from env), default settings, and sample challenges automatically. `python seed.py` is only needed locally.
- **SQLite is ephemeral in containers.** Without a persistent volume, every redeploy/restart wipes the database. On Railway: add a Volume mounted at `/app/data` (the default `DATABASE_URL` resolves there). Change `DATABASE_URL` if your mount path differs.

## Reset Everything

From the shell:

```bash
rm -f data/portal.db && python seed.py
```

From the web UI: `/admin/settings` → **Danger Zone → Reset Portal to Defaults**. Wipes students, challenges, and submissions; restores default branding/toggles; re-seeds the sample challenges. Admin accounts are preserved and your session survives.

## Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | — | **Required.** Long random value. |
| `DATABASE_URL` | `sqlite:///data/portal.db` | Relative paths resolved from project root. |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` behind TLS reverse proxy. |
| `FLASK_DEBUG` | `0` | Set `1` for development. |
| `ADMIN_USERNAME` | `admin` | First-run admin (seed only). |
| `ADMIN_PASSWORD` | `change-me` | First-run admin password (seed only). |
| `ADMIN_EMAIL` | `admin@example.com` | First-run admin email (seed only). |
| `PORT` | `5000` | Listen port. |
| `HOST` | `0.0.0.0` | Listen address. |

## Roles

- **Student** — self-registration (if open; optional registration code). View challenges, submit flags, see scoreboard (if enabled).
- **Admin** — manage challenges, users, settings, and portal reset through `/admin`. First admin created by `seed.py`.

## Features

- Challenge accordion with per-challenge solved state, points, and starting points
- Async flag submission (no page reload) with a full no-JS form fallback
- Derived scoring — points counted once per solved challenge, no double-counting
- Optional scoreboard (admin-toggled) ranked by score, then earliest last-solve
- Runtime-editable branding (title/subtitle) and registration toggle/code
- One-click reset to defaults from the admin UI
- Dark, terminal-adjacent theme; responsive to ~360px; keyboard-accessible accordion; `prefers-reduced-motion` respected

## Security

- Passwords hashed with Werkzeug (scrypt)
- Flag comparison via `hmac.compare_digest` (constant-time); flags never leave the server
- CSRF protection on every state-changing POST (Flask-WTF)
- Admin routes return 403 for non-admin users
- Generic auth error messages (no user enumeration)
- Login redirect targets restricted to relative paths (no open redirect)
- Deactivating a user invalidates their sessions immediately
- No user-controlled data in inline-JS contexts; username charset restricted
- Session cookies: `HttpOnly`, `SameSite=Lax`, `Secure` behind TLS
- Rate limiting on login (per-IP) and flag submission (per-user)
- Zero external network requests at runtime

## Project Structure

```
├── app.py              # App factory + entrypoint
├── config.py           # Config from env
├── defaults.py         # Default settings + sample challenges (seed + admin reset)
├── extensions.py       # db, login_manager, csrf, limiter
├── models.py           # User, Challenge, Submission, Setting
├── utils.py            # Decorators, flag compare, settings helpers
├── seed.py             # First-run bootstrap
├── blueprints/
│   ├── auth.py         # Register, login, logout
│   ├── student.py      # Dashboard, flag submission, scoreboard
│   └── admin.py        # CRUD: challenges, users, settings, portal reset
├── templates/          # Jinja2 server-rendered
├── static/
│   ├── css/styles.css  # Dark theme, custom properties
│   └── js/app.js       # Accordion + async flag submission
└── data/portal.db      # SQLite database (gitignored)
```

## License

MIT — see [LICENSE](LICENSE). Build Break Repeat.
