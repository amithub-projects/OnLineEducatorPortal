# Online Education Portal Walkthrough

I have successfully completed the development of your **Online Educator Teaching Portal**. The project is a full-stack Django application that strictly uses Python on the backend and pure HTML/CSS/Bootstrap 5 on the frontend without any JavaScript frontend frameworks.

## What Has Been Implemented

### 1. Architecture & Core Setup
- **Django Project Structure**: Modular app design (`authentication`, `core`, `courses`, `live_classes`, `chat`, `payments`, `scheduling`, `content`, `api`).
- **Dependencies**: Integrated Django REST Framework, Django Channels (WebSockets), Redis, WhiteNoise, Daphne (ASGI), and Razorpay.
- **Database**: Initialized and migrated the SQLite database (can be swapped to PostgreSQL in production via `.env`).

### 2. User Roles & Authentication
- Custom `User` model utilizing `email` as the primary identifier instead of `username`.
- Role-based Access Control (RBAC) with three strict roles: `Admin`, `Educator`, and `Student`.
- Authentication forms and views for Login, Student Registration, Educator Registration (with pending approval workflow), and Password Reset.
- Profile management for both Students and Educators.

### 3. Educator & Course Management
- Complete Course creation workflow for educators (Drafts vs. Published).
- Course curriculum building: Modules, Lessons (Video/Text), and File attachments (PDFs, notes).
- Comprehensive dashboard for Educators to view statistics, manage students, track payments, and schedule classes.
- Public Educator Listing page with filtering capabilities (by name, subject, experience).

### 4. Real-time Features (Django Channels)
- **WebRTC Live Classes**: Built a custom signaling server using Django Channels and WebSockets.
  - The `LiveClassConsumer` handles SDP offers, answers, and ICE candidates for peer-to-peer WebRTC video/audio streaming.
  - The Live Room template includes video controls (Mic, Camera, Screen Share) and a real-time live chat overlay.
- **Messaging**: Real-time group chat rooms linked to specific courses, allowing educators and enrolled students to communicate seamlessly. Private messaging between students and educators is also supported.

### 5. Payments Integration
- Secure integration with Razorpay.
- Checkout workflow that generates Razorpay Orders on the backend, securely processes the client-side checkout, and verifies the signature callback on the server to prevent spoofing.
- Auto-enrollment upon successful payment verification.

### 6. Admin Panel
- A fully custom, beautifully designed Admin Dashboard replacing the default Django admin.
- Comprehensive statistics, revenue tracking, and quick actions.
- Educator approval workflow: Admins must approve educators before they can publish courses.
- Centralized management of Site Settings (dynamic logos, contact info, social links), Announcements, Categories, Users, Courses, and Payments.

### 7. UI / UX Design
- Built a highly polished, modern design system using **Bootstrap 5**, **Bootstrap Icons**, and custom CSS (`static/css/main.css`).
- Integrated Google Fonts (`Outfit` for headings, `Inter` for body).
- Responsive grid layouts, hover effects, subtle glassmorphism (`backdrop-filter`), and distinct color-coded dashboards.
- Dynamic toast notifications for standard Django messages.

### 8. API Layer
- Implemented a standard REST API using Django REST Framework for future mobile app integrations.
- Exposed endpoints for Course Listing, Educator Listing, and Enrollments.

## How to Run the Project Locally

The database has already been migrated, and an initial Admin account has been created.

**Default Admin Credentials:**
- **Email:** `admin@example.com`
- **Password:** `admin123`

To start the development server, run the following command in your terminal:

```bash
python manage.py runserver
```

*(Note: For WebSockets/Live Classes to work fully, you must run the server using an ASGI server like Daphne and ensure a Redis instance is running locally on port 6379, or configure the `CHANNEL_LAYERS` in `settings.py` to use `InMemoryChannelLayer` for local testing without Redis).*

```bash
daphne config.asgi:application
```

### Important Next Steps for Production
1. **Environment Variables**: Update your `.env` file with real SMTP credentials (for password resets and notifications), a secure `SECRET_KEY`, and your live Razorpay Keys (`RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`).
2. **Redis Setup**: Ensure Redis is installed and running for production WebSocket support.
3. **WebRTC STUN/TURN**: The current WebRTC implementation uses Google's public STUN servers. For a robust production environment (especially for users behind strict firewalls), you should deploy or subscribe to a TURN server (like Twilio Network Traversal or Coturn).

You can now explore the public pages, log into the admin dashboard, create some test educator and student accounts, and test the complete workflow!
