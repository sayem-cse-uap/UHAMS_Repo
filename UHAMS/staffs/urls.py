from django.urls import path
from . import views

urlpatterns = [
    path('register-staff/', views.register_staff, name='register_staff'),
    path('staff-dashboard/', views.staff_dashboard, name='staff-dashboard'),
    path('manage/', views.manage_staff_list, name='manage-staff'),
    path('manage/<int:pk>/', views.manage_staff_detail, name='manage-staff-detail'),
    path('manage/vacations/', views.manage_vacations, name='manage-vacations'),
    path('vacations/', views.my_vacations, name='my-vacations'),
    path('calls/', views.call_list, name='call-list'),
    path('calls/new/', views.call_new, name='call-new'),
    path('calls/<int:pk>/', views.call_detail, name='call-detail'),
]
