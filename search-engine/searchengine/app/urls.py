from django.urls import path
from app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('detail/<int:id>/', views.detail, name="detail"),
]