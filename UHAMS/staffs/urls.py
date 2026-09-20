from django.urls import path
from . import views

urlpatterns = [
    path('register-staff/', views.register_staff, name='register_staff'),
]