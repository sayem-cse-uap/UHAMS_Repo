"""
URL configuration for UHAMS.

This is the "table of contents" of the whole website. When a request arrives,
Django walks through `urlpatterns` from top to bottom and uses the first
pattern that matches. Each `include()` hands the rest of the URL over to the
urls.py of one app, which is why every app has its own small urls.py.

Layout (every app is namespaced; reverse with e.g. 'patients:dashboard'):

    /                          core        home, login, logout, register, settings
    /admin/                    Django admin
    /staff/...                 staffs      dashboard, register, members, vacations, calls
    /patients/...              patients    register, dashboard, doctors/<id>/book
    /doctors/...               doctors     register, dashboard, schedule, appointments/<id>/confirm
    /drivers/...               drivers     register, dashboard
    /ambulances/...            ambulances  list, new, mine, <pk>, <pk>/edit|delete|status

Old URLs are kept alive through UHAMS.legacy_urls (301 redirects).

"Namespaced" means each app's urls.py sets `app_name = '...'`, so in code and
templates you refer to a page by "<app>:<name>", e.g. {% url 'staffs:dashboard' %}
or redirect('core:login'). That way two apps can both have a page called
"dashboard" without clashing, and the real URL text can change later without
having to edit every link.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django's built-in admin site (uses Django's own login, separate from
    # the session-based login the rest of the site uses).
    path('admin/', admin.site.urls),

    # '' (empty prefix) means core owns the site root: /, /login/, /logout/ ...
    path('', include('core.urls')),

    # Each of these prefixes is stripped off before the app's own urls.py
    # sees the remaining part of the URL.
    path('staff/', include('staffs.urls')),
    path('patients/', include('patients.urls')),
    path('doctors/', include('doctors.urls')),
    path('drivers/', include('drivers.urls')),
    path('ambulances/', include('ambulances.urls')),

    # Redirects from the previous URL scheme
    # Listed LAST so that real, current URLs always win; the legacy file only
    # catches old paths that nothing above matched.
    path('', include('UHAMS.legacy_urls')),
]
