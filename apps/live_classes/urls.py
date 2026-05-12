from django.urls import path
from . import views

urlpatterns = [
    path('', views.live_sessions_list, name='live_sessions_list'),
    path('create/', views.create_live_session, name='create_live_session'),
    path('<int:session_pk>/start/', views.start_live_session, name='start_live_session'),
    path('<int:session_pk>/end/', views.end_live_session, name='end_live_session'),
    path('room/<str:room_code>/', views.live_session_room, name='live_session_room'),
    path('join/', views.join_live_session, name='join_live_session'),
]
