from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'dokumen', views.DokumenViewSet)

urlpatterns = [
    # 1. HALAMAN UTAMA: Langsung munculin index.html (Desain Rifdah)
    path('', views.search_view, name='index'), 
    
    # 2. HALAMAN HASIL: Jalur saat tombol cari diklik
    path('search/', views.search_view, name='search'),
    
    # 3. HALAMAN DETAIL: Untuk melihat abstrak lengkap
    path('detail/<int:id>/', views.detail_view, name='detail'),
    
    # 4. JALUR API: Kita pindah ke /api/ biar gak tabrakan sama halaman utama
    path('api/', include(router.urls)),
    
    # 5. JALUR API: Semantic Scholar (Global Search) - Bisa dipanggil dari JS atau mobile app
    path('api/global-search/', views.search_global_api, name='api_global_search'),
]