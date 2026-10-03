"""URLs of the `patients` app, mounted under /patients/ in UHAMS/urls.py."""
from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('register/', views.register_patient, name='register'),
    path('dashboard/', views.patient_dashboard, name='dashboard'),
    # <int:doctor_id> is the DoctorProfile id of the doctor being booked.
    path('doctors/<int:doctor_id>/book/', views.book_appointment, name='book-appointment'),
]
