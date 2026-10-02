from django.urls import path
from . import views

urlpatterns = [
    path('', views.ambulance_list, name='ambulance-list'),
    path('add/', views.create_ambulance, name='create-ambulance'),
    path('my-ambulance/', views.my_ambulance, name='my-ambulance'),
    path('<int:ambulance_pk>/', views.ambulance_detail, name='ambulance-detail'),
    path('<int:ambulance_pk>/edit/', views.edit_ambulance, name='edit-ambulance'),
    path('<int:ambulance_pk>/delete/', views.delete_ambulance, name='delete-ambulance'),
    path('<int:ambulance_pk>/status/', views.update_ambulance_status, name='update-ambulance-status'),
]
