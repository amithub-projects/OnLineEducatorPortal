# Online Educator Teaching Portal — Implementation Plan

## Overview

A full-stack Python/Django education portal with three distinct panels (Public, Educator, Admin), real-time features via Django Channels (WebSockets), WebRTC-based live classes, role-based authentication, payment integration, and a modern responsive UI using Bootstrap 5 + custom CSS.

---

## User Review Required

> [!IMPORTANT]
> **Project Location**: All files will be created under `c:\Users\amitc\OneDrive\Documents\Online-Teaching\`

> [!IMPORTANT]
> **Database Choice**: Plan uses **SQLite** for development (zero-setup, works immediately). You can migrate to PostgreSQL/MySQL for production. Please confirm if you need PostgreSQL/MySQL set up from the start.

> [!WARNING]
> **Razorpay Integration**: Razorpay requires API keys from your Razorpay account. I will integrate the frontend and backend hooks, but you'll need to supply your own `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`. Same applies to email (SMTP credentials).

> [!IMPORTANT]
> **WebRTC Live Classes**: Full WebRTC (camera/mic) requires HTTPS in production. In local dev it works on `localhost`. I will implement the signaling server via Django Channels and a full WebRTC peer connection UI.

> [!WARNING]
> **Scope**: This is a very large project (~50+ files). I will build it in phases and provide a working, runnable application. Some advanced features (e.g., screen sharing, complex analytics charts) will be scaffolded and functional at a basic level.

---

## Open Questions

> [!IMPORTANT]
> 1. **Database**: SQLite (dev-ready, no setup) or PostgreSQL/MySQL from the start?
> 2. **Email**: Do you have SMTP credentials (Gmail, SendGrid, etc.) for email notifications?
> 3. **Razorpay**: Do you have Razorpay API keys ready?
> 4. **Domain/Deployment**: Is this for local development only, or do you need a deployment guide for a specific platform (Railway, Heroku, VPS)?

---

## Proposed Architecture

```
Online-Teaching/
├── manage.py
├── requirements.txt
├── .env.example
├── config/                        # Django project settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py                    # For Django Channels
│   └── wsgi.py
├── apps/
│   ├── authentication/            # Login, register, roles
│   ├── courses/                   # Course, lesson, module management
│   ├── live_classes/              # WebRTC + Django Channels
│   ├── chat/                      # Real-time chat (Channels)
│   ├── payments/                  # Razorpay integration
│   ├── content/                   # PDFs, notes, assignments
│   ├── scheduling/                # Class schedules, calendar
│   └── core/                      # Homepage, about, contact, public pages
├── templates/
│   ├── base.html
│   ├── public/                    # Landing pages
│   ├── educator/                  # Educator dashboard
│   ├── student/                   # Student dashboard
│   └── admin_panel/               # Custom admin UI
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── media/                         # Uploaded files
└── api/                           # DRF API endpoints
```

---

## Proposed Changes

### Phase 1 — Project Foundation

#### [NEW] `config/` — Django Project Core
- `settings/base.py` — Installed apps, DB, auth, channels, media, static
- `settings/development.py` — Debug=True, SQLite
- `config/urls.py` — Root URL dispatcher
- `config/asgi.py` — Django Channels ASGI config

#### [NEW] `apps/authentication/`
- `models.py` — Custom `User` model with `role` field (admin/educator/student)
- `views.py` — Register, login, logout, forgot password, profile
- `forms.py` — Student/Educator registration forms
- `urls.py` — Auth URL routes

#### [NEW] `apps/core/`
- `models.py` — SiteSettings, Announcement, ContactMessage
- `views.py` — Home, About, Contact, Educator Listing, Educator Public Profile
- `urls.py`

---

### Phase 2 — Educator Panel

#### [NEW] `apps/courses/`
- `models.py` — Course, Lesson, Module, Enrollment
- `views.py` — CRUD for courses/lessons, material upload
- Educator dashboard: course list, create, edit, delete

#### [NEW] `apps/content/`
- `models.py` — CourseFile (PDF, notes, images, assignments)
- `views.py` — Upload, list, delete files
- Secure file serving with permission checks

#### [NEW] `apps/scheduling/`
- `models.py` — ClassSchedule, Attendance
- `views.py` — Calendar view, create/edit schedules, attendance marking

---

### Phase 3 — Real-Time Features

#### [NEW] `apps/live_classes/`
- `consumers.py` — WebSocket consumer for WebRTC signaling (offer/answer/ICE)
- `models.py` — LiveSession, SessionParticipant
- `views.py` — Start/end live class, join room
- `routing.py` — WebSocket URL patterns
- Frontend: WebRTC peer connections, camera/mic controls

#### [NEW] `apps/chat/`
- `consumers.py` — WebSocket consumer for real-time chat
- `models.py` — Message, ChatRoom, PrivateMessage
- `views.py` — Chat room views
- Frontend: Live chat UI with group + private messaging

---

### Phase 4 — Payments & Admin

#### [NEW] `apps/payments/`
- `models.py` — Payment, Transaction
- `views.py` — Razorpay order creation, payment verification webhook
- Payment history for students and educators

#### [NEW] Custom Admin Panel (`templates/admin_panel/`)
- Full CRUD: educators, students, courses, content
- Approve/suspend educators
- View payment details
- Site settings management
- Analytics dashboard (totals, charts)
- Monitor live sessions

---

### Phase 5 — APIs & Polish

#### [NEW] `api/`
- DRF ViewSets for courses, users, enrollments
- Token authentication for API access
- Serializers for all major models

#### [NEW] Frontend Polish
- Bootstrap 5 + custom CSS design system
- Responsive layouts (mobile, tablet, desktop)
- Smooth animations, modern color palette
- SEO meta tags on all pages

---

## Database Schema (Key Models)

| Model | Key Fields |
|-------|-----------|
| `User` | id, email, full_name, role (admin/educator/student), phone, avatar, is_approved |
| `EducatorProfile` | user, bio, subjects, experience_years, hourly_rate, rating |
| `Course` | educator, title, description, category, thumbnail, price, is_published |
| `Lesson` | course, title, order, video_file, duration |
| `Enrollment` | student, course, enrolled_at, payment_status |
| `LiveSession` | educator, course, title, room_code, scheduled_at, is_active |
| `Message` | room, sender, content, timestamp, message_type |
| `Payment` | student, course, amount, razorpay_order_id, status, created_at |
| `ClassSchedule` | educator, course, title, start_time, end_time, meeting_link |
| `Attendance` | student, schedule, is_present |
| `CourseFile` | course, file, file_type (pdf/image/doc), uploaded_by |
| `SiteSettings` | site_name, logo, hero_text, about_content |
| `Announcement` | title, content, is_active, created_by |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Student/Educator registration |
| POST | `/api/auth/login/` | JWT/session login |
| GET | `/api/courses/` | List all published courses |
| POST | `/api/courses/create/` | Educator creates course |
| POST | `/api/enrollments/` | Student enrolls in course |
| GET | `/api/educators/` | List all educators |
| POST | `/api/payments/create-order/` | Razorpay order |
| POST | `/api/payments/verify/` | Payment verification |
| WS | `ws/chat/<room_id>/` | Chat WebSocket |
| WS | `ws/live/<session_id>/` | WebRTC signaling WebSocket |

---

## User Workflow

```
Student:
  Register → Login → Browse Educators → View Profile →
  Enroll (Pay) → Access Course Materials → Join Live Class → Chat

