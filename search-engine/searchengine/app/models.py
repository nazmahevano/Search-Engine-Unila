from django.db import models

# Create your models here.
# Database untuk Digilib (Misal fokus ke Skripsi)
class Digilib(models.Model):
    # Kolom ini harus sama persis dengan nama di Supabase
    judul = models.TextField(null=True, blank=True)
    penulis = models.TextField(null=True, blank=True)
    abstrak = models.TextField(null=True, blank=True)
    tanggal_terbit = models.CharField(max_length=100, null=True, blank=True) 
    sumber = models.CharField(max_length=255, null=True, blank=True)
    url_asli = models.URLField(null=True, blank=True)
    diambil_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False  # Jangan ubah struktur tabel temanmu
        db_table = 'SearchEngine_dokumenakademik' # Nama tabel asli

    def __str__(self):
        return self.judul

    def __str__(self):
        return self.judul