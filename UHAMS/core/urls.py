from django.urls import path
from . import views
# from staffs.views import register_staff
urlpatterns = [
    path('', views.home, name='home'),
    path('register-staff/', views.register_staff, name='register_staff'),
]
