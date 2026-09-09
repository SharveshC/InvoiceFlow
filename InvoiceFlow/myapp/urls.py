from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name="home"),
    path('login/', views.login_page, name="login"),
    path('signup/', views.signup, name="signup"),
    path('dashboard/', views.dashboard, name="dashboard"),
    path('logout/', views.logout_view, name="logout"),
    path('create-company/', views.create_company, name="create_company"),
    path('switch-company/<int:company_id>/',views.switch_company,name="switch_company"),
    path('clients/',views.clients,name="clients"),
    path('clients/add/', views.add_client, name="add_client"),
    path('clients/<int:client_id>/edit/',views.edit_client,name="edit_client"),
    path('clients/<int:client_id>/delete/',views.delete_client,name="delete_client"),
    path('products/', views.products, name="products"),
    
]