from django.urls import path
from .views import api_search

urlpatterns = [
    path('api/search/', api_search, name='api_search'),
]