from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('educators/', views.educator_listing, name='educator_listing'),
    path('educators/<str:unique_link>/', views.educator_public_profile, name='educator_profile'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
]
