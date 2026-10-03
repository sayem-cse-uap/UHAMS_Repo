"""URLs of the `staffs` app, mounted under /staff/ in UHAMS/urls.py
(so 'dashboard/' below is really /staff/dashboard/)."""
from django.urls import path
from . import views

app_name = 'staffs'

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='dashboard'),
    path('register/', views.register_staff, name='register'),

    # Staff members (manager only)
    # <int:pk> captures a number from the URL and passes it to the view as `pk`
    # (the StaffProfile's primary key).
    path('members/', views.manage_staff_list, name='member-list'),
    path('members/<int:pk>/', views.manage_staff_detail, name='member-detail'),

    # Vacations: own requests, and the manager review queue
    path('vacations/', views.my_vacations, name='vacations'),
    path('vacations/requests/', views.manage_vacations, name='vacation-requests'),

    # Emergency calls
    path('calls/', views.call_list, name='call-list'),
    path('calls/new/', views.call_new, name='call-create'),
    path('calls/<int:pk>/', views.call_detail, name='call-detail'),
]
