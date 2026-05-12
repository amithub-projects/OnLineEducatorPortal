from django.urls import path
from . import views

urlpatterns = [
    path('checkout/<int:course_pk>/', views.payment_checkout, name='payment_checkout'),
    path('callback/', views.payment_callback, name='payment_callback'),
    path('history/', views.payment_history, name='payment_history'),
]
