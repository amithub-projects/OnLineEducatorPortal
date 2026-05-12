from django.urls import path
from . import views

urlpatterns = [
    path('rooms/', views.chat_room_list, name='chat_room_list'),
    path('rooms/<int:room_id>/', views.chat_room, name='chat_room'),
    path('rooms/create/<int:course_pk>/', views.create_chat_room, name='create_chat_room'),
    path('private/<int:user_id>/', views.private_messages, name='private_messages'),
]
