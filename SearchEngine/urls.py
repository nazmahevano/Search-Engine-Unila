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

    # 5. FITUR AUTOCOMPLETE
    path('api/autocomplete/', views.autocomplete_api, name='autocomplete'),
    
    path('dashboard-pencarian/', views.dashboard_analitik_view, name='dashboard_pencarian'),
]