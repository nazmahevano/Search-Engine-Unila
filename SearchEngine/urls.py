from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'dokumen', views.DokumenViewSet)

urlpatterns = [
    # Arahkan halaman utama ke fungsi api_search yang kamu punya
    path('', include(router.urls)),
    
    # Jalur API tetap ada
    path('search/', views.api_search, name='api_search'),
]