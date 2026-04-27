# Request Hub

> **Role-based request and activity management platform built with Django.**  
> Helps requestors, engineers, and administrators coordinate work, track SLA timelines, and monitor operational progress from a single web portal.

---

## Table of Contents

- [UI Previews](#ui-previews)
- [Workflow](#workflow)
- [Features](#features)
- [Role Permissions](#role-permissions)
- [Data Model](#data-model)
- [Application Flow](#application-flow)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Development Setup](#local-development-setup)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [Database and Migrations](#database-and-migrations)
- [Scheduled Jobs](#scheduled-jobs)
- [Deployment](#deployment)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)

---

## UI Previews

| Page | Description |
|---|---|
| **Login** | Dark-themed login with background illustration and SSO-ready form |
| **Dashboard** | Role-specific table with SLA indicators, stat pills (All / Ongoing / Completed / Overdue), filter panel, and Export CSV |
| **Request Detail** | Full request card with status log timeline, communication actions (Teams / Outlook), and SQR link |
| **Manage Request** | Admin/PM form with engineer assignment, engagement type, priority, and product category fields |
| **Activity Logs** | Engineer time-tracking table with billable hours, location, and activity type |
| **Reports â€“ Operational** | Stacked bar charts for Requestors and Engineers; donut charts for Engagement Types and Product Categories; KPI summary row |
| **Reports â€“ Activity** | Hours-by-engineer and hours-by-activity-type bar charts; Work Location Mix and Billable Distribution donut charts; paginated activity log table |
| **Notifications** | Bell-icon inbox with categorised notifications (New Request / Assignment / Status Update / Completion / Reminder) |
| **SQR** | Service Quotation Request list with submission workflow, revenue tracker, and PM-ESG review |
| **User Management** | Admin-only user role and profile management table |

---

## Workflow

```
Requestor creates request
        â”‚
        â–¼
Admin / PM-ESG reviews and assigns Engineer + Backup Engineer
        â”‚
        â–¼
Engineer works on request, posts Status Log updates
        â”‚
        â”œâ”€â”€â–¶ Engineer logs activity hours (EngineerActivityLog)
        â”‚
        â”œâ”€â”€â–¶ Teams / Outlook communication actions triggered
        â”‚
        â”œâ”€â”€â–¶ SLA deadline monitored daily (check_sla command)
        â”‚        â”‚
        â”‚        â””â”€â”€â–¶ Overdue flag set â†’ Nudge notification sent
        â”‚
        â–¼
Request marked Completed by Engineer or Admin
        â”‚
        â–¼
Admin / PM-ESG can submit SQR (Service Quotation Request)
        â”‚
        â–¼
PM-ESG Reviewer approves / requests revision â†’ Revenue Tracker updated
```

---

## Features

### Request Management
- Auto-generated reference codes (e.g. `RH-2025-0001`)
- Priority levels: **Medium** (5-day SLA) and **High** (3-day SLA)
- Engagement types: Opportunity Â· Training Â· Support Â· Inquiry Â· Deployment Â· Project Management
- Product categories: Azure Â· M365 Â· VMware Â· Omnissa Â· Hybrid Â· Dell Â· HP Â· Network Â· Others
- Engineer capacity enforcement (max 5 ongoing; max 3 when deployment is active)
- Backup engineer assignment
- Status lifecycle: **Ongoing â†’ Completed**

### Dashboard
- Role-specific views (Requestor / Engineer / Admin / PM-ESS / PM-ESG)
- Advanced filter panel (status, priority, engineer, engagement, date range)
- SLA countdown and overdue indicators per row
- Stat pills: All Â· Ongoing Â· Completed Â· Overdue
- Sortable table with pagination and CSV export

### Activity Logging
- Engineer time tracking per account and request
- Activity types: Learning Â· Internal Support Â· On-Call Support Â· Pre-Sales Â· Project Management Â· Training Â· Deployment
- Work locations: WFA Â· Office Â· Onsite
- Billable / non-billable flag

### Reports
- **Operational tab**: stacked bar charts (Requestors, Engineers), status breakdown chips, KPI cards
- **Activity tab**: hours-by-engineer and hours-by-type bar charts, location mix and billable distribution donut charts, paginated log table with inline edit
- **Chart expand modal**: full-screen chart expansion with animated overlay
- CSV export for both report views

### SQR (Service Quotation Request)
- Structured quotation submission by engineers
- Discount rate calculation and revenue stage tracking (Quotation â†’ Order â†’ Revenue)
- PM-ESG review workflow with approval / revision notes
- Teams chat and Outlook approval email actions

### Notifications
- In-app notification bell with unread count badge
- Auto-categorisation: New Request Â· Assignment Â· Status Update Â· Completion Â· Reminder Â· System
- Mark as read, follow to related request, bulk mark-all-read, delete

### Collaboration
- Teams deep-link chat creation per request
- Outlook compose redirect for engineer introductions and request closings
- Nudge action to send SLA reminders

### User Management (Admin only)
- Role assignment, profile completion tracking
- Microsoft Graph integration to sync users from the Phildata Azure AD tenant
- Profile photos stored in the database (no external media host required)
- Forced password change on first login

---

## Role Permissions

| Capability | Requestor | Requestor-ESS | PM-ESS | PM-ESG | Engineer | On Hold | Admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Create request | âœ“ | âœ“ | âœ“ | âœ“ | | | âœ“ |
| View own requests | âœ“ | âœ“ | âœ“ | âœ“ | | | âœ“ |
| View all requests | | | âœ“ | âœ“ | | | âœ“ |
| Post status log update | | | | | âœ“ | | âœ“ |
| Close (complete) request | | | | | âœ“ | | âœ“ |
| Assign engineers | | | | | | | âœ“ |
| Manage request fields | | | | | | | âœ“ |
| Log activity hours | | | | | âœ“ | | |
| View activity reports | | | | âœ“ | âœ“ | | âœ“ |
| Submit SQR | | | | | âœ“ | | |
| Review / approve SQR | | | | âœ“ | | | âœ“ |
| Update SQR revenue tracker | | | | âœ“ | | | âœ“ |
| Manage users | | | | | | | âœ“ |
| Nudge engineers | | | | | | | âœ“ |
| Export CSV | | | âœ“ | âœ“ | âœ“ | | âœ“ |

> **On Hold** engineers are visible in the system but cannot be assigned new requests. Their existing assignments remain active.

---

## Data Model

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ accounts.User (AbstractUser)                                    â”‚
â”‚  role: requestor | requestor_ess | pm_ess | pm_esg |            â”‚
â”‚         engineer | on_hold | admin                              â”‚
â”‚  profile_photo, phone_number, banner_gradient                   â”‚
â”‚  must_change_password, profile_completed                        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                â”‚ FK (requestor / engineer / backup_engineer)
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ hub.Request                                                     â”‚
â”‚  reference_code (auto)  priority: medium | high                 â”‚
â”‚  engagement_type        status: ongoing | completed             â”‚
â”‚  product_category       start_date, due_date, end_date          â”‚
â”‚  account (FK)           description, teams_chat_topic           â”‚
â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
   â”‚       â”‚      â”‚       â”‚
   â”‚       â”‚      â”‚       â””â”€â”€ hub.StatusLog
   â”‚       â”‚      â”‚             author (FK User), message, created_at
   â”‚       â”‚      â”‚
   â”‚       â”‚      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ hub.RequestCommunication
   â”‚       â”‚                    channel: outlook | teams
   â”‚       â”‚                    user (FK), created_at
   â”‚       â”‚
   â”‚       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ hub.Notification
   â”‚                            recipient (FK User), message
   â”‚                            is_read, category, related_request (FK)
   â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ hub.EngineerActivityLog
                                engineer (FK User), account (FK)
                                request (FK, nullable)
                                activity_type, actual_hours
                                location, is_billable, status
                                request_date

hub.SqrSubmission
  reference_code (SQR-YYYY-NNNN, auto)
  engineer (FK User), pm_esg_reviewer (FK User)
  customer_name, project_title, project_details
  sse_manhrs, quotation_total_price, discount_rate
  status: submitted | for_revision | reviewed
  po_attachment_link, revenue_overview

hub.Account
  name (unique)
```

---

## Application Flow

```
Browser
  â”‚
  â”œâ”€â”€ GET /               â†’ Landing page (login redirect if unauthenticated)
  â”œâ”€â”€ POST /accounts/login/ â†’ Authenticate â†’ redirect to /dashboard/
  â”‚
  â”œâ”€â”€ GET /dashboard/     â†’ DashboardView
  â”‚     â”œâ”€â”€ role=admin    â†’ All requests table + filter panel + stat pills
  â”‚     â”œâ”€â”€ role=engineer â†’ Assigned / Backup / Report Graph tabs
  â”‚     â””â”€â”€ role=requestorâ†’ My Requests + metrics summary
  â”‚
  â”œâ”€â”€ GET /requests/<pk>/ â†’ RequestDetailView (status log, actions)
  â”œâ”€â”€ POST /requests/<pk>/status/ â†’ RequestStatusUpdateView (engineer / admin)
  â”œâ”€â”€ GET|POST /requests/<pk>/manage/ â†’ RequestAdminUpdateView (admin/pm_esg)
  â”‚
  â”œâ”€â”€ GET /activity-logs/ â†’ EngineerActivityLogView (engineer / pm_esg / admin)
  â”‚
  â”œâ”€â”€ GET /reports/       â†’ RequestReportView
  â”‚     â”œâ”€â”€ ?report_view=operational â†’ KPIs + charts (requestors, engineers, engagement, product)
  â”‚     â””â”€â”€ ?report_view=activity   â†’ Activity charts + paginated log table
  â”‚
  â”œâ”€â”€ GET /sqr/           â†’ SqrListView (engineer: own submissions; pm_esg/admin: all)
  â”œâ”€â”€ POST /sqr/<pk>/review/ â†’ SqrReviewUpdateView (pm_esg)
  â”‚
  â”œâ”€â”€ GET /notifications/ â†’ NotificationListView
  â”‚
  â””â”€â”€ GET /management/   â†’ UserManagementView (admin only)

Django Signals (hub/signals.py)
  â””â”€â”€ post_save on Request â†’ auto-create Notifications for engineer and admin

Management Commands
  â”œâ”€â”€ check_sla        â†’ marks overdue, sends nudge notifications
  â””â”€â”€ fetch_phildata_users â†’ syncs users from Microsoft Graph (Azure AD)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12 Â· Django 4.2 |
| **Database** | PostgreSQL (Azure Database for PostgreSQL â€“ Flexible Server in production) |
| **Frontend** | Django Templates Â· Bootstrap 5.3 Â· Bootstrap Icons Â· Chart.js 4.4 |
| **CSS** | Custom `app.css` â€” glass-card design system, dark-mode, responsive layout |
| **Auth** | Django `AbstractUser` Â· Custom role field Â· `must_change_password` flag |
| **Email** | Azure Communication Services (ACS) â€” `DoNotReply@dreadops.site` sender |
| **Microsoft Integration** | Microsoft Graph API (MSAL) â€” user sync, Teams deep links, Outlook compose |
| **Containerisation** | Docker Â· Docker Compose Â· Gunicorn |
| **Static Files** | `django.contrib.staticfiles` â€” collected into `/app/staticfiles` at build time |
| **Media Storage** | Database-backed (`DatabaseMediaStorage`) â€” profile photos stored as binary blobs |
| **Scheduling** | External cron / Azure App Service scheduler â†’ `manage.py check_sla` |
| **Deployment** | Azure App Service (container) â€” see `docs/azure-app-service-deployment.md` |

---

## Project Structure

```
request-hub/
â”œâ”€â”€ accounts/                   # User model, auth, profile, role management
â”‚   â”œâ”€â”€ models.py               # User (AbstractUser + role), StoredFile
â”‚   â”œâ”€â”€ views.py                # Login, profile, password change
â”‚   â”œâ”€â”€ backends.py             # Custom auth backend
â”‚   â”œâ”€â”€ middleware.py           # Force password change / profile completion redirects
â”‚   â”œâ”€â”€ storage.py              # DatabaseMediaStorage for profile photos
â”‚   â””â”€â”€ migrations/
â”‚
â”œâ”€â”€ hub/                        # Core application
â”‚   â”œâ”€â”€ models.py               # Request, Account, StatusLog, EngineerActivityLog,
â”‚   â”‚                           #   SqrSubmission, Notification, RequestCommunication
â”‚   â”œâ”€â”€ views.py                # All CBVs: Dashboard, Detail, Reports, SQR, Notificationsâ€¦
â”‚   â”œâ”€â”€ forms.py                # Request, activity log, SQR, status log forms
â”‚   â”œâ”€â”€ mixins.py               # Role-check mixins (AdminRequired, EngineerRequired, â€¦)
â”‚   â”œâ”€â”€ signals.py              # post_save â†’ Notification creation
â”‚   â”œâ”€â”€ constants.py            # Engineer/Account Manager/Account name lists
â”‚   â”œâ”€â”€ context_processors.py  # Global notification count injected into all templates
â”‚   â”œâ”€â”€ urls.py                 # All hub URL patterns
â”‚   â”œâ”€â”€ admin.py                # Django admin registrations
â”‚   â””â”€â”€ management/
â”‚       â””â”€â”€ commands/
â”‚           â”œâ”€â”€ check_sla.py          # SLA monitoring and overdue notifications
â”‚           â””â”€â”€ fetch_phildata_users.py # Microsoft Graph user sync
â”‚
â”œâ”€â”€ request_hub/                # Django project config
â”‚   â”œâ”€â”€ settings.py
â”‚   â”œâ”€â”€ urls.py                 # Root URL conf (accounts + hub + admin)
â”‚   â”œâ”€â”€ asgi.py
â”‚   â””â”€â”€ wsgi.py
â”‚
â”œâ”€â”€ templates/                  # All HTML templates
â”‚   â”œâ”€â”€ base.html               # Global layout: navbar, dark-mode toggle, notifications bell
â”‚   â”œâ”€â”€ landing.html
â”‚   â”œâ”€â”€ accounts/               # Login, profile, password change templates
â”‚   â””â”€â”€ hub/                    # Dashboard, request detail/form, reports, SQR, notificationsâ€¦
â”‚
â”œâ”€â”€ static/
â”‚   â”œâ”€â”€ css/app.css             # Complete design system (glass cards, charts, dark mode)
â”‚   â”œâ”€â”€ js/                     # login-success.js and page-specific scripts
â”‚   â””â”€â”€ images/ img/            # Logos, favicons, background SVG
â”‚
â”œâ”€â”€ staticfiles/                # Collected static files (generated at build)
â”‚
â”œâ”€â”€ docs/
â”‚   â””â”€â”€ azure-app-service-deployment.md
â”‚
â”œâ”€â”€ Dockerfile
â”œâ”€â”€ docker-compose.yml
â”œâ”€â”€ entrypoint.sh               # collectstatic â†’ migrate â†’ gunicorn
â”œâ”€â”€ manage.py
â””â”€â”€ requirements.txt
```

---

## Local Development Setup

### 1. Create virtual environment (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local database credentials and secret key.

### 3. Apply migrations and start

```powershell
python manage.py migrate
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

---

## Docker Setup

### Build and run

```powershell
# Build image and tag
docker build -t lloydismael12/request-hub:vX.Y -t lloydismael12/request-hub:latest .

# Run locally
docker run --rm -p 8000:8000 --env-file .env lloydismael12/request-hub:latest

# Stop running container on port 8000 and rebuild
docker ps -q --filter "publish=8000" | ForEach-Object { docker stop $_ }
```

### Push to Docker Hub

```powershell
docker push lloydismael12/request-hub:vX.Y
docker push lloydismael12/request-hub:latest
```

### Docker Compose (local with DB)

```powershell
docker compose up --build
docker compose exec web python manage.py migrate
docker compose down
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host (e.g. `requesthub-postgre.postgres.database.azure.com`) |
| `DB_PORT` | Database port (default `5432`) |
| `ACS_EMAIL_CONNECTION_STRING` | Azure Communication Services connection string |
| `ACS_EMAIL_SENDER` | Sender address (e.g. `DoNotReply@dreadops.site`) |
| `PHILDATA_TENANT_ID` | Microsoft Entra tenant ID |
| `PHILDATA_CLIENT_ID` | App registration client ID |
| `PHILDATA_CLIENT_SECRET` | App registration client secret |
| `PHILDATA_DOMAIN` | Default: `phildata.com` |
| `PHILDATA_GRAPH_SCOPE` | Default: `https://graph.microsoft.com/.default` |

> Do not commit real secrets, tokens, passwords, or connection strings to source control.

---

## Database and Migrations

```powershell
# Apply all pending migrations
python manage.py migrate

# After model changes
python manage.py makemigrations
python manage.py migrate

# Inspect migration state
python manage.py showmigrations
```

---

## Scheduled Jobs

### SLA monitoring

```powershell
# Run daily (local)
python manage.py check_sla

# In Docker
docker compose exec web python manage.py check_sla
```

Schedule with Windows Task Scheduler, cron, or Azure App Service WebJobs.

### Microsoft Graph user sync

```powershell
# Sync up to 25 users, sample 10 for preview
python manage.py fetch_phildata_users --limit 25 --sample 10

# Include non-phildata.com accounts
python manage.py fetch_phildata_users --include-non-domain
```

---

## Deployment

For Azure App Service container deployment see:

- [docs/azure-app-service-deployment.md](docs/azure-app-service-deployment.md)

The `entrypoint.sh` runs `collectstatic`, `migrate`, then starts Gunicorn automatically on container start.

---

## Security Notes

- Keep `.env` out of source control (`.gitignore` it)
- Rotate any exposed keys immediately
- Use strong passwords and enforce least privilege
- Prefer Azure Key Vault or similar secret stores for production credentials
- `DEBUG=False` and `ALLOWED_HOSTS` must be set correctly in production
- Profile photos and media are stored in the database â€” no public media URL exposure

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| App does not start locally | Verify `.env` values; confirm DB is reachable; recreate `.venv` |
| `Connection refused` on DB | Azure PostgreSQL may be paused â€” start it from the Azure Portal; check firewall rules |
| Migration errors | Ensure DB is running; confirm credentials; run `showmigrations` |
| Worker timeout in Gunicorn | Usually a slow DB query or Azure DB cold start; wait for DB to warm up |
| Static files not loading | Run `python manage.py collectstatic`; clear browser cache (Ctrl+F5) |
| Chart expand modal blank | Ensure Chart.js CDN loads; check console for canvas reuse errors |
| Navbar missing on a page | Check that `context_object_name` does not shadow `request` in CBVs |

