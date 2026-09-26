from django.urls import path
from . import views

urlpatterns = [
    path('register-doctor/', views.register_doctor, name='register_doctor'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor-dashboard'),
]