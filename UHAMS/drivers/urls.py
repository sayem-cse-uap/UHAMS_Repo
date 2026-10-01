from django.urls import path
from . import views

urlpatterns = [
    path('register-driver/', views.register_driver, name='register_driver'),
    path('driver-dashboard/', views.driver_dashboard, name='driver-dashboard'),
]