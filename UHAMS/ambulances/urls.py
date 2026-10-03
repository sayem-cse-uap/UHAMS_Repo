from django.urls import path
from . import views

app_name = 'ambulances'

urlpatterns = [
    path('', views.ambulance_list, name='list'),
    path('new/', views.create_ambulance, name='create'),
    path('mine/', views.my_ambulance, name='mine'),
    path('<int:pk>/', views.ambulance_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_ambulance, name='edit'),
    path('<int:pk>/delete/', views.delete_ambulance, name='delete'),
    path('<int:pk>/status/', views.update_ambulance_status, name='update-status'),
]
