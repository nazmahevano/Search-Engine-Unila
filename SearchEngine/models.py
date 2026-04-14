from django.db import models

class DokumenAkademik(models.Model):
    # Data dari OAI-PMH (Dublin Core)
    judul = models.TextField()
    penulis = models.CharField(max_length=255)
    abstrak = models.TextField(null=True, blank=True)
    tanggal_terbit = models.CharField(max_length=50, null=True, blank=True)
    
    # Metadata tambahan untuk sistem kamu
    sumber = models.CharField(max_length=50, default='digilib') # Misal: 'digilib' atau 'scholar'
    url_asli = models.URLField(max_length=500, unique=True) # Unik agar tidak ada data ganda
    diambil_pada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.judul