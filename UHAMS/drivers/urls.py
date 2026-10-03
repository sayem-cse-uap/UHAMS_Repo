from django.urls import path
from . import views

app_name = 'drivers'

urlpatterns = [
    path('register/', views.register_driver, name='register'),
    path('dashboard/', views.driver_dashboard, name='dashboard'),
]
