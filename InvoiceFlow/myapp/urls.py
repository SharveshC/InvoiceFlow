from django.urls import path
from . import views


urlpatterns = [

    path('', views.home, name="home"),
    path('login/', views.login_page, name="login"),
    path('signup/', views.signup, name="signup"),
    path('dashboard/', views.dashboard, name="dashboard"),
    path('logout/', views.logout_view, name="logout"),
]