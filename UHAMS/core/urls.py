"""URLs owned by the `core` app. They are mounted at the site root ('') in
UHAMS/urls.py, so these are the public paths: /, /login/, /logout/, /register/, /settings/."""
from django.urls import path
from . import views

# Namespace for reverse lookups: {% url 'core:login' %}, redirect('core:home'), ...
app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),                       # landing page
    path('login/', views.loginView, name='login'),           # username + password form
    path('logout/', views.logoutView, name='logout'),        # ends the session
    path('register/', views.register_new_user, name='register'),   # "which kind of account?" chooser
    path('settings/', views.account_settings, name='settings'),    # every role's own settings page
]
