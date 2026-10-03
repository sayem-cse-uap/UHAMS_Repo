"""URLs of the `ambulances` app, mounted under /ambulances/ in UHAMS/urls.py."""
from django.urls import path
from . import views

app_name = 'ambulances'

# Order matters: fixed paths such as 'new/' and 'mine/' are listed before the
# <int:pk> ones. (An <int:pk> pattern would not match them anyway, but keeping
# literal paths first is the safe habit.)
urlpatterns = [
    path('', views.ambulance_list, name='list'),                    # staff: fleet list
    path('new/', views.create_ambulance, name='create'),            # staff: add an ambulance
    path('mine/', views.my_ambulance, name='mine'),                 # driver: jump to own ambulance
    path('<int:pk>/', views.ambulance_detail, name='detail'),       # staff/driver: one ambulance
    path('<int:pk>/edit/', views.edit_ambulance, name='edit'),      # staff: edit
    path('<int:pk>/delete/', views.delete_ambulance, name='delete'),# staff: delete (confirm page)
    path('<int:pk>/status/', views.update_ambulance_status, name='update-status'),  # POST-only status change
]
