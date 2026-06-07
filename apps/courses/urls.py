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
    path('modules/<int:module_pk>/assign-sub-educators/', views.assign_subject_sub_educators, name='assign_subject_sub_educators'),
    path('modules/<int:module_pk>/lesson/add/', views.lesson_create, name='lesson_create'),
    path('students/', views.student_management, name='student_management'),
    path('students/<int:pk>/', views.student_detail_educator, name='student_detail_educator'),
    path('sub-educators/', views.manage_sub_educators, name='manage_sub_educators'),
    path('sub-educators/add/', views.add_sub_educator, name='add_sub_educator'),
    path('sub-educators/<int:sub_id>/assign/', views.assign_courses_to_sub_educator, name='assign_courses_to_sub_educator'),
    path('sub-educators/<int:sub_id>/toggle-status/', views.toggle_sub_educator_status, name='toggle_sub_educator_status'),
    path('sub-educators/<int:sub_id>/delete/', views.delete_sub_educator, name='delete_sub_educator'),
    path('promo-codes/', views.manage_promo_codes, name='manage_promo_codes'),

    # Student-facing
    path('course/<slug:slug>/', views.course_public_detail, name='course_public_detail'),
    path('course/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    path('learn/<int:enrollment_pk>/', views.course_learn, name='course_learn'),
    path('lesson-preview/<int:lesson_pk>/', views.lesson_preview, name='lesson_preview'),
]
