# admin.py
from django.contrib import admin
from .models import DokumenAkademik

@admin.register(DokumenAkademik)
class DokumenAkademikAdmin(admin.ModelAdmin):
    # Ganti list_display kamu biar sinkron sama models.py yang baru
    list_display = ('title', 'author', 'source', 'date_release') # Dulu: ('judul', 'penulis', 'sumber', 'tanggal_terbit')
    
    # Kalau kamu punya search_fields atau list_filter, ganti juga ya!
    search_fields = ('title', 'author') 
    list_filter = ('source', 'faculty', 'major')