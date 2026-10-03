from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('register/', views.register_patient, name='register'),
    path('dashboard/', views.patient_dashboard, name='dashboard'),
    path('doctors/<int:doctor_id>/book/', views.book_appointment, name='book-appointment'),
]
