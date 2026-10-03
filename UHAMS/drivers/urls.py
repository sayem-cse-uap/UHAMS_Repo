"""URLs of the `drivers` app, mounted under /drivers/ in UHAMS/urls.py."""
from django.urls import path
from . import views

app_name = 'drivers'

urlpatterns = [
    path('register/', views.register_driver, name='register'),
    path('dashboard/', views.driver_dashboard, name='dashboard'),
]
