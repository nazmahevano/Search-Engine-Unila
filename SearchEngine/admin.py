from django.contrib import admin
from .models import DokumenAkademik

@admin.register(DokumenAkademik)
class DokumenAkademikAdmin(admin.ModelAdmin):
    list_display = ('judul', 'penulis', 'sumber', 'tanggal_terbit')
    search_fields = ('judul', 'penulis')
