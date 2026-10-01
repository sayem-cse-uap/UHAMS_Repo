from django.urls import path
from . import views

urlpatterns = [
    path('register-doctor/', views.register_doctor, name='register_doctor'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor-dashboard'),
    path('schedule/', views.doctor_schedule, name='doctor-schedule'),
    path('appointments/<int:appointment_id>/confirm/', views.confirm_appointment, name='confirm-appointment'),
]
