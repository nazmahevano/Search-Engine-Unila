from django.urls import path
from . import views

urlpatterns = [
    # Arahkan halaman utama ke fungsi api_search yang kamu punya
    path('', views.api_search, name='home'),
    
    # Jalur API tetap ada
    path('api/search/', views.api_search, name='api_search'),
]