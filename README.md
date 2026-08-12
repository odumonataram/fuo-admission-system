# Federal University Otuoke — Computerized Student Admission System
### with QR Code-Based Admission Letter Verification

B.Sc. Computer Science Final Year Project — Federal University Otuoke, Bayelsa State.

---

## ✅ Completed phases

**Phase 1 —** Application factory, all 16 database tables, 10 blueprints, full public marketing site.

**Phase 2 —** Auth blueprint: registration, login with account lockout, forgot/reset password, change password, audit logging, email service.

**Phase 3 —** Applicant blueprint:
- Dashboard with live checklist and application status
- Profile editor with passport photo upload
- Application form: cascading Faculty → Department → Programme dropdowns (AJAX), UTME details (4 subjects), O'Level results (9 rows, server-side validated for 5 credits including English & Maths)
- Document upload (O'Level result, UTME slip, birth certificate, LGA certificate) with file type/size validation
- Preview page showing everything before submission
- Submit flow: validates full completeness, assigns real application number, locks the application from further edits
- Status tracking page with a visual progress tracker
- All flows verified end-to-end via automated test-client runs (registration → profile → programme selection → academic details → documents → preview → submit → status → edit-lock)

**Phase 4 —** Administrator blueprint:
- Sidebar-navigated admin console
- Dashboard with stats cards (total/pending/approved/rejected/letters/verifications) and Chart.js visualizations (monthly applications line chart, faculty doughnut chart)
- Manage Applicants: search by name/email/application number, filter by status/faculty/session, pagination
- Applicant detail view: full profile, UTME/O'Level breakdown, documents, auto-transitions to "under review" when an officer opens it
- Approve/reject decision flow with remarks, in-app notifications sent to the applicant, audit logging
- Full CRUD for faculties, departments, programmes, and academic sessions (with "set as current session")
- Staff account management (super admin only): create admin/registrar/super-admin accounts, activate/deactivate
- All flows verified end-to-end: admin login → academic structure setup → applicant submits → admin reviews → approve/reject → applicant sees updated status → staff account creation

## 🚧 Coming in later phases

| Phase | Contents |
|---|---|
| 5 | Admission processing: QR code generation, PDF admission letter (WeasyPrint) |
| 6 | Verification blueprint: public QR-scan page, verification logging |
| 7 | Reports (PDF/Excel/CSV), audit log viewer, settings, notifications |
| 8 | Security hardening pass, seed data, deployment guide |

---

## Quick start (recommended for development)

No MySQL, no manual migrations, no configuration needed — just:

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

That's it. On first run, `app.py` automatically:
- creates a `.env` file with a generated `SECRET_KEY`
- creates a local SQLite database at `instance/app.db`
- creates all tables
- seeds default roles (applicant, admin, super_admin, registrar)
- seeds a starter faculty/department/programme so the site isn't empty

Every time you run `python app.py` after that, it reuses the same database
and just starts the server — nothing gets re-seeded or wiped.

To create a super-admin account so you can log into the admin dashboard
once it's built (Phase 4), run:
```bash
flask --app wsgi.py create-super-admin
```

---

## Advanced setup (MySQL, for production/deployment)

<details>
<summary>Click to expand</summary>

### 1. Install full dependencies (includes MySQL driver, PDF/QR libs added in later phases)
```bash
pip install -r requirements.txt -r requirements-later-phases.txt
```

### 2. Create the MySQL database
```sql
CREATE DATABASE fuo_admission_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'admission_user'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON fuo_admission_system.* TO 'admission_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Configure `.env`
```bash
cp .env.example .env
```
Edit `.env`: set `DB_ENGINE=mysql+pymysql` and fill in `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`.

### 4. Run migrations
```bash
export FLASK_APP=wsgi.py
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
flask seed-roles
flask seed-academic-structure
flask create-super-admin
```

### 5. Run with a production WSGI server
```bash
gunicorn wsgi:app
```

> **Note on WeasyPrint (Phase 5):** it depends on system libraries (Pango, Cairo).
> Ubuntu: `sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0`
> macOS: `brew install pango`

</details>

---

## Project structure

```
admission_system/
├── app/
│   ├── __init__.py              # Application factory
│   ├── extensions.py            # db, migrate, login_manager, csrf, mail, limiter
│   ├── models/                  # SQLAlchemy models (one file per domain)
│   ├── blueprints/              # One folder per blueprint (routes.py, forms.py, services.py)
│   ├── templates/                # Jinja2 templates, mirrors blueprint structure
│   ├── static/                   # css/, js/, img/, uploads/
│   ├── services/                 # Business logic (QR generation, PDF generation, etc.)
│   └── utils/                     # CLI commands, helpers, decorators
├── migrations/                   # Flask-Migrate (Alembic) migration scripts
├── config.py                     # Environment-based configuration
├── wsgi.py                       # Production entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Security notes (implemented so far)

- Passwords hashed with Werkzeug's `generate_password_hash` (never stored in plaintext)
- CSRF protection enabled globally via Flask-WTF
- Account lockout after repeated failed logins (`User.register_failed_login`)
- QR codes will only ever encode `https://domain/verify/<uuid-token>` — **no personal
  data is ever embedded in a QR code**; all applicant details are looked up
  server-side from the token at verification time
- Every verification attempt (valid or invalid) is logged with IP, browser, and timestamp
