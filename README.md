# Request Hub

Request Hub is a role-based request management portal for coordinating work between account managers, engineers, and administrators.

## Features

- Custom user roles (Requestor, Engineer, Admin) with first-login profile completion.
- Ticket lifecycle with SLA tracking, engineer capacity guardrails, and completion notifications.
- Admin dashboard for status control and SLA oversight.
- Configurable notification center and nightly SLA checker management command.
- Responsive UI with a modern glassmorphism-inspired design.

## Quick Start (Local)

1. Create a virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set values as needed.
3. Apply migrations (default users are created via data migration):
   ```powershell
   python manage.py migrate
   ```
4. Run the development server:
   ```powershell
   python manage.py runserver
   ```

Quick-start demo credentials (per role selection):
- Admin: `Admin` / `Admin`
- Engineer: `Admin` / `Admin`
- Account manager: `Admin` / `Admin`

Additional seeded requestors and engineers remain available with the password `RequestHub123`. Update all passwords immediately after first login.

## Docker

1. Build and start the stack:
   ```powershell
   docker compose up --build
   ```
2. Apply migrations inside the `web` container if needed:
   ```powershell
   docker compose exec web python manage.py migrate
   ```

## Tests

Run the Django test suite:
```powershell
python manage.py test
```

## Scheduled Tasks

Use the provided management command to monitor SLA breaches:
```powershell
docker compose exec web python manage.py check_sla
```
Schedule this command (e.g., Windows Task Scheduler, cron) to run daily.

## Azure App Service

Refer to `docs/azure-app-service-deployment.md` for container deployment steps, recommended App Service settings, and CLI snippets.
