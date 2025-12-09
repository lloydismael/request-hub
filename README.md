# Request Hub

Request Hub is a role-based request management portal for coordinating work between requestors, engineers, and administrators.

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
- Admin (secondary): `Admin1` / `Admin1`
- Engineer: `Admin` / `Admin`
- Engineer (alternate): `Admin1` / `Admin1`
- Requestor: `Admin` / `Admin`
- Requestor (alternate): `Admin1` / `Admin1`

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

### Docker Image Versioning

- The current published image version is `v9.1`.
- Increment patch versions sequentially: `v9.1`, `v9.2`, … up to `v9.9`.
- After `v9.9`, bump the major version and reset the patch: `v10.0`.
- Avoid tags such as `v9.10` or `v9.11`; each series only goes up to `.9`.
- Before building, confirm the latest pushed tag (e.g., `docker images lloydismael12/request-hub --format "{{.Tag}}" | sort`) to avoid rebuilding an existing version.
- Continue tagging `latest` alongside the specific version when pushing to the registry.

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
