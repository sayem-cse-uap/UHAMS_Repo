"""URLs of the `doctors` app, mounted under /doctors/ in UHAMS/urls.py."""
from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('register/', views.register_doctor, name='register'),
    path('dashboard/', views.doctor_dashboard, name='dashboard'),
    path('schedule/', views.doctor_schedule, name='schedule'),
    # <int:appointment_id> = the Appointment the doctor is confirming.
    path('appointments/<int:appointment_id>/confirm/', views.confirm_appointment, name='confirm-appointment'),
]
