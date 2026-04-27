# Request Hub

Request Hub is a role-based request and activity management platform built with Django. It helps requestors, engineers, and administrators coordinate work, track SLA timelines, and monitor operational progress from a single web portal.

![Request Hub Logo](static/img/phil-data-full-logo.png)

**Current image:** `lloydismael12/request-hub:v29.0`

---

## Table of Contents

- [Overview](#overview)
- [User Roles](#user-roles)
- [Core Features](#core-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [URL Map](#url-map)
- [Local Development Setup](#local-development-setup)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [Database and Migrations](#database-and-migrations)
- [Running Tests](#running-tests)
- [Scheduled Jobs](#scheduled-jobs)
- [Deployment](#deployment)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)

---

## Overview

Request Hub is a full-stack Django web application that serves as a centralised operations hub for managing service requests, engineer workloads, and activity reporting. It enforces role-based access control so each user type sees only what they need.

Key capabilities:

- Role-aware dashboards tailored per user type
- Full request lifecycle management (creation → in-progress → completion)
- SLA monitoring with overdue visibility and nudge actions
- Engineer activity logging with billable/non-billable tracking
- Operational and activity reports with Chart.js visualisations and CSV export
- In-app notifications and Microsoft 365 integrations (Teams, Outlook)
- Dark mode and responsive UI built on Bootstrap 5 + custom CSS

---

## User Roles

| Role | Label | Access Level |
|---|---|---|
| `admin` | Admin | Full access — manage all requests, users, SQR, reports |
| `pm_esg` | PM-ESG | Admin-equivalent with collaborative request management |
| `pm_ess` | PM-ESS | Requestor view + "All Requests" tab + report graph |
| `engineer` | Engineer | Assigned/backup request views + activity log + SQR |
| `on_hold` | On Hold | Read-only engineer view (no new assignments) |
| `requestor` | Requestor | Create and track own requests |
| `requestor_ess` | Requestor-ESS | Requestor with ESS-specific scoping |

---

## Core Features

### Dashboards

- **Admin / PM-ESG**: Full request table with sorting, filtering, SLA indicators, stat pills (All / Ongoing / Completed / Overdue), and Export CSV
- **Engineer**: Tabs for Assigned Requests, Backup Requests, and Report Request Graph
- **PM-ESS**: All Requests + My Requests tabs with report graph
- **Requestor / Requestor-ESS**: Personal request summary metrics, request list, and New Request button

### Request Management

- Create requests with title, description, engagement type, priority, product category, due date, and file attachments
- Assign primary engineer and backup engineer
- Role-gated status updates, admin manage form, and collaborative manage form
- Nudge action to prompt engineer updates via email/Teams
- Delete requests (admin only)
- Export all requests to CSV

### Activity Logs

- Engineers log work entries: date, account, activity type, location, hours, billable flag, and notes
- Activity log view with pagination
- Inline edit and delete

### Reports

Two report views accessible at `/reports/`:

**Operational tab**
- KPI cards (Active Requests, Completed, Requestors, Engineers)
- Charts: Requests by Requestor, Requests by Engineer, Engagement Types, Product Categories
- Breakdown tables: Requestor Breakdown, Engineer Allocation
- Request Status Overview chips

**Activity Logs tab**
- KPI cards (Log Entries, Total Hours, Billable Hours, Accounts)
- Charts: Hours by Engineer, Hours by Activity Type, Work Location Mix, Billable Distribution
- Breakdown tables: Engineer Hour Breakdown, Activity Type Breakdown
- Recent Engineer Activity log table with pagination and inline edit
- Month range filter

All charts support **expand to full-screen** via the `⛶` button on each chart card.
Both tabs offer **Export CSV**.

### Notifications

- In-app notification bell with unread badge
- Mark single or all notifications read
- Follow link redirects to related request
- Delete individual notifications

### SQR (Service Quality Report)

- SQR submission list for engineers
- Engineer update and delete
- Revenue tracker update (admin)
- Approval email via Outlook redirect
- Teams redirect for SQR discussion

### User Management

- Admin-only user management view (`/management/`)
- Fetch Microsoft Graph users from the Phildata tenant

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Django ≥ 4.2, Python 3.12 |
| Database | PostgreSQL 16 (psycopg2-binary) |
| Frontend | Django Templates, Bootstrap 5.3.2, Bootstrap Icons, Chart.js 4.4 |
| Static files | WhiteNoise 6.7 |
| WSGI server | Gunicorn 23 |
| Containerisation | Docker / Docker Compose |
| Auth integrations | MSAL (Microsoft Graph), Azure Communication Services email |
| Image | `lloydismael12/request-hub` on Docker Hub |

---

## Project Structure

```text
accounts/               Custom user model, roles, auth backends, profile storage
  migrations/           Account migration history (0001 → 0014)
hub/                    Core application
  models.py             Account, Request, StatusLog, EngineerActivityLog,
                        SqrSubmission, Notification, RequestCommunication
  views.py              All CBVs (dashboard, reports, requests, SQR, management)
  forms.py              Request, activity log, SQR, and admin forms
  signals.py            Post-save signal handlers (notifications, SLA)
  urls.py               All hub URL routes
  constants.py          Shared constants (engagement types, priorities, etc.)
  mixins.py             Role-access mixins
  services/             External service clients (Microsoft Graph)
  management/commands/  Management commands (check_sla, fetch_phildata_users)
  migrations/           Hub migration history (0001 → 0024)
request_hub/            Django project settings, root URLs, ASGI/WSGI
templates/              All HTML templates
  base.html             Shared layout (navbar, notifications, dark mode toggle)
  hub/dashboard.html    Role-aware dashboard
  hub/report.html       Operational + Activity report tabs with Chart.js
  hub/request_*.html    Request detail, edit, manage, collab manage forms
  accounts/             Login, profile, password change templates
static/                 CSS (app.css), images, JS
  css/app.css           All custom styles (.glass-card, .rpt-*, .dbd-*, .rmf-*, etc.)
docs/                   Deployment documentation
```

---

## URL Map

| URL | Name | Description |
|---|---|---|
| `/` | landing | Landing / login redirect |
| `/accounts/login/` | login | Login page |
| `/dashboard/` | hub:dashboard | Role-aware dashboard |
| `/requests/<pk>/` | hub:request-detail | Request detail |
| `/requests/<pk>/edit/` | hub:request-edit | Edit request (requestor) |
| `/requests/<pk>/status/` | hub:request-status | Update request status |
| `/requests/<pk>/manage/` | hub:request-manage | Admin manage form |
| `/requests/<pk>/manage/collab/` | hub:request-manage-collab | Collaborative manage form |
| `/requests/<pk>/nudge/` | hub:request-nudge | Send nudge notification |
| `/requests/<pk>/teams-chat/` | hub:request-teams | Open Teams chat |
| `/requests/<pk>/outlook/` | hub:request-outlook | Open Outlook email |
| `/requests/<pk>/delete/` | hub:request-delete | Delete request (admin) |
| `/requests/export/csv/` | hub:request-export | Export all requests as CSV |
| `/activity-logs/` | hub:activity-logs | Engineer activity log view |
| `/notifications/` | hub:notifications | Notification list |
| `/sqr/` | hub:sqr | SQR submission list |
| `/management/` | hub:management | User management (admin) |
| `/reports/` | hub:report | Operational + Activity reports |
| `/reports/export/` | hub:report-export | Export report data as CSV |

---

## Local Development Setup

### 1. Create and activate virtual environment (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local values — database connection, secret key, and optional service credentials.

### 3. Run migrations

```powershell
python manage.py migrate
```

### 4. Start development server

```powershell
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

---

## Docker Setup

### Pull and run the published image

```powershell
docker run --rm -p 8000:8000 --env-file .env lloydismael12/request-hub:v29.0
```

### Build locally and run

```powershell
docker build -t lloydismael12/request-hub:v29.0 -t lloydismael12/request-hub:latest .
docker run --rm -p 8000:8000 --env-file .env lloydismael12/request-hub:latest
```

### Docker Compose (local with PostgreSQL)

```powershell
docker compose up --build
```

Run migrations inside the container:

```powershell
docker compose exec web python manage.py migrate
```

Stop services:

```powershell
docker compose down
```

### Image tags on Docker Hub

| Tag | Description |
|---|---|
| `latest` | Always points to the most recent release |
| `v29.0` | Current stable release |
| `v28.x` | Previous releases |

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated allowed host names |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | PostgreSQL host (e.g. `localhost` or Azure FQDN) |
| `DB_PORT` | PostgreSQL port (default `5432`) |
| `ACS_EMAIL_CONNECTION_STRING` | Azure Communication Services connection string |
| `ACS_EMAIL_SENDER` | Sender address (e.g. `DoNotReply@dreadops.site`) |
| `PHILDATA_TENANT_ID` | Microsoft Entra tenant ID |
| `PHILDATA_CLIENT_ID` | App registration client ID |
| `PHILDATA_CLIENT_SECRET` | App registration client secret |
| `PHILDATA_DOMAIN` | Default `phildata.com` |
| `PHILDATA_GRAPH_SCOPE` | Default `https://graph.microsoft.com/.default` |

> Never commit real secrets, tokens, passwords, or connection strings to source control.

---

## Database and Migrations

Apply all pending migrations:

```powershell
python manage.py migrate
```

Create new migrations after model changes:

```powershell
python manage.py makemigrations
python manage.py migrate
```

Inspect migration state:

```powershell
python manage.py showmigrations
```

---

## Running Tests

```powershell
python manage.py test
```

---

## Scheduled Jobs

### SLA monitoring

Flags requests as overdue and triggers notifications:

```powershell
python manage.py check_sla
```

In a container:

```powershell
docker compose exec web python manage.py check_sla
```

Schedule this daily via Task Scheduler, cron, or your preferred scheduler.

### Microsoft Graph user sync

Fetch Phildata tenant users:

```powershell
python manage.py fetch_phildata_users --limit 25 --sample 10
```

Include non-domain accounts:

```powershell
python manage.py fetch_phildata_users --include-non-domain
```

---

## Deployment

For Azure App Service container deployment guidance, see:

- [docs/azure-app-service-deployment.md](docs/azure-app-service-deployment.md)

---

## Security Notes

- Keep `.env` out of source control (add to `.gitignore`)
- Rotate any exposed secrets immediately
- Use strong passwords and least-privilege database accounts
- Use Azure Key Vault or equivalent secret store in production
- Set `DEBUG=False` and configure `ALLOWED_HOSTS` in production
- PostgreSQL firewall rules must explicitly allow your host IP

---

## Troubleshooting

### App does not start locally

- Confirm Python 3.12 and pip are installed and on PATH
- Recreate `.venv` and reinstall: `pip install -r requirements.txt`
- Verify `.env` values and database connectivity

### Worker timeouts / container crash

- Usually caused by the Azure PostgreSQL server being paused (auto-pause feature)
- Go to Azure Portal → PostgreSQL Flexible Server → click **Start**
- Verify your IP is in Networking → Firewall rules

### Migration errors

- Ensure the database service is running and reachable
- Confirm credentials and host/port in `.env`
- Run `python manage.py showmigrations` to inspect state

### Static files / UI issues

- Clear browser cache (`Ctrl+F5`)
- Rebuild the Docker image after CSS/template changes
- Confirm `whitenoise` is in `MIDDLEWARE` and `STATICFILES_STORAGE` is set


- [Overview](#overview)
- [Core Features](#core-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Local Development Setup](#local-development-setup)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [Database and Migrations](#database-and-migrations)
- [Running Tests](#running-tests)
- [Scheduled Jobs](#scheduled-jobs)
- [Deployment](#deployment)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)

## Overview

Request Hub provides:

- Role-aware dashboards for Requestor, Engineer, and Admin users
- Request lifecycle management from creation to completion
- SLA-aware monitoring and overdue visibility
- Engineer activity logging and reporting
- Built-in notification workflows and communication actions
- Dark mode and responsive UI behavior for desktop/mobile users

## Core Features

### Request Management

- Create and track requests with status, priority, engagement type, and due dates
- Assign engineers and backup engineers
- Manage request updates through role-appropriate actions

### Dashboard Insights

- Requestor dashboards with request metrics and report graphs
- Engineer dashboards with assigned/backup views and activity reporting
- Admin dashboard with sorting, filtering, and SLA indicators

### Activity Logs

- Engineer activity logging (hours, location, billable status, work details)
- Activity Report Graph tab for trend and distribution views

### Collaboration and Notifications

- In-app notification center for assignment and workflow updates
- Teams/Outlook integrations via action buttons where configured

## Technology Stack

- Backend: Django 4.2
- Database: PostgreSQL (recommended for production)
- Frontend: Django Templates + Bootstrap 5 + custom CSS/JS
- Containerization: Docker / Docker Compose
- Optional integrations: Azure Communication Services, Microsoft cloud services

## Project Structure

```text
accounts/            User/account management
hub/                 Core app: requests, activity logs, dashboards, reports
request_hub/         Django project settings and URL configuration
templates/           Shared and app templates
static/              CSS, images, and frontend assets
docs/                Deployment and operational documentation
```

## Local Development Setup

### 1) Create and activate virtual environment (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Configure environment

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local values (database host/user/password, secrets, and optional service keys).

### 3) Run migrations

```powershell
python manage.py migrate
```

### 4) Start development server

```powershell
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

## Docker Setup

### Start services

```powershell
docker compose up --build
```

### Run migrations in container

```powershell
docker compose exec web python manage.py migrate
```

### Stop services

```powershell
docker compose down
```

## Environment Variables

Use `.env` to store runtime configuration. Typical values include:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `ACS_EMAIL_CONNECTION_STRING` (use the ACS endpoint `https://esgrequesthub.asiapacific.communication.azure.com` in the connection string)
- `ACS_EMAIL_SENDER` (set to `DoNotReply@dreadops.site`)
- Optional integration settings (email/Azure/etc.)

Microsoft Graph (MSAL) settings for phildata tenant:

- `PHILDATA_TENANT_ID`
- `PHILDATA_CLIENT_ID`
- `PHILDATA_CLIENT_SECRET`
- `PHILDATA_DOMAIN` (default: `phildata.com`)
- `PHILDATA_GRAPH_SCOPE` (default: `https://graph.microsoft.com/.default`)

Do not commit real secrets, tokens, passwords, or connection strings.

## Database and Migrations

Apply migrations:

```powershell
python manage.py migrate
```

Create new migrations after model changes:

```powershell
python manage.py makemigrations
python manage.py migrate
```

## Running Tests

```powershell
python manage.py test
```

## Scheduled Jobs

SLA monitoring command:

```powershell
python manage.py check_sla
```

In containerized environments:

```powershell
docker compose exec web python manage.py check_sla
```

Run this on a daily schedule using Task Scheduler, cron, or your preferred scheduler.

Microsoft Graph tenant authentication and user fetch command:

```powershell
python manage.py fetch_phildata_users --limit 25 --sample 10
```

To include all users returned by Graph (not only `@phildata.com`):

```powershell
python manage.py fetch_phildata_users --include-non-domain
```

## Deployment

For Azure App Service container deployment guidance, see:

- [docs/azure-app-service-deployment.md](docs/azure-app-service-deployment.md)

## Security Notes

- Keep `.env` out of source control
- Rotate any exposed keys immediately
- Use strong passwords and enforce least privilege
- Prefer secret stores for production credentials (not plaintext files)

## Troubleshooting

### App does not start locally

- Verify Python and pip are installed and on PATH
- Recreate `.venv` and reinstall dependencies
- Confirm `.env` values and database connectivity

### Migration errors

- Ensure database service is running
- Confirm credentials/host/port in `.env`
- Run `python manage.py showmigrations` to inspect migration state

### Static files/UI issues

- Clear browser cache (Ctrl+F5)
- Rebuild containers if running via Docker

---

If you want, I can also add a **Contributing Guide**, **API/URL map**, and a **changelog section** to this README.
