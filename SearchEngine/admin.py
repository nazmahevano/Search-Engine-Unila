from django.contrib import admin
from django.db.models import Count, Subquery, OuterRef
from .models import DokumenAkademik, SearchTrend
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@admin.register(DokumenAkademik)
class DokumenAkademikAdmin(admin.ModelAdmin):
    # Kolom yang muncul di daftar tabel admin
    list_display = ('title', 'author', 'division', 'year', 'source')
    
    # Filter yang ada di sebelah kanan (Ini yang bikin error tadi)
    list_filter = ('source', 'division', 'year',)
    
    # Fitur pencarian di admin panel
    search_fields = ('title', 'author', 'identifier')
    
    # Agar field ini hanya bisa dibaca (opsional)
    readonly_fields = ('indexed_at', 'synced_at')
    
@admin.register(SearchTrend)
class SearchTrendAdmin(admin.ModelAdmin):
    # Menampilkan kolom kata kunci dan waktu pencarian
    list_display = ('keyword', 'created_at')
    
    # Menambahkan kotak pencarian khusus untuk admin
    search_fields = ('keyword',)
    
    # Menambahkan filter waktu di sebelah kanan (Hari ini, 7 hari lalu, dsb)
    list_filter = ('created_at',)
    
    # Mengurutkan dari pencarian terbaru ke terlama
    ordering = ('-created_at',)
    
    # 5. Membatasi 50 baris per halaman agar rapi
    list_per_page = 50 
    
    # --- PRO-TIP BACKEND: Menghindari N+1 Query Problem ---
    # Alih-alih menghitung jumlah satu per satu yang membuat server lambat,
    # kita gunakan Subquery untuk menghitung total frekuensi langsung dari level Database PostgreSQL.
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        sq = SearchTrend.objects.filter(keyword=OuterRef('keyword')).values('keyword').annotate(count=Count('id')).values('count')
        return qs.annotate(total_frekuensi=Subquery(sq))

    # --- FORMATTING TAMPILAN PROFESIONAL ---
    def tampilkan_frekuensi(self, obj):
        # Jika sebuah kata kunci dicari lebih dari 10 kali, kita beri label visual "Populer"
        if obj.total_frekuensi > 10:
            return f"🔥 Populer ({obj.total_frekuensi} kali)"
        return f"{obj.total_frekuensi} kali"
    
    tampilkan_frekuensi.short_description = 'Frekuensi Pencarian'
    # Mengizinkan dosen mengklik judul kolom untuk mengurutkan dari yang terbanyak dicari
    tampilkan_frekuensi.admin_order_field = 'total_frekuensi' 

    def waktu_pencarian(self, obj):
        # Mengubah format waktu acak menjadi standar Indonesia yang rapi
        return obj.created_at.strftime("%d %b %Y - %H:%M")
    waktu_pencarian.short_description = 'Waktu Akses Terakhir'