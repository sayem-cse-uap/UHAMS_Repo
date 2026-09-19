from django.urls import path
from . import views
# from staffs.views import register_staff
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.loginView, name='login'),
    # path('logout/', views.logoutView, name='logout'),

]
