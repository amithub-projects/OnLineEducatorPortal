from django.urls import path
from . import admin_views, views

urlpatterns = [
    # Admin Panel
    path('admin-panel/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/educators/', admin_views.manage_educators, name='manage_educators'),
    path('admin-panel/educators/create/', admin_views.create_educator_admin, name='create_educator_admin'),
    path('admin-panel/educators/<int:pk>/approve/', admin_views.approve_educator, name='approve_educator'),
    path('admin-panel/educators/<int:pk>/suspend/', admin_views.suspend_educator, name='suspend_educator'),
    path('admin-panel/users/<int:pk>/delete/', admin_views.delete_user, name='delete_user'),
    path('admin-panel/students/', admin_views.manage_students, name='manage_students'),
    path('admin-panel/students/<int:pk>/', admin_views.student_detail_admin, name='student_detail_admin'),
    path('admin-panel/courses/', admin_views.manage_courses, name='manage_courses'),
    path('admin-panel/courses/<int:pk>/', admin_views.admin_course_detail, name='admin_course_detail'),
    path('admin-panel/courses/<int:pk>/toggle-featured/', admin_views.toggle_featured_course, name='toggle_featured_course'),
    path('admin-panel/lessons/<int:pk>/delete/', admin_views.admin_delete_lesson, name='admin_delete_lesson'),
    path('admin-panel/payments/', admin_views.manage_payments, name='manage_payments'),
    path('admin-panel/settings/', admin_views.site_settings_admin, name='site_settings_admin'),
    path('admin-panel/announcements/', admin_views.announcements_admin, name='announcements_admin'),
    path('admin-panel/announcements/<int:pk>/toggle/', admin_views.toggle_announcement, name='toggle_announcement'),
    path('admin-panel/live/', admin_views.monitor_live_sessions, name='monitor_live_sessions'),
    path('admin-panel/messages/', admin_views.contact_messages, name='contact_messages'),
    path('admin-panel/categories/', admin_views.manage_categories, name='manage_categories'),

    # REST API
    path('courses/', views.CourseListAPIView.as_view(), name='api_courses'),
    path('educators/', views.EducatorListAPIView.as_view(), name='api_educators'),
    path('enrollments/', views.EnrollmentAPIView.as_view(), name='api_enrollments'),
]