Educator:
  Register → Admin Approves → Login → Setup Profile →
  Create Courses → Upload Content → Schedule Classes →
  Start Live Session → Manage Students → View Payments

Admin:
  Login → Dashboard → Manage Educators (Approve/Suspend) →
  Manage Students → View Payments → Edit Site Content →
  Monitor Live Sessions → Generate Reports
```

---

## Verification Plan

### Automated
- Django's built-in test runner: `python manage.py test`
- Test user creation for all 3 roles
- Test course enrollment flow
- Test WebSocket connection

### Manual Verification
- Run dev server: `python manage.py runserver`
- Test all three panels in browser
- Test responsive design on mobile viewport
- Test Razorpay payment flow (test mode)
- Test WebRTC live class (two browser tabs)

---

## Installation Steps (to be generated)

1. `git clone` / extract project
2. `pip install -r requirements.txt`
3. Copy `.env.example` → `.env`, fill credentials
4. `python manage.py migrate`
5. `python manage.py createsuperuser`
6. `python manage.py runserver`

## Deployment Guide

- **Development**: `python manage.py runserver` + Redis (for Channels)
- **Production**: Gunicorn + Daphne (ASGI) + Nginx + PostgreSQL + Redis
- **Platform options**: Railway, Render, DigitalOcean, or VPS

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend Framework | Django 4.2 |
| Real-time | Django Channels 4.x + Redis |
| WebRTC | Native browser API + custom signaling server |
| API | Django REST Framework |
| Auth | Django built-in + custom User model |
| Frontend | Django Templates + Bootstrap 5 + Custom CSS |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Payments | Razorpay |
| Media Storage | Local (`/media/`) → S3 for production |
| Email | Django email backend (SMTP) |
