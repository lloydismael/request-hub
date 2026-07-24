<div align="center">

<p align="center">
  <img src="https://raw.githubusercontent.com/lloydismael/request-hub/dev/static/img/phil-data-full-logo.png" width="1000" alt="Phil-Data Logo">
</p>


# Request Hub

**A role-based request and activity management platform built on Django.**  
Coordinate engineering work, enforce SLA timelines, and gain operational visibility — all from a single web portal.

[![Docker](https://img.shields.io/badge/Docker-lloydismael12%2Frequest--hub-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/r/lloydismael12/request-hub)
[![Latest Tag](https://img.shields.io/badge/Latest-v43.7-0ea5e9)](https://hub.docker.com/r/lloydismael12/request-hub/tags)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Azure-336791?logo=postgresql&logoColor=white)](https://azure.microsoft.com/en-us/products/postgresql/)

</div>

---

## Latest Release Snapshot

- **Current image tag:** `lloydismael12/request-hub:v48.1`
- **App version shown in profile:** `v48.1`
- **Latest update included:**
      - Added PM-ESG default SQR view for assigned records while preserving Total/filter access to all SQR.

---

## Table of Contents

- [UI Preview](#ui-preview)
- [Features](#features)
- [Workflow](#workflow)
- [Role Permissions](#role-permissions)
- [Data Model](#data-model)
- [Application Flow](#application-flow)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [Database & Migrations](#database--migrations)
- [Scheduled Jobs](#scheduled-jobs)
- [Deployment](#deployment)
- [Security](#security)

---

## UI Preview

> Role-aware dashboards, glass-morphism UI, dark mode, and responsive layouts across all pages.

| Page | Description |
|------|-------------|
| 🔐 **Login** | Clean auth page with branded background and forced password-change flow |
| 📋 **Dashboard** | Filterable request table with SLA indicators, stat pills, and status badges |
| 📝 **Request Detail** | Full lifecycle view — status log, communication actions, SQR submission |
| ⚙️ **Manage Request** | Admin/PM form for assigning engineers, changing status, and writing updates |
| 📊 **Reports — Operational** | Charts for requestor volume, engineer load, engagement types, product categories |
| 📊 **Reports — Activity** | Billable vs non-billable hours, location mix, engineer hour breakdown |
| 👤 **Profile** | User profile page with avatar, banner gradient, and contact details |
| 🔔 **Notifications** | In-app notification center for assignments and workflow events |

---

## Features

### 📋 Request Management
- Create requests with reference codes, priority (Medium / High), engagement type, and product category
- Assign primary and backup engineers with capacity enforcement (max 5 ongoing; max 3 when a deployment is active)
- SLA due-date auto-calculation (Medium = 5 days, High = 3 days)
- Overdue detection and visual indicators on the dashboard
- Status log history and admin-authored request updates

### 📊 Dashboard & Reporting
- **Admin/PM dashboard**: filterable, sortable request table with stat pills (All / Ongoing / Completed / Overdue)
- **Engineer dashboard**: Assigned vs Backup tabs, personal activity report graph
- **Requestor dashboard**: personal metrics, request creation, and progress tracking
- **Reports page (Operational)**: stacked bar charts — requests by requestor, by engineer, by engagement type, by product category
- **Reports page (Activity)**: billable vs non-billable hours, work location mix (donut), activity type breakdown, paginated engineer log
- Chart **expand button** on every chart card for full-screen view

### 🔔 Notifications & Communication
- In-app notification center for assignment events and workflow changes
- Communication action log (Teams, Outlook, Phone) with channel tagging
- Optional Teams chat topic field per request

### 📝 SQR (Service Quotation Request)
- Engineers and reviewers manage SQR entries directly from the tracker
- Tracks quotation details, SSE/PM man-hours, managed support amount, discounting, approval metadata, and revenue fields
- Status labels in the tracker:
      - `submitted` → **For Processing**
      - `for_revision` → **For Revision**
      - `reviewed` → **Approved**
- Approved flow supports two user options:
      - open a ready-to-edit email draft through the local mail app
      - download a formatted `.eml` file with the branded quotation layout
- Managed support date behavior:
      - `AI` = Post-service warranty end date
      - `AJ` = Support start date (manual value or computed fallback)
      - `AK` = Support end date (`AJ + 365 days`)
      - `AJ` and `AK` show `NA` when column `P` has no managed support value

### 👥 User & Profile Management
- Profile photos stored in the database (no external media bucket required)
- Configurable banner gradient (Blue, Sunset, Forest, Crimson, Slate, Aurora, Rose, Teal)
- Forced password-change on first login or admin reset
- Microsoft Graph user sync via `fetch_phildata_users` management command

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                       REQUEST LIFECYCLE                              │
│                                                                      │
│  Requestor / PM          Admin / PM-ESG           Engineer           │
│  ─────────────           ─────────────           ─────────           │
│  Create Request  ──────► Review & Assign  ──────► Work on Request    │
│  (with priority,         (engineer + due           (view in         │
│   engagement type,        date + status             assigned tab)    │
│   product category)       updates)                                   │
│                                                                      │
│                          Monitor SLA     ──────► Log Activity        │
│                          (overdue flags,           (hours, type,     │
│                           daily check_sla)          location,        │
│                                                     billable Y/N)    │
│                                                                      │
│                          Mark Completed  ◄──────  Submit SQR         │
│                          (end_date set)            (post-engagement  │
│                                                     quality report)  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Role Permissions

| Permission | Requestor | Requestor-ESS | PM-ESS | PM-ESG | Engineer | On Hold | Admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Create request | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| View own requests | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| View all requests | ❌ | ❌ | ✅ (all + mine tabs) | ✅ | ❌ | ❌ | ✅ |
| Assign engineers | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Update request status | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| View assigned requests | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ (read-only) | ✅ |
| Log engineer activity | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Submit SQR | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Access reports | ❌ | ❌ | ❌ | ✅ | ✅ (own graph) | ❌ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Export CSV | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |

> **PM-ESS** = Project Manager (ESS division) — sees both "All Requests" and "My Requests" tabs.  
> **PM-ESG** = Project Manager (ESG division) — full admin-level request management.  
> **On Hold** = Engineer account suspended from new assignments; retains read-only access to current tickets.

---

## Data Model

```
┌──────────────┐        ┌─────────────────────────────────────────────────┐
│    User       │        │                   Request                        │
│──────────────│        │─────────────────────────────────────────────────│
│ username      │◄──────►│ reference_code  (auto, unique)                  │
│ email         │  1:N   │ requestor       → User (requestor roles)         │
│ role          │        │ account         → Account                        │
│ phone_number  │        │ engineer        → User (engineer roles)          │
│ profile_photo │        │ backup_engineer → User (engineer roles)          │
│ banner_grad.. │        │ priority        Medium | High                    │
│ must_change.. │        │ engagement_type Opportunity | Training | Support  │
└──────────────┘        │                 Inquiry | Deployment | PM         │
                        │ product_category Azure | M365 | VMware | …        │
┌──────────────┐        │ status          Ongoing | Completed               │
│   Account    │        │ due_date        SLA auto-calculated                │
│──────────────│        │ description                                        │
│ name         │◄───────┤ teams_chat_topic                                   │
└──────────────┘        └─────────────────────────────────────────────────┘
                                  │ 1                        │ 1
                    ┌─────────────┘              ┌───────────┘
                    ▼ N                           ▼ N
        ┌──────────────────────┐     ┌────────────────────────────┐
        │    StatusLog          │     │   RequestCommunication      │
        │──────────────────────│     │────────────────────────────│
        │ status (ongoing/done)│     │ channel  Teams|Email|Phone  │
        │ note                 │     │ direction Inbound|Outbound  │
        │ author → User        │     │ summary                     │
        │ created_at           │     │ logged_by → User            │
        └──────────────────────┘     └────────────────────────────┘

        ┌──────────────────────────────────────────────────────────┐
        │                  EngineerActivityLog                      │
        │──────────────────────────────────────────────────────────│
        │ engineer      → User                                      │
        │ account       → Account                                   │
        │ request_date                                              │
        │ activity_type  Customer-Facing | Internal | Learning | …  │
        │ location       On-site | Remote | Mixed                   │
        │ actual_hours                                              │
        │ is_billable   Boolean                                     │
        │ details                                                   │
        └──────────────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────────────────┐
        │                    SQRSubmission                          │
        │──────────────────────────────────────────────────────────│
        │ request       → Request (1:1)                             │
        │ submitted_by  → User                                      │
        │ status        Draft | Submitted | Reviewed                │
        │ resolution_notes                                          │
        │ sse_manhours                                              │
        │ revenue_tracker fields                                    │
        └──────────────────────────────────────────────────────────┘
```

---

## Application Flow

```
Browser Request
      │
      ▼
 Django URL Router (request_hub/urls.py)
      │
      ├─► /accounts/*   ── AccountsApp  (login, profile, notifications)
      │                        │
      │                        └─ Middleware: MustChangePasswordMiddleware
      │                                       ProfileCompleteMiddleware
      │
      ├─► /dashboard/   ── DashboardView (role-dispatched)
      │                        │
      │                        ├─ Admin/PM-ESG  → full request table + filters
      │                        ├─ Engineer      → assigned/backup tabs + graph
      │                        └─ Requestor/PM  → personal metrics + request list
      │
      ├─► /requests/*   ── RequestDetailView, RequestAdminUpdateView
      │                        │
      │                        ├─ StatusLog writes on every save
      │                        ├─ SLA check on due_date
      │                        └─ Notification signals (hub/signals.py)
      │
      ├─► /reports/     ── ReportView (operational / activity tabs)
      │                        │
      │                        ├─ Chart.js 4.4 — stacked bar + doughnut
      │                        ├─ EngineerActivityLog CRUD
      │                        ├─ SQR form integration
      │                        └─ CSV export endpoint
      │
      └─► /admin/       ── Django admin (superusers only)

Signals & Background Jobs
      │
      ├─ post_save Request  → create Notification for assigned engineer
      ├─ check_sla (cron)   → mark overdue, send email via ACS
      └─ fetch_phildata_users (management cmd) → sync users from MS Graph
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12 · Django 4.2 |
| **Database** | PostgreSQL (Azure Flexible Server in production) |
| **Frontend** | Django Templates · Bootstrap 5.3 · Bootstrap Icons · Chart.js 4.4 |
| **Auth** | Django `AbstractUser` · custom role system · MSAL (Microsoft Graph) |
| **Email** | Azure Communication Services (ACS) — `DoNotReply@dreadops.site` |
| **Containerisation** | Docker · Docker Compose · Gunicorn (WSGI) |
| **Media Storage** | Database-backed `StoredFile` model (no S3/blob required) |
| **Deployment** | Azure App Service (container) — see [docs/azure-app-service-deployment.md](docs/azure-app-service-deployment.md) |
| **CI / Image** | `lloydismael12/request-hub` on Docker Hub |

---

## Project Structure

```
request-hub/
│
├── accounts/                   # User management app
│   ├── models.py               #   User (AbstractUser + roles + profile photo)
│   ├── views.py                #   Login, profile, notifications
│   ├── backends.py             #   Email-or-username auth backend
│   ├── middleware.py           #   Password-change & profile-complete guards
│   ├── storage.py              #   DatabaseMediaStorage for profile photos
│   └── migrations/
│
├── hub/                        # Core business logic app
│   ├── models.py               #   Request, Account, StatusLog, SQR, ActivityLog
│   ├── views.py                #   Dashboard, Detail, Reports, SQR, ActivityLog
│   ├── forms.py                #   RequestForm, AdminForm, ActivityLogForm
│   ├── mixins.py               #   Role-based access mixins
│   ├── signals.py              #   Notification triggers
│   ├── constants.py            #   Shared choices / constants
│   ├── urls.py
│   ├── services/
│   │   └── microsoft_graph.py  #   MS Graph API integration
│   └── management/commands/
│       ├── check_sla.py        #   Daily SLA overdue checker
│       └── fetch_phildata_users.py  # MS Graph user sync
│
├── request_hub/                # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── templates/
│   ├── base.html               # Shared layout (navbar, dark-mode, notifications)
│   ├── landing.html
│   ├── accounts/               # Login, profile, notification templates
│   └── hub/                    # Dashboard, detail, report, SQR templates
│
├── static/
│   ├── css/app.css             # All custom styles (glass-card, rpt-*, dbd-*, rmf-*)
│   ├── js/
│   └── img/
│
├── docs/
│   └── azure-app-service-deployment.md
│
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── manage.py
└── requirements.txt
```

---

## Local Development

### 1. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env with your database credentials and secret key
```

### 3. Apply migrations & run

```powershell
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`

---

## Docker Setup

### Pull and run from Docker Hub

```powershell
docker run --rm -p 8000:8000 --env-file .env lloydismael12/request-hub:latest
```

### Build locally

```powershell
$containers = docker ps --format "{{.ID}} {{.Ports}}" | Where-Object { $_ -match "0\.0\.0\.0:8000->8000/tcp|:::8000->8000/tcp" }
$containers | ForEach-Object { docker rm -f (($_ -split ' ')[0]) }
docker build -t lloydismael12/request-hub:v46.8 -t lloydismael12/request-hub:latest .
docker run --rm -p 8000:8000 --env-file .env -e APP_VERSION=v46.8 lloydismael12/request-hub:v46.8
```

### Push to Docker Hub

```powershell
docker push lloydismael12/request-hub:v43.7
docker push lloydismael12/request-hub:latest
```

### Compose (with local PostgreSQL)

```powershell
docker compose up --build
docker compose exec web python manage.py migrate
```

> If you are running the image on another machine, make sure the `.env` file exists on that machine and the `--env-file` path points to the correct local file.

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for dev, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated allowed host names |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `DB_HOST` | Database host (e.g. `requesthub-postgre.postgres.database.azure.com`) |
| `DB_PORT` | Database port (default `5432`) |
| `ACS_EMAIL_CONNECTION_STRING` | Azure Communication Services connection string |
| `ACS_EMAIL_SENDER` | Sender address — `DoNotReply@dreadops.site` |
| `PHILDATA_TENANT_ID` | Microsoft Entra tenant ID |
| `PHILDATA_CLIENT_ID` | App registration client ID |
| `PHILDATA_CLIENT_SECRET` | App registration client secret |
| `PHILDATA_DOMAIN` | Default `phildata.com` |
| `PHILDATA_GRAPH_SCOPE` | Default `https://graph.microsoft.com/.default` |

> ⚠️ Never commit real secrets, tokens, passwords, or connection strings to source control.

> ℹ️ The checked-in `.env.example` currently documents the Microsoft Graph variables used for Outlook draft creation. Create your own full `.env` file for local or Docker runs with database, Django, ACS, and Graph settings.

---

## Database & Migrations

```powershell
# Apply all pending migrations
python manage.py migrate

# After model changes
python manage.py makemigrations
python manage.py migrate

# Inspect current state
python manage.py showmigrations
```

---

## Scheduled Jobs

### SLA Monitoring (run daily)

```powershell
# Local
python manage.py check_sla

# Docker
docker compose exec web python manage.py check_sla
```

Schedule with Windows Task Scheduler, Linux `cron`, or Azure Container Apps scheduled jobs.

### Microsoft Graph User Sync

```powershell
# Fetch up to 25 users, sample 10
python manage.py fetch_phildata_users --limit 25 --sample 10

# Include all users (not only @phildata.com domain)
python manage.py fetch_phildata_users --include-non-domain
```

---

## Deployment

Full Azure App Service container deployment guide:

📄 [docs/azure-app-service-deployment.md](docs/azure-app-service-deployment.md)

**Key steps:**
1. Push image to Docker Hub (`lloydismael12/request-hub:v43.7` or your next release tag)
2. Set App Service container to the target tag
3. Configure all environment variables in App Service → Configuration
4. Ensure Azure PostgreSQL Flexible Server firewall allows the App Service outbound IPs
5. Run migrations via the App Service console or a startup script

---

## Security

- Store all secrets in `.env` or Azure Key Vault — never in source code
- Rotate any exposed credentials immediately
- `MustChangePasswordMiddleware` enforces password rotation on flagged accounts
- `ProfileCompleteMiddleware` blocks access until profile fields are filled
- All role checks are enforced server-side via `LoginRequiredMixin` + custom role mixins
- PostgreSQL connections use SSL in production (enforced by Azure Flexible Server)
- Static files served by WhiteNoise — no user-uploaded files exposed via the filesystem

---

<div align="center">

Built and maintained by **Phil-Data Business Systems Inc.**  
Docker Hub · [`lloydismael12/request-hub`](https://hub.docker.com/r/lloydismael12/request-hub)

</div>


