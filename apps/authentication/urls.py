from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_student, name='register_student'),
    path('register/educator/', views.register_educator, name='register_educator'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('toggle-follow/<int:educator_pk>/', views.toggle_follow, name='toggle_follow'),
]
