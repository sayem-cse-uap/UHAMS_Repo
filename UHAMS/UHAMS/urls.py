"""
URL configuration for UHAMS.

Layout (every app is namespaced; reverse with e.g. 'patients:dashboard'):

    /                          core        home, login, logout, register, settings
    /admin/                    Django admin
    /staff/...                 staffs      dashboard, register, members, vacations, calls
    /patients/...              patients    register, dashboard, doctors/<id>/book
    /doctors/...               doctors     register, dashboard, schedule, appointments/<id>/confirm
    /drivers/...               drivers     register, dashboard
    /ambulances/...            ambulances  list, new, mine, <pk>, <pk>/edit|delete|status

Old URLs are kept alive through UHAMS.legacy_urls (301 redirects).
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('staff/', include('staffs.urls')),
    path('patients/', include('patients.urls')),
    path('doctors/', include('doctors.urls')),
    path('drivers/', include('drivers.urls')),
    path('ambulances/', include('ambulances.urls')),

    # Redirects from the previous URL scheme
    path('', include('UHAMS.legacy_urls')),
]
