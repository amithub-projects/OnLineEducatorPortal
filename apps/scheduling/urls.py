from django.urls import path
from . import views

urlpatterns = [
    path('', views.schedule_list, name='schedule_list'),
    path('create/', views.schedule_create, name='schedule_create'),
    path('<int:pk>/edit/', views.schedule_edit, name='schedule_edit'),
    path('<int:schedule_pk>/attendance/', views.attendance_view, name='attendance_view'),
    path('<int:schedule_pk>/attendance/mark/', views.mark_attendance, name='mark_attendance'),
]
