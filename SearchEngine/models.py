from django.db import models

class DokumenAkademik(models.Model):
    # Primary Key (Wajib ada agar Django bisa panggil data spesifik)
    id = models.BigIntegerField(primary_key=True) 
    
    # --- Hasil Perubahan ke Bahasa Inggris ---
    identifier = models.CharField(max_length=255, null=True, blank=True, unique=True)
    title = models.TextField() # Dulu: judul
    author = models.CharField(max_length=255) # Dulu: penulis
    abstract = models.TextField(null=True, blank=True) # Dulu: abstrak
    date_release = models.CharField(max_length=50, null=True, blank=True) # Dulu: tanggal_terbit
    source = models.CharField(max_length=50, default='digilib') # Dulu: sumber
    
    # --- Metadata & URL Legacy ---
    url_asli = models.URLField(max_length=500, null=True, blank=True)
    diambil_pada = models.DateTimeField(auto_now_add=True)
    
    # --- Kolom Struktur File Baru (URL PDF) ---
    url_digilib = models.URLField(max_length=500, null=True, blank=True)
    url_abstract = models.URLField(max_length=500, null=True, blank=True)
    url_bab_1 = models.URLField(max_length=500, null=True, blank=True)
    url_bab_2 = models.URLField(max_length=500, null=True, blank=True)
    url_bab_3 = models.URLField(max_length=500, null=True, blank=True)
    
    # --- Kolom Akademik (Terbaru) ---
    type = models.CharField(max_length=100, null=True, blank=True) # Jenis Dokumen (Skripsi, Tesis, Disertasi)
    faculty = models.CharField(max_length=100, null=True, blank=True) # Fakultas

    class Meta:
        managed = False  # WAJIB! Agar Django tidak mengubah tabel yang sudah ada
        db_table = 'SearchEngine_dokumenakademik' # Harus persis nama tabel di Supabase

    def __str__(self):
        return self.title # Sekarang kita return title