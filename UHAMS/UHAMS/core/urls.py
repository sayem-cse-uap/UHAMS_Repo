from django.urls import path
from . import views
# from staffs-templates.views import register_staff
urlpatterns = [

    path('', views.home, name='home'),
    path('login/', views.loginView, name='login'),
    path('logout/', views.logoutView, name='logout'),
    path('register-new-user/', views.register_new_user, name='register_new_user'),

    # path('logout/', views.logoutView, name='logout'),

]
