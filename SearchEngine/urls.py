from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'dokumen', views.DokumenViewSet)

urlpatterns = [
    # 1. HALAMAN UTAMA: Langsung munculin index.html (Desain Rifdah di sini!!)
    path('', views.search_view, name='index'), 
    
    # 2. HALAMAN HASIL: Jalur pas ngeklik tombol search
    path('search/', views.search_view, name='search'),
    
    # 3. HALAMAN DETAIL: Buat liat rincian dokumen kek abstrak dll. Digilib, LPPM, sama aja jalurnya
    path('detail/<int:id>/', views.detail_view, name='detail'),
    
    # 4. JALUR API: Pindah jalur ke /api/ biar gak tabrakan sama halaman utama
    path('api/', include(router.urls)),
    
    # 5. JALUR API: Kalau berhasil pakai OPAC hapus aja ini
    path('api/global-search/', views.search_global_api, name='api_global_search'),
]