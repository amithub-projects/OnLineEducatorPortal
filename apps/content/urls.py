from django.urls import path
from . import views

urlpatterns = [
    path('upload/<int:course_pk>/', views.upload_file, name='upload_file'),
    path('delete/<int:pk>/', views.delete_file, name='delete_file'),
    path('download/<int:pk>/', views.download_file, name='download_file'),
]
