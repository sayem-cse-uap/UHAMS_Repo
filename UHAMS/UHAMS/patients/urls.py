from django.urls import path
from . import views

urlpatterns = [
    path('register-patient/', views.register_patient, name='register_patient'),
    path('patient-dashboard/', views.patient_dashboard, name='patient-dashboard'),
    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book-appointment'),
]
