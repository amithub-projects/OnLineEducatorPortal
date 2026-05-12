from django.urls import path
from . import views

urlpatterns = [
    # Educator panel
    path('dashboard/', views.educator_dashboard, name='educator_dashboard'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail_educator, name='course_detail_educator'),
    path('courses/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('courses/<int:course_pk>/module/add/', views.module_create, name='module_create'),
    path('modules/<int:module_pk>/lesson/add/', views.lesson_create, name='lesson_create'),
    path('students/', views.student_management, name='student_management'),

    # Student-facing
    path('course/<slug:slug>/', views.course_public_detail, name='course_public_detail'),
    path('course/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    path('learn/<int:enrollment_pk>/', views.course_learn, name='course_learn'),
    path('lesson-preview/<int:lesson_pk>/', views.lesson_preview, name='lesson_preview'),
]
