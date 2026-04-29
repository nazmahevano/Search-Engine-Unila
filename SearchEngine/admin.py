from django.contrib import admin
from .models import DokumenAkademik
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@admin.register(DokumenAkademik)
class DokumenAkademikAdmin(admin.ModelAdmin):
    # Kolom yang muncul di daftar tabel admin
    list_display = ('title', 'author', 'division', 'year', 'source')
    
    # Filter yang ada di sebelah kanan (Ini yang bikin error tadi)
    list_filter = ('source', 'division', 'year', 'access')
    
    # Fitur pencarian di admin panel
    search_fields = ('title', 'author', 'identifier')
    
    # Agar field ini hanya bisa dibaca (opsional)
    readonly_fields = ('indexed_at', 'synced_at')